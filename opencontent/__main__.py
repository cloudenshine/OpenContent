import argparse
import json
import sys
from pathlib import Path
from .kernel import Kernel
from .jobs import Jobs
from .providers import CodexProvider, activate_cli, detect_cli, bootstrap_cli
from . import discovery, workbench, ideation
import time
from .server import Server
from .vault import Problem


def main():
    parser = argparse.ArgumentParser(description="OpenContent Markdown control plane")
    parser.add_argument("--vault", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("board")
    sub.add_parser('providers')
    find=sub.add_parser('discover');find.add_argument('--goal',default='');find.add_argument('--ideas',action='store_true')
    ideas=sub.add_parser('ideate');ideas.add_argument('--direction',default='');ideas.add_argument('--provider',choices=['codex','claude'],default='codex')
    chat=sub.add_parser('talk');chat.add_argument('project');chat.add_argument('--message',required=True)
    chat.add_argument('--mode',choices=['discuss','revise','illustrate'],default='discuss')
    chat.add_argument('--provider',choices=['codex','claude'],default='codex')
    chat.add_argument('--skill-root',action='append',default=[])
    hist=sub.add_parser('history');hist.add_argument('project')
    inspect = sub.add_parser("inspect"); inspect.add_argument("id")
    apply = sub.add_parser("apply"); apply.add_argument("request", help="JSON file: action plus arguments")
    serve = sub.add_parser("serve")
    serve.add_argument("--port", type=int, default=0)
    serve.add_argument("--codex")
    serve.add_argument("--agent-timeout", type=int, default=180)
    serve.add_argument("--skill-root", action="append", default=[])
    args = parser.parse_args()
    k = Kernel(args.vault)
    if args.command == "serve":
        # OS lock automatically releases after a crash; no stale-PID guessing.
        lockfile = (k.vault.runtime / "service.lock").open("a+b")
        lockfile.seek(0); lockfile.write(b"0"); lockfile.flush(); lockfile.seek(0)
        try:
            if sys.platform == "win32":
                import msvcrt
                msvcrt.locking(lockfile.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lockfile.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise Problem("Another Kernel service already owns this Vault", 409)
        providers = {"codex": CodexProvider(args.codex, args.agent_timeout)} if args.codex else {}
        jobs = Jobs(k, providers, args.skill_root)
        jobs.provider_notice=bootstrap_cli(jobs)
        server = Server(k, jobs, args.port)
        connection = {"url": f"http://127.0.0.1:{server.server_port}", "token": server.token, "vault": str(k.vault.root)}
        print(json.dumps(connection), flush=True)
        try:
            server.serve_forever(poll_interval=.2)
        finally:
            jobs.close(); server.server_close(); lockfile.close()
        return
    if args.command == "init":
        result = {"vault": str(k.vault.root), "status": "initialized"}
    elif args.command == "board":
        result = k.board()
    elif args.command == "inspect":
        result = k.inspect(args.id)
    elif args.command=='providers':result=detect_cli()
    elif args.command=='discover':result=ideation.preview(k,args.goal) if args.ideas else discovery.recommend(k,args.goal)
    elif args.command=='history':result=workbench.history(k,args.project)
    elif args.command in ('talk','ideate'):
        # A live service owns the job table and interruption recovery; never start a second Jobs owner.
        lockfile=(k.vault.runtime/'service.lock').open('a+b')
        lockfile.seek(0);lockfile.write(b'0');lockfile.flush();lockfile.seek(0)
        try:
            if sys.platform=='win32':
                import msvcrt
                msvcrt.locking(lockfile.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(lockfile.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:raise Problem('已有 Kernel 运行，请使用插件内项目指令台或选题发现；先停用插件才能独立运行 talk / ideate',409)
        jobs=Jobs(k,skill_roots=getattr(args,'skill_root',[]))
        try:
            activate_cli(jobs,args.provider)
            job=(jobs.discover(ideation.preview(k,args.direction)['id'],args.provider) if args.command=='ideate'
                 else jobs.submit(args.project,args.provider,expected=k.vault.token(),instruction=args.message,mode=args.mode))
            while True:
                result=next(j for j in jobs.list() if j['id']==job['id'])
                if result['status'] not in ('QUEUED','RUNNING'):break
                time.sleep(.2)
            result={'job':result,**({'ideation':ideation.read(k,job['id'])} if args.command=='ideate' else {'turns':workbench.history(k,args.project)})}
        finally:jobs.close();lockfile.close()
        if result['job']['status']!='SUCCEEDED':raise Problem('CLI 指令未完成：'+result['job']['detail'].get('error',result['job']['status']))
    else:
        request = json.loads(Path(args.request).read_text(encoding="utf-8-sig"))
        action = request.pop("action")
        functions = {"create_project": k.create_project, "add": k.add, "advance": k.advance, "review": k.review, "decide": k.decide}
        if action not in functions:
            raise Problem("Unknown CLI action")
        result = functions[action](**request)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (Problem, OSError, ValueError, TypeError, KeyError) as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
