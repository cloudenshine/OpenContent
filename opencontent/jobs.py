"""Long-running work lives in the kernel process; job receipts live in SQLite."""
import json
import threading
import uuid
from .providers import discover_skills
from .vault import Problem, now, atomic
from . import workbench, ideation


class Jobs:
    def __init__(self, kernel, providers=None, skill_roots=()):
        self.kernel = kernel
        self.providers = providers or {}
        self.skill_roots = skill_roots
        self.running = {}
        self.mutex = threading.RLock()
        with self.kernel.vault.connection() as db:
            rows = db.execute("SELECT * FROM jobs WHERE status IN ('QUEUED','RUNNING')").fetchall()
            for row in rows:
                detail = json.loads(row["detail"])
                detail["error"] = "Kernel stopped before a terminal receipt; inspect Vault before resuming"
                db.execute("UPDATE jobs SET status='INTERRUPTED',detail=?,updated=? WHERE id=?", (json.dumps(detail), now(), row["id"]))
                if detail.get('stage')=='conversation':workbench.fail(self.kernel,row['project'],row['id'],detail['error'])
                if detail.get('kind')=='ideation':
                    try:
                        saved=ideation.read(self.kernel,row['id']);saved.update(status='INTERRUPTED',error=detail['error']);ideation.save(self.kernel,row['id'],saved)
                    except (Problem,ValueError,OSError):
                        detail['error']='选题任务已中断，结果记录缺失或损坏；请重新准备资料范围。'
                        db.execute('UPDATE jobs SET detail=? WHERE id=?',(json.dumps(detail),row['id']))

    def list(self):
        with self.kernel.vault.connection() as db:
            rows = db.execute("SELECT * FROM jobs ORDER BY created DESC LIMIT 100").fetchall()
        return [{**dict(row), "detail": json.loads(row["detail"])} for row in rows]

    def update(self, uid, status, detail):
        with self.kernel.vault.connection() as db:
            db.execute("UPDATE jobs SET status=?,detail=?,updated=? WHERE id=?", (status, json.dumps(detail, ensure_ascii=False), now(), uid))

    def retry_ideation(self,run):
        old=ideation.read(self.kernel,run)
        if old['status'] not in ('FAILED','CANCELLED','INTERRUPTED'):raise Problem('只能重试失败、取消或中断的选题任务',409)
        snapshot=ideation.load_snapshot(self.kernel,run);ideation.check_snapshot(self.kernel,snapshot)
        previous=next((j for j in self.list() if j['id']==run),None)
        provider=old.get('provider') or (previous['detail'].get('provider') if previous else None)
        if provider not in self.providers:raise Problem('请先启用原任务使用的本地 CLI',503)
        new=uuid.uuid4().hex;snapshot={**snapshot,'id':new,'at':now(),'retry_of':run}
        atomic(ideation.path(self.kernel,new,'snapshot.json'),json.dumps(snapshot,ensure_ascii=False).encode())
        checkpoint=ideation.path(self.kernel,run,'classification.json')
        if checkpoint.is_file():atomic(ideation.path(self.kernel,new,'classification.json'),checkpoint.read_bytes())
        return self.discover(new,provider)

    def discover(self,preview_id,provider=None):
        provider=provider or next(iter(self.providers),None)
        if provider not in self.providers:raise Problem('请先在选题发现窗口启用本地 CLI，综合选题需要模型推理',503)
        snapshot=ideation.load_snapshot(self.kernel,preview_id)
        ideation.check_snapshot(self.kernel,snapshot)
        if len(snapshot['families'])<2:raise Problem('当前资料只构成一个来源组；请补充不同来源，原文与转录不算两份独立资料')
        with self.mutex:
            if any(v['project']=='@ideation' for v in self.running.values()):raise Problem('已有选题综合任务正在运行',409)
            if ideation.path(self.kernel,preview_id).exists():raise Problem('此范围已运行，请查看已有结果或重新准备',409)
            event=threading.Event();detail={'kind':'ideation','stage':'classify','provider':provider,'attempts':[]}
            saved={'id':preview_id,'created':now(),'status':'QUEUED','stage':'classify','direction':snapshot['direction'],'scope':snapshot.get('scope',{}),'provider':provider,'retry_of':snapshot.get('retry_of'),'stats':snapshot['stats'],'result':None}
            ideation.save(self.kernel,preview_id,saved)
            with self.kernel.vault.connection() as db:
                db.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?)',(preview_id,'@ideation','QUEUED',json.dumps(detail),now(),now()))
            thread=threading.Thread(target=self.discover_work,args=(snapshot,provider,event,detail,saved),daemon=True)
            self.running[preview_id]={'project':'@ideation','event':event,'thread':thread,'provider':provider}
            thread.start();return saved

    def discover_work(self,snapshot,provider,event,detail,saved):
        run=snapshot['id']
        try:
            def progress(stage):
                detail['stage']=stage;saved.update(stage=stage,status='RUNNING')
                ideation.save(self.kernel,run,saved);self.update(run,'RUNNING',detail)
            result=ideation.execute(self.kernel,snapshot,self.providers[provider],event,progress)
            saved['path']=ideation.save_markdown(self.kernel,run,result)
            saved.update(status='SUCCEEDED',result=result,completed=now());ideation.save(self.kernel,run,saved)
            self.update(run,'SUCCEEDED',detail)
        except Exception as e:
            state='CANCELLED' if event.is_set() else 'FAILED'
            saved.update(status=state,error=str(e));ideation.save(self.kernel,run,saved)
            self.update(run,state,{**detail,'error':str(e)})
        finally:
            with self.mutex:self.running.pop(run,None)

    def submit(self, pid, provider=None, stage=None, resume=None, expected=None, instruction=None, mode='discuss'):
        if provider is None:
            provider = next(iter(self.providers), None)
        if provider not in self.providers:
            raise Problem("No Agent configured. Core Markdown/state/provenance remain available.", 503)
        if instruction is not None:
            if not isinstance(instruction,str) or not 1<=len(instruction.strip())<=8000 or mode not in ('discuss','revise','illustrate'):
                raise Problem('请填写有效的项目指令并选择讨论、改稿或配图')
            if resume:raise Problem('对话失败后请重新发送指令；历史已保留')
            stage='conversation'
        if stage not in (None, "critique", 'conversation') or stage=='conversation' and instruction is None:
            raise Problem("Only full production or re-critique is supported")
        previous = None
        if resume:
            previous = next((j for j in self.list() if j["id"] == resume), None)
            if not previous or previous["project"] != pid or previous["status"] not in ("FAILED", "CANCELLED", "INTERRUPTED"):
                raise Problem("Only an interrupted/failed/cancelled project job can be resumed")
            if previous['detail'].get('instruction'):raise Problem('请在项目指令台重新发送；对话不会自动转为生产任务')
        with self.mutex:
            input_token = self.kernel.vault.token()
            if expected is not None and input_token != expected:
                raise Problem("Materials changed since preview; inspect them again", 409)
            if any(v["project"] == pid for v in self.running.values()):
                raise Problem("This project already has a running job", 409)
            if not stage and self.kernel.next_stage(pid) is None:
                raise Problem("Project is waiting for judgment; edit the draft or request a new critique")
            uid = uuid.uuid4().hex
            event = threading.Event()
            self.kernel.inspect(pid)
            detail = {"provider": provider, "stage": stage, "attempts": [], "resumed_from": resume, "input_token": input_token}
            if instruction is not None:detail.update(instruction=instruction,mode=mode)
            with self.kernel.vault.connection() as db:
                db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?)", (uid, pid, "QUEUED", json.dumps(detail), now(), now()))
            thread = threading.Thread(target=self.work, args=(uid, pid, provider, stage, event, detail, previous), daemon=True)
            self.running[uid] = {"project": pid, "event": event, "thread": thread, "provider": provider}
            thread.start()
            return {"id": uid, "status": "QUEUED"}

    def work(self, uid, pid, provider_id, forced_stage, event, detail, previous):
        try:
            provider = self.providers[provider_id]
            while True:
                if event.is_set():
                    raise Problem("Cancelled before next stage")
                stage = forced_stage or self.kernel.next_stage(pid)
                if stage is None:
                    break
                self.update(uid, "RUNNING", {**detail, "stage": stage})
                run_id = uuid.uuid4().hex
                workspace = self.kernel.vault.runtime / "runs" / run_id
                workspace.mkdir(parents=True)
                skills=discover_skills(self.skill_roots)
                request = (workbench.request(self.kernel,pid,detail['instruction'],detail['mode'],skills,uid)
                           if stage=='conversation' else self.kernel.request(pid, stage, skills))
                if not detail["attempts"] and request["token"] != detail["input_token"]:
                    raise Problem("Vault changed while queued; no material sent to Agent", 409)
                atomic(workspace / "request.json", json.dumps(request, ensure_ascii=False).encode("utf-8"))
                attempt = {"id": run_id, "stage": stage, "started": now(), "status": "RUNNING"}
                detail["attempts"].append(attempt)
                self.update(uid, "RUNNING", {**detail, "stage": stage})
                if previous:
                    result = provider.resume(request, workspace, event, previous)
                    previous = None
                else:
                    result = provider.run(request, workspace, event)
                if event.is_set():
                    raise Problem("Cancelled before committing response")
                added = (workbench.complete(self.kernel,pid,uid,result,workspace)['id'] if stage=='conversation'
                         else self.kernel.apply_result(pid, stage, result, request["token"], provider_id, run_id))
                attempt.update(status="COMMITTED", completed=now(), objects=added)
                self.update(uid, "RUNNING", detail)
                if forced_stage:
                    break
            detail["outcome"] = "NEEDS_JUDGMENT"
            self.update(uid, "SUCCEEDED", detail)
        except Exception as e:
            detail["error"] = f"{type(e).__name__}: {e}"
            if detail["attempts"] and detail["attempts"][-1]["status"] == "RUNNING":
                detail["attempts"][-1].update(status="FAILED", completed=now())
            self.update(uid, "CANCELLED" if event.is_set() else "FAILED", detail)
            if forced_stage=='conversation':workbench.fail(self.kernel,pid,uid,detail['error'])
        finally:
            with self.mutex:
                self.running.pop(uid, None)

    def cancel(self, uid):
        with self.mutex:
            record = self.running.get(uid)
            if not record:
                raise Problem("Job is no longer running", 409)
            self.providers[record["provider"]].cancel(record["event"])
            return {"id": uid, "status": "CANCELLING"}

    def close(self):
        with self.mutex:
            records = list(self.running.values())
            for record in records:
                self.providers[record["provider"]].cancel(record["event"])
        for record in records:
            record["thread"].join(timeout=12)
