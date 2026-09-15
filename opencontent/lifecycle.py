"""File-native source management and human-confirmed learning. No external services."""
from copy import deepcopy
from datetime import date
import re
import uuid
from .vault import Problem, digest, now, encode
from .domain import require_object, linked, validate


def source_key(material):
    return digest(material.get('source_url') or material['source'])


def note_snapshot(vault, source):
    if not source.startswith('vault:'):
        return None
    try:
        path = vault.safe(source[6:])
        if not path.is_file() or path.stat().st_size > 1_000_000:
            return None
        raw = path.read_bytes()
        body = re.sub(r'^---\r?\n[\s\S]*?\r?\n---\r?\n', '', raw.decode('utf-8-sig')).strip()
        return {'hash':digest(raw), 'body':body}
    except (OSError, UnicodeError, Problem):
        return None


def freshness(vault, material):
    captured = material.get('source_note_hash')
    if not captured:
        return {'status':'UNTRACKED', 'current':None}
    current = note_snapshot(vault, material['source'])
    return {'status':'MISSING' if current is None else 'CURRENT' if current['hash']==captured else 'CHANGED', 'current':current}


def source_issues(kernel, objects, pid):
    issues=[]
    for m in linked(objects,pid,'Material'):
        status=freshness(kernel.vault,m)['status']
        if status in ('CHANGED','MISSING'):
            issues.append(f"Source {status}: {m['title']} — inspect and refresh the captured snapshot")
    return issues


def library(kernel):
    objects, errors = kernel.read(); groups = {}
    for m in (o for o in objects.values() if o['type']=='Material'):
        key = source_key(m)
        group = groups.setdefault(key, {'key':key,'source':m.get('source_url') or m['source'],'materials':[]})
        status = freshness(kernel.vault,m)
        group['materials'].append({'id':m['oc_id'],'title':m['title'],'project':m['project'],
            'project_title':objects.get(m['project'],{}).get('title','Missing project'),
            'revision':digest(m['body']),'freshness':status['status'],'path':m['path'],
            'artifacts':[a['oc_id'] for a in linked(objects,m['project'],'Artifact')],
            'publications':[p['oc_id'] for p in linked(objects,m['project'],'Publication')]})
    return {'sources':list(groups.values()),'diagnostics':errors,'token':kernel.vault.token()}


def refresh_preview(kernel, mid):
    m = require_object(kernel.read()[0],mid,'Material'); state = freshness(kernel.vault,m)
    if not state['current']:
        # Old captures can explicitly start source tracking.
        state['current'] = note_snapshot(kernel.vault,m['source'])
    if not state['current']: raise Problem('The original local Markdown source is unavailable')
    return {'material':m,'source_hash':state['current']['hash'],'current_body':state['current']['body'],
            'token':kernel.vault.token(),'warning':'Refreshing replaces this capture with the selected text and invalidates its project reviews.'}


def refresh_source(kernel, mid, body, expected_source_hash, expected):
    with kernel.vault.lock():
        objects, errors = kernel.read(); m = deepcopy(require_object(objects,mid,'Material'))
        current = note_snapshot(kernel.vault,m['source'])
        if not current or current['hash']!=expected_source_hash: raise Problem('Source changed after preview',409)
        if not isinstance(body,str) or not body.strip() or body.strip() not in current['body']:
            raise Problem('Select a nonempty exact excerpt from the current source')
        old = {k:m.get(k) for k in ('body','capture_hash','source_note_hash')}
        old['archived_at']=now()
        m['versions']=[*m.get('versions',[]),old]
        m.update(body=body.strip(),capture_hash=digest(body.strip()),source_note_hash=current['hash'])
        if len(encode(m))>1_000_000: raise Problem('Version history exceeds 1 MB; archive this material before another refresh')
        validate(m,objects);kernel.vault.commit([m],expected)
        return m


def reuse_material(kernel, mid, pid, expected):
    with kernel.vault.lock():
        objects,_=kernel.read();m=require_object(objects,mid,'Material');require_object(objects,pid,'Project')
        if freshness(kernel.vault,m)['status'] in ('MISSING','CHANGED'):raise Problem('Refresh the source before reusing it')
        if kernel.vault.token()!=expected:raise Problem('Vault changed before reuse',409)
        for existing in linked(objects,pid,'Material'):
            if source_key(existing)==source_key(m) and existing['body']==m['body']:
                return {'object':existing,'duplicate':True}
        copy=kernel.vault.new('Material',m['title'],m['body'],pid,source=m['source'],reused_from=mid,
            **{k:m[k] for k in ('source_url','source_note_hash','capture_hash') if k in m})
        validate(copy,objects);kernel.vault.commit([copy],expected)
        return {'object':copy,'duplicate':False}


def plan_project(kernel, pid, planned_for, expected):
    if planned_for:
        try:date.fromisoformat(planned_for)
        except (TypeError,ValueError):raise Problem('Use a YYYY-MM-DD plan date')
    with kernel.vault.lock():
        p=deepcopy(require_object(kernel.read()[0],pid,'Project'))
        p['planning']={'planned_for':planned_for or None}
        kernel.vault.commit([p],expected);return p


def feedback(kernel, pubid, source, body, suggestion, expected):
    if not all(isinstance(v,str) and v.strip() for v in (source,body,suggestion)):
        raise Problem('Feedback needs an explicit source, observation and proposed lesson')
    with kernel.vault.lock():
        objects,_=kernel.read();pub=deepcopy(require_object(objects,pubid,'Publication'))
        if pub.get('delivery_status','MANUAL') not in ('PUBLISHED','MANUAL'):
            raise Problem('Feedback requires a published receipt or an explicitly manual publication record')
        item={'id':uuid.uuid4().hex,'at':now(),'source':source,'observation':body,'suggestion':suggestion,
              'context_hash':pub['context_hash'],'decision':'PENDING'}
        pub['feedback']=[*pub.get('feedback',[]),item]
        p=deepcopy(objects[pub['project']]);changes=[pub]
        if p['state']=='PUBLISHED':
            p['history'].append({'from':p['state'],'to':'LEARNING','at':now(),'basis':pubid})
            p['state']='LEARNING';changes.append(p)
        kernel.vault.commit(changes,expected);return item


def judge_feedback(kernel, pubid, fid, decision, reviewer, reason, expected):
    if decision not in ('accept','reject') or not isinstance(reviewer,str) or not reviewer.strip() or not isinstance(reason,str) or len(reason.strip())<8:
        raise Problem('Lesson decision requires accept/reject, reviewer and a substantive reason')
    with kernel.vault.lock():
        pub=deepcopy(require_object(kernel.read()[0],pubid,'Publication'))
        item=next((f for f in pub.get('feedback',[]) if f['id']==fid),None)
        if not item or item['decision']!='PENDING':raise Problem('Feedback is absent or already decided',409)
        item.update(decision=decision,reviewer=reviewer,reason=reason,decided_at=now())
        kernel.vault.commit([pub],expected);return item


def next_project(kernel, pubid, fid, title, goal, audience, expected):
    with kernel.vault.lock():
        if kernel.vault.token()!=expected:raise Problem('Vault changed before lesson reuse',409)
        objects,_=kernel.read();pub=require_object(objects,pubid,'Publication')
        item=next((f for f in pub.get('feedback',[]) if f['id']==fid),None)
        if not item or item['decision']!='accept':raise Problem('Only a human-accepted lesson can seed another project')
        for p in objects.values():
            if p['type']=='Project' and p.get('learning_from')=={'publication':pubid,'feedback':fid}:
                return {'object':p,'duplicate':True}
        p=kernel.vault.new('Project',title,f'# {title}\n\n{goal}\n\n## 已确认的编辑经验\n\n{item["suggestion"]}',
            goal=goal,audience=audience,thesis='',state='CAPTURED',history=[],
            learning_from={'publication':pubid,'feedback':fid},
            editorial_lessons=[{'lesson':item['suggestion'],'source':item['source'],'reviewer':item['reviewer'],'reason':item['reason']}])
        validate(p,{p['oc_id']:p});kernel.vault.commit([p],expected);return {'object':p,'duplicate':False}
