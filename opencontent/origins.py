"""Conservative source-family hints; a family is not proof of independent evidence."""
import hashlib
import re
from urllib.parse import urlsplit,parse_qsl,urlencode
import yaml

def origin_digest(text):
    match=re.match(r'^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)',text)
    if not match or len(match[1])>20000:return None
    try:meta=yaml.safe_load(match[1])
    except yaml.YAMLError:return None
    if not isinstance(meta,dict):return None
    value=next((meta[k] for k in ('source','source_url','url') if isinstance(meta.get(k),str) and meta[k].startswith(('http://','https://'))),None)
    if not value:return None
    try:
        u=urlsplit(value)
        if not u.hostname or u.username or u.password:return None
        query=sorted((k,v) for k,v in parse_qsl(u.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid','gclid'))
        canonical=(u.hostname.lower(),u.port,u.path or '/',urlencode(query))
    except ValueError:return None
    return hashlib.sha256(repr(canonical).encode()).hexdigest()

def title_key(title):
    value=re.sub(r'^(?:get_|import_)','',title,flags=re.I)
    value=re.sub(r'(?:[_\- ](?:original|transcript|summary|摘要|原文|转录|文字稿|总结|副本)|_\d{10,22})+$','',value,flags=re.I)
    key=re.sub(r'[\W_]+','',value).casefold()
    return key,value!=title

def plain(text):return re.sub(r'[\W_]+','',text).casefold()[:30000]
def shingles(text):return {text[i:i+5] for i in range(len(text)-4)}

def annotate(sources,rows):
    parent=list(range(len(sources)));reasons=[]
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    bodies=[plain(n['body']) for n in rows];grams=[shingles(t) if len(t)>=120 else set() for t in bodies]
    keys=[title_key(s['title']) for s in sources]
    for i in range(len(sources)):
        for j in range(i):
            reason=None
            if rows[i].get('origin_digest') and rows[i]['origin_digest']==rows[j].get('origin_digest'):reason='相同来源链接'
            elif sources[i]['content_hash']==sources[j]['content_hash']:reason='相同正文'
            elif len(keys[i][0])>=12 and keys[i][0]==keys[j][0] and (keys[i][1] or keys[j][1]):reason='原文/转录/摘要文件名关系'
            elif grams[i] and grams[j] and len(grams[i]&grams[j])/min(len(grams[i]),len(grams[j]))>=.88:reason='正文高度重合'
            if reason:
                parent[find(i)]=find(j);reasons.append((i,j,reason))
    groups={}
    for i,source in enumerate(sources):
        root=find(i);group=groups.setdefault(root,{'id':'f'+str(len(groups)+1),'sources':[],'reasons':[]})
        group['sources'].append(source['id']);source['family']=group['id']
    for i,j,reason in reasons:
        group=groups[find(i)]
        if reason not in group['reasons']:group['reasons'].append(reason)
    return list(groups.values())
