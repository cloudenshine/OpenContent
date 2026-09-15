"""Local, explainable note discovery. Nothing is sent to an Agent until selected."""
from collections import Counter
from pathlib import Path
import math
import os
import re
from .vault import Problem, digest
from .domain import validate
from .origins import origin_digest

EXCLUDED = {'OpenContent', 'OpenContent-Exports', 'OpenContent-Workspace', 'Attachments', 'node_modules', 'archive'}

def words(text):
    text=text.lower()
    tokens=re.findall(r'[a-z0-9]{2,}',text)
    for run in re.findall(r'[\u4e00-\u9fff]+',text):
        tokens.extend(run[i:i+2] for i in range(len(run)-1))
    return set(tokens)

def prose(text):
    return re.sub(r'^---\r?\n[\s\S]*?\r?\n---\r?\n','',text).strip()

def notes(kernel):
    rows=[];skipped=0;total=0;limited=False
    for directory,dirs,files in os.walk(kernel.vault.root,followlinks=False):
        dirs[:]=sorted(d for d in dirs if not d.startswith(('.', '_')) and d not in EXCLUDED
                        and not (Path(directory)/d).is_symlink() and not (Path(directory)/d).is_junction())
        for name in sorted(files):
            if not name.lower().endswith('.md') or name in ('CONTENT.md','AGENTS.md','SKILL.md'):continue
            candidate=Path(directory)/name
            if candidate.is_symlink():skipped+=1;continue
            path=kernel.vault.safe(candidate.relative_to(kernel.vault.root))
            if path.stat().st_size>500_000:skipped+=1;continue
            if len(rows)>=3000 or total+path.stat().st_size>30_000_000:limited=True;break
            try:raw=path.read_bytes();body=prose(raw.decode('utf-8-sig'))
            except (OSError,UnicodeError):skipped+=1;continue
            if len(body)<20:continue
            total+=len(raw)
            rows.append({'path':path.relative_to(kernel.vault.root).as_posix(),'title':path.stem,
                         'body':body,'origin_digest':origin_digest(raw.decode('utf-8-sig')),'hash':digest(raw),'words':words(path.stem+' '+body[:30000])})
        if limited:break
    return rows,{'scanned':len(rows),'skipped':skipped,'limited':limited,'algorithm':'local-cjk-bigram-tfidf'}

def recommend(kernel, goal='', ideas=False):
    if ideas:
        from .ideation import preview
        return preview(kernel,goal)
    if not isinstance(goal,str) or len(goal)>4000:raise Problem('目标需为不超过 4000 字的文字')
    rows,stats=notes(kernel);objects,errors=kernel.read()
    if errors:raise Problem('请先处理 Vault 诊断')
    projects=[p for p in objects.values() if p['type']=='Project']
    used={};used_bodies={}
    for m in objects.values():
        if m['type']=='Material' and m.get('source','').startswith('vault:'):
            used.setdefault(m['source'][6:],set()).add(m['project'])
        if m['type'] in ('Material','Artifact'):
            used_bodies.setdefault(digest(prose(m['body'])),set()).add(m['project'])
    q=words(goal);freq=Counter(w for n in rows for w in n['words']);ranked=[];excluded=[]
    for n in rows:
        matched=q & n['words']
        score=sum(math.log(1+len(rows)/(1+freq[w])) for w in matched)/(1+math.sqrt(len(n['words']))*.05)
        score+=len(q & words(n['title']))*2
        similar=[]
        for p in projects:
            t=words(p['title']+' '+p['goal']);base=words(n['title'])
            overlap=len(base&t)/max(1,len(base))
            same_body=p['oc_id'] in used_bodies.get(digest(n['body']),set())
            if p['oc_id'] in used.get(n['path'],set()) or same_body or overlap>=.8 and len(base)>=3:
                similar.append({'id':p['oc_id'],'title':p['title'],'state':p['state'],
                                'reason':'内容已覆盖' if same_body else '已作为项目材料' if p['oc_id'] in used.get(n['path'],set()) else '主题高度重合'})
        row={k:n[k] for k in ('path','title','hash')}
        row.update(score=round(score,3),excerpt=n['body'][:240],matches=sorted(matched)[:12],existing_projects=similar)
        if q and not matched:continue
        ranked.append(row)
    ranked.sort(key=lambda n:(-n['score'],n['path']))
    return {'candidates':ranked[:40],'excluded':excluded[:40],'stats':stats,'token':kernel.vault.token(),
            'note':'按本地词项、标题与已关联材料判断；语义相近但用词不同的重复选题仍需人工核对。'}

def create_selected(kernel,title,goal,audience,selected,expected,editorial_brief=None):
    if not all(isinstance(s,str) and 0<len(s.strip())<=4000 for s in (title,goal,audience)):
        raise Problem('请填写项目名称、目标和读者')
    if not isinstance(selected,list) or len(selected)>20:raise Problem('最多选择 20 篇材料')
    available={n['path']:n for n in notes(kernel)[0]};chosen=[]
    for row in selected:
        if not isinstance(row,dict) or row.get('path') not in available:raise Problem('所选笔记不在可检索范围')
        note=available[row['path']]
        if row.get('hash')!=note['hash']:raise Problem('材料在推荐后发生变化，请刷新推荐',409)
        if note not in chosen:chosen.append(note)
    with kernel.vault.lock():
        if kernel.vault.token()!=expected:raise Problem('项目库已变化，请刷新推荐',409)
        objects,errors=kernel.read()
        if errors:raise Problem('请先处理 Vault 诊断')
        if any(o['type']=='Project' and o['title'].strip().casefold()==title.strip().casefold() for o in objects.values()):
            raise Problem('已有同名项目，请继续已有项目或明确修改选题',409)
        p=kernel.vault.new('Project',title.strip(),goal,goal=goal,audience=audience,thesis='',state='CAPTURED',history=[])
        if editorial_brief is not None:p['editorial_brief']=editorial_brief
        additions=[p];objects[p['oc_id']]=p
        for n in chosen:
            if digest(kernel.vault.safe(n['path']).read_bytes())!=n['hash']:raise Problem('材料已变化，请刷新',409)
            m=kernel.vault.new('Material',n['title'],n['body'],p['oc_id'],source='vault:'+n['path'],source_note_hash=n['hash'])
            objects[m['oc_id']]=m;additions.append(m)
        for obj in additions:validate(obj,objects)
        kernel.vault.commit(additions,expected)
        return p
