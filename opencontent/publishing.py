"""File-native WeChat outbox. Two human confirmations; no automatic write retry."""
from copy import deepcopy
from html.parser import HTMLParser
import json
import re
import threading
import uuid
from urllib.parse import urlsplit
import mistune
from . import credentials
from .domain import require_object, linked
from .handoff import reader_body
from .publishing_adapters import WeChat, UnknownOutcome, RemoteRejected, platform_image_url
from . import rendering
from .vault import Problem, digest, now, atomic

INTENT_FIELDS=('artifact','context_hash','review','decision','channel','destination','action','payload','media_id','draft_publication','remote_before_hash')
UNRESOLVED=('SENDING','UNKNOWN','SUBMITTED')
BUILD_FIELDS=('build_id','artifact','context_hash','semantic_hash','review','decision','renderer_version','theme','theme_version','render_hash','assets')

def preview_hash(pub):
    value={k:pub.get(k) for k in INTENT_FIELDS}
    if 'build' in pub:value['build']=pub['build'];value['payload_hash']=pub['payload_hash']
    if 'delivery_confirmation' in pub:value['delivery_confirmation']=pub['delivery_confirmation']
    return digest(value)

def remote_id(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_\-=]{1,256}',value):
        raise Problem('微信回执 ID 无效')
    return value

class CanonicalHTML(HTMLParser):
    def __init__(self): super().__init__(convert_charrefs=True); self.parts=[]
    def handle_starttag(self,tag,attrs): self.parts.append(('start',tag,tuple(sorted(attrs))))
    def handle_startendtag(self,tag,attrs): self.handle_starttag(tag,attrs)
    def handle_endtag(self,tag):
        if tag not in ('br','img','hr'): self.parts.append(('end',tag))
    def handle_data(self,data):
        if data.strip(): self.parts.append(('text',data))
    def handle_comment(self,data): self.parts.append(('comment',data))

def canonical(content):
    p=CanonicalHTML();p.feed(content);return p.parts

def article_matches(payload, remote):
    return (isinstance(remote,dict) and all(remote.get(k,'')==payload.get(k,'') for k in
        ('title','author','digest','content_source_url','thumb_media_id')) and
        all(remote.get(k,0)==payload.get(k,0) for k in ('need_open_comment','only_fans_can_comment')) and
        isinstance(remote.get('content'),str) and canonical(remote['content'])==canonical(payload['content']))

def one_article(value):
    rows=value.get('news_item') if isinstance(value,dict) else None
    if not isinstance(rows,list) or len(rows)!=1 or not isinstance(rows[0],dict):
        raise Problem('只支持可核验的单篇图文；远端文章数量或格式不符',409)
    return rows[0]

def render_content(objects, artifact, vault=None, theme='serif'):
    if vault is not None:return rendering.render(vault,artifact,theme)['token_html']
    text=reader_body(artifact)
    if re.search(r'!\[|!\[\[',text):
        raise Problem('正文含图片：本版需先移除图片引用，或在微信后台排版并手动登记发表。封面可单独上传。')
    # Legacy pure text helper keeps its public calling form; same parser contract.
    class NoAssets:
        def safe(self,path):raise Problem('图片渲染需要 Vault')
    return rendering.render(NoAssets(),{**artifact,'title':artifact.get('title',''),'oc_id':artifact.get('oc_id','legacy')},theme)['token_html']


def legacy_content(artifact):
    """Exact origin/main text contract, exclusively for existing no-build outboxes."""
    text=reader_body(artifact)
    if re.search(r'!\[',text) or artifact.get('pages') or artifact.get('mother_dependency'):
        raise Problem('旧版投递只支持原始纯文本批准稿',409)
    return mistune.create_markdown(escape=True,plugins=['table','strikethrough'])(text)

class Publishing:
    def __init__(self,kernel,adapters=None):
        self.kernel=kernel;self.adapters=adapters or {};self.mutex=threading.RLock();self.locks={};self.cache={}

    def lock(self,aid,channel):
        with self.mutex:return self.locks.setdefault((aid,channel),threading.RLock())

    def configs(self):
        path=self.kernel.vault.safe('.opencontent/channels.json')
        if not path.exists():return {}
        if path.stat().st_size>100_000:raise Problem('渠道配置超过大小限制')
        value=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(value,dict):raise Problem('渠道配置无效')
        return value

    def channels(self):
        result=[{**{k:c[k] for k in ('id','name','appid','kind')},'publish_mode':c.get('publish_mode','draft_only')} for c in self.configs().values()]
        result.extend({'id':key,'name':key,'appid':adapter.identity()['appid'],'kind':'test','publish_mode':'draft_and_publish'} for key,adapter in self.adapters.items())
        return result

    def publish_allowed(self,channel):
        return channel in self.adapters or self.configs().get(channel,{}).get('publish_mode','draft_only')=='draft_and_publish'

    def configure(self,name,appid,secret='',secret_env='',channel_id=None,publish_mode=None):
        if not isinstance(name,str) or not 1<=len(name.strip())<=80 or not isinstance(appid,str) or not re.fullmatch(r'wx[0-9a-fA-F]{16}',appid):
            raise Problem('请填写账号名称及正确的微信 AppID')
        uid=channel_id or uuid.uuid4().hex
        if not re.fullmatch(r'[0-9a-f]{32}',uid):raise Problem('渠道 ID 无效')
        if secret_env and not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',secret_env):raise Problem('环境变量名称无效')
        if not secret and not secret_env:raise Problem('在本地填写 AppSecret 或环境变量名称')
        if publish_mode is not None and publish_mode not in ('draft_only','draft_and_publish'):
            raise Problem('公众号投递模式无效')
        with self.kernel.vault.lock():
            configs=self.configs();key=uuid.uuid4().hex
            mode=publish_mode or configs.get(uid,{}).get('publish_mode','draft_only')
            if secret:credentials.save(self.kernel.vault,key,secret)
            configs[uid]={'id':uid,'name':name.strip(),'appid':appid,'kind':'wechat',
                'credential_id':key,'password_env':secret_env if not secret else '', 'publish_mode':mode}
            atomic(self.kernel.vault.safe('.opencontent/channels.json'),json.dumps(configs,ensure_ascii=False,indent=2).encode())
            self.cache.pop(uid,None)
        return next(c for c in self.channels() if c['id']==uid)

    def adapter(self,channel):
        if channel in self.adapters:return self.adapters[channel]
        config=self.configs().get(channel)
        if not config:raise Problem('请先配置微信公众号渠道',503)
        fingerprint=digest(config)
        with self.mutex:
            if channel not in self.cache or self.cache[channel][0]!=fingerprint:
                self.cache[channel]=(fingerprint,WeChat(config['appid'],credentials.load(self.kernel.vault,config)))
            return self.cache[channel][1]

    def list(self):
        objects,errors=self.kernel.read();rows=[]
        for pub in (p for p in objects.values() if p['type']=='Publication'):
            a=objects.get(pub.get('artifact'));g=self.kernel.quality(objects,a,errors=errors) if a else None
            rows.append({**pub,'current_approval':bool(g and g['approved'] and g['context_hash']==pub.get('context_hash')),
                         'submitted_publication':next((p['oc_id'] for p in objects.values() if p['type']=='Publication' and
                            p.get('draft_publication')==pub['oc_id'] and p.get('delivery_status') not in ('CANCELLED','FAILED')),None),
                         'preview_hash':preview_hash(pub)})
        return {'publications':sorted(rows,key=lambda p:p['created'],reverse=True),'channels':self.channels(),'token':self.kernel.vault.token()}

    def upload_cover(self,channel,path):
        file=self.kernel.vault.safe(path)
        if not file.is_file() or file.stat().st_size>2_000_000:raise Problem('应用封面策略：Vault 内不超过 2 MB 的 JPEG/PNG')
        raw=file.read_bytes();mime=rendering.decode_image(raw)['mime']
        result=self.adapter(channel).upload_cover(raw,mime);mid=remote_id(result.get('media_id'))
        receipt={'channel':channel,'path':path,'hash':digest(raw),'media_id':mid,'at':now()}
        atomic(self.kernel.vault.safe('.opencontent/cover-receipts/'+uuid.uuid4().hex+'.json'),json.dumps(receipt,ensure_ascii=False).encode())
        return receipt

    def verify_legacy(self,objects,pub,artifact,quality):
        if pub.get('build') or pub.get('delivery_assets') or pub.get('payload_hash'):
            raise Problem('不能用旧版兼容路径验证新构建',409)
        if (not quality['approved'] or pub.get('context_hash')!=quality['context_hash'] or
                pub.get('review')!=(quality['review'] or {}).get('oc_id') or
                pub.get('decision')!=(quality['decision'] or {}).get('oc_id') or
                pub['payload'].get('content')!=legacy_content(artifact)):
            raise Problem('旧版载荷与当时批准版本及渲染契约不符，请保留回执并人工核对',409)
        for field in ('title','author','digest'):rendering.public_markdown({'body':pub['payload'].get(field,''),'derived_from':[]})

    def verify_current_build(self,pub,expected=None):
        """Derive authority from the approved Artifact, not self-rehashed outbox data."""
        frozen=pub.get('build');payload=pub.get('payload')
        if not isinstance(frozen,dict) or not isinstance(frozen.get('theme'),str) or not isinstance(payload,dict):
            raise Problem('Invalid frozen publication build',409)
        current=rendering.build(self.kernel,pub['artifact'],expected,frozen['theme'],approved=True)
        authoritative={key:current[key] for key in BUILD_FIELDS}
        if frozen!=authoritative or any(pub.get(key)!=current[key] for key in ('artifact','context_hash','review','decision')):
            raise Problem('Publication build differs from the current approved artifact',409)
        if digest(payload)!=pub.get('payload_hash') or payload.get('content')!=current['token_html']:
            raise Problem('Publication body differs from the authoritative approved render',409)
        return current

    def prepare(self,aid,channel,action,expected,options=None,draft_publication=None):
        if action not in ('draft','publish'):raise Problem('操作必须为送入草稿箱或发表')
        if action=='publish' and not self.publish_allowed(channel):
            raise Problem('当前账号仅送入草稿箱；个人未认证公众号请在微信后台完成发表，再登记文章链接。',403)
        with self.lock(aid,channel):
            k=self.kernel;objects,errors=k.read();a=require_object(objects,aid,'Artifact');g=k.quality(objects,a,errors=errors)
            if not g['approved']:raise Problem('必须先通过当前版本审查并由用户批准')
            if k.vault.token()!=expected:raise Problem('内容已变化，请重新预览',409)
            prior=[p for p in linked(objects,a['project'],'Publication') if p.get('artifact')==aid and p.get('channel')==channel]
            if any(p.get('delivery_status') in UNRESOLVED for p in prior):raise Problem('已有未核验投递，请先恢复回执，禁止重复提交',409)
            if any(p.get('delivery_status')=='PREPARED' for p in prior):raise Problem('已有待确认预览，请先确认或取消',409)
            adapter=self.adapter(channel);identity=adapter.identity();mid=None;before=None
            theme=(options or {}).get('theme','serif')
            construction=rendering.build(k,aid,expected,theme,approved=True)
            frozen={key:construction[key] for key in BUILD_FIELDS}
            if action=='draft':
                if any(p.get('delivery_status') in ('REMOTE_DRAFT','PUBLISHED') and p.get('context_hash')==g['context_hash'] for p in prior):
                    raise Problem('此批准版本已有微信草稿或发表回执，请使用现有记录；修订内容后重新审查才能另行投递',409)
                options=options or {};title=options.get('title',a['title']);author=options.get('author','');summary=options.get('digest','')
                if not isinstance(title,str) or not 1<=len(title)<=32 or not isinstance(author,str) or len(author)>16 or not isinstance(summary,str) or len(summary)>120:
                    raise Problem('微信标题限 32 字、作者限 16 字、摘要限 120 字')
                if not summary:raise Problem('请填写明确摘要，以便回读比对微信保存的内容')
                for value in (title,author,summary):rendering.public_markdown({'body':value,'derived_from':[]})
                payload={'article_type':'news','title':title,'author':author,'digest':summary,'content':construction['token_html'],
                    'content_source_url':'','thumb_media_id':remote_id(options.get('thumb_media_id')),
                    'need_open_comment':0,'only_fans_can_comment':0}
                if len(payload['content'].encode())>20_000:raise Problem('正文超过本版 20 KB 保守投递上限，请精简正文')
            else:
                draft=require_object(objects,draft_publication,'Publication')
                if draft.get('action')!='draft' or draft.get('delivery_status')!='REMOTE_DRAFT' or draft.get('artifact')!=aid or draft.get('channel')!=channel or draft.get('context_hash')!=g['context_hash']:
                    raise Problem('请选择此账号下与当前批准版本一致且已核验的草稿')
                if any(p.get('draft_publication')==draft_publication and p.get('delivery_status') not in ('PREPARED','CANCELLED','FAILED') for p in prior):
                    raise Problem('此草稿已提交过发表；请查询原回执',409)
                mid=remote_id(draft.get('remote_media_id'));payload=deepcopy(draft['payload'])
                if draft.get('destination')!=identity:raise Problem('草稿账号已变化',409)
                if draft.get('build'):
                    self.verify_current_build(draft,expected)
                    frozen=deepcopy(draft['build'])
                if not draft.get('build'):self.verify_legacy(objects,draft,a,g)
                remote=one_article(adapter.get_draft(mid))
                if not article_matches(self.delivery_payload(draft),remote):raise Problem('微信后台草稿已变更；请人工核对，不能以旧批准自动发表',409)
                before=digest(remote)
            pub=k.vault.new('Publication','微信'+('草稿' if action=='draft' else '发表')+' · '+payload['title'],
                '等待用户确认，尚未投递。',a['project'],artifact=aid,channel=channel,destination=identity,
                action=action,delivery_status='PREPARED',context_hash=g['context_hash'],review=g['review']['oc_id'],
                decision=g['decision']['oc_id'],media_id=mid,draft_publication=draft_publication,remote_before_hash=before,
                payload=payload,build=frozen,payload_hash=digest(payload),
                delivery_confirmation=digest(draft.get('delivery_assets',{})) if action=='publish' else digest({}),
                delivery_assets=deepcopy(draft.get('delivery_assets',{})) if action=='publish' else {},
                events=[{'at':now(),'status':'PREPARED'}],url=None,published_at=None)
            if action=='publish':pub['remote_payload_hash']=digest(self.delivery_payload(draft))
            if action=='publish' and not draft.get('build'):
                # Preserve the already confirmed payload without relabelling it
                # as the new styled renderer's output.
                for key in ('build','payload_hash','delivery_assets','delivery_confirmation'):pub.pop(key,None)
            with k.vault.lock():k.vault.commit([pub],expected)
            return {**pub,'preview_hash':preview_hash(pub),'token':k.vault.token()}

    def delivery_payload(self,pub):
        payload=deepcopy(pub['payload'])
        if not pub.get('build'):
            if pub.get('remote_payload_hash') and digest(payload)!=pub['remote_payload_hash']:raise Problem('远端载荷身份不符',409)
            return payload
        if digest(payload)!=pub.get('payload_hash'):raise Problem('冻结载荷被修改',409)
        if set(pub.get('delivery_assets',{}))!={a['hash'] for a in pub['build']['assets']}:raise Problem('上传图片集合与构建不符',409)
        mapping={}
        for asset in pub['build']['assets']:
            receipt=pub.get('delivery_assets',{}).get(asset['hash'])
            if not receipt or receipt.get('status')!='VERIFIED' or receipt.get('hash')!=asset['hash']:
                raise Problem('正文图片上传回执尚未核验',409)
            mapping[asset['token']]=platform_image_url(receipt['url'])
            saved=self.kernel.vault.safe('.opencontent/delivery-assets/'+pub['oc_id']+'/'+asset['hash']+'.json')
            if not saved.exists() and pub.get('draft_publication'):
                saved=self.kernel.vault.safe('.opencontent/delivery-assets/'+pub['draft_publication']+'/'+asset['hash']+'.json')
            if not saved.exists():raise Problem('冻结图片上传身份缺失',409)
            frozen=json.loads(saved.read_text(encoding='utf-8'))
            if frozen.get('url')!=receipt['url'] or frozen.get('hash')!=asset['hash'] or frozen.get('destination',pub['destination'])!=pub['destination']:
                raise Problem('图片回执映射与冻结上传身份不符',409)
        payload['content']=rendering.inline_assets(payload['content'],mapping)
        if pub.get('remote_payload_hash') and digest(payload)!=pub['remote_payload_hash']:
            raise Problem('已确认的远端载荷身份不符，禁止自动恢复或重发',409)
        return payload

    def upload_assets(self,pub,adapter):
        for asset in pub.get('build',{}).get('assets',[]):
            receipts=deepcopy(pub.get('delivery_assets',{}));old=receipts.get(asset['hash'])
            if old:
                if old['status']!='VERIFIED':raise Problem('图片上传结果未知，先只读恢复，禁止重传',409)
                adapter.verify_image(old['url'],asset);continue
            receipts[asset['hash']]={'status':'UPLOADING','hash':asset['hash']}
            pub=self.persist(pub['oc_id'],{'delivery_assets':receipts,'send_phase':'ASSET_UPLOAD'},{'status':'ASSET_UPLOAD'},pub['intent_hash'])
            current,raw=rendering.load_asset(self.kernel.vault,asset['path'])
            if current['hash']!=asset['hash']:raise Problem('上传前图片被替换',409)
            result=adapter.upload_image(raw,asset['mime']);url=platform_image_url(result.get('url'))
            # Save the returned identifier before a network read or domain update can fail.
            receipts[asset['hash']]={'status':'UPLOADED','hash':asset['hash'],'url':url,'destination':pub['destination']}
            recovery=self.kernel.vault.safe('.opencontent/delivery-assets/'+pub['oc_id']+'/'+asset['hash']+'.json')
            atomic(recovery,json.dumps(receipts[asset['hash']]).encode())
            pub=self.persist(pub['oc_id'],{'delivery_assets':receipts},{'status':'ASSET_ACK'},pub['intent_hash'])
            adapter.verify_image(url,asset)
            receipts[asset['hash']]['status']='VERIFIED'
            pub=self.persist(pub['oc_id'],{'delivery_assets':receipts},{'status':'ASSET_VERIFIED'},pub['intent_hash'])
        return pub

    def reconcile_asset(self,uid,asset_hash,url=None):
        initial=require_object(self.kernel.read()[0],uid,'Publication')
        with self.lock(initial['artifact'],initial['channel']):
            pub=require_object(self.kernel.read()[0],uid,'Publication')
            if pub.get('send_phase')!='ASSET_UPLOAD' or pub['delivery_status'] not in ('SENDING','UNKNOWN'):
                raise Problem('此阶段不能恢复图片或重新发送',409)
            if preview_hash(pub)!=pub.get('intent_hash'):raise Problem('投递意图已变化',409)
            adapter=self.adapter(pub['channel'])
            if adapter.identity()!=pub['destination']:raise Problem('账号已变化',409)
            asset=next((a for a in pub['build']['assets'] if a['hash']==asset_hash),None)
            if not asset:raise Problem('资产不属于此投递')
            saved=self.kernel.vault.safe('.opencontent/delivery-assets/'+uid+'/'+asset_hash+'.json')
            receipt=pub.get('delivery_assets',{}).get(asset_hash,{})
            if saved.exists():receipt=json.loads(saved.read_text(encoding='utf-8'))
            candidate=url or receipt.get('url')
            if not candidate:raise Problem('需从平台找回此图片 URL 后只读核验，不能重传',409)
            if receipt.get('url') and receipt['url']!=candidate:raise Problem('禁止替换已有图片回执',409)
            if receipt.get('hash',asset_hash)!=asset_hash or receipt.get('destination',pub['destination'])!=pub['destination']:raise Problem('图片上传身份不符',409)
            adapter.verify_image(platform_image_url(candidate),asset)
            atomic(saved,json.dumps({'hash':asset_hash,'url':candidate,'destination':pub['destination']}).encode())
            receipts=deepcopy(pub['delivery_assets']);receipts[asset_hash]={'status':'VERIFIED','hash':asset_hash,'url':candidate}
            complete=all(receipts.get(a['hash'],{}).get('status')=='VERIFIED' for a in pub['build']['assets'])
            # DRAFT_WRITE has never started in this persisted phase. Require another
            # human confirmation after verified upload recovery; never write here.
            return self.persist(uid,{'delivery_assets':receipts,'delivery_confirmation':digest(receipts),'delivery_status':'PREPARED' if complete else 'UNKNOWN'},
                                {'status':'ASSET_RECOVERY_READ_ONLY'},pub['intent_hash'])

    def persist(self,uid,changes,event,intent=None):
        k=self.kernel
        with k.vault.lock():
            pub=deepcopy(require_object(k.read()[0],uid,'Publication'));token=k.vault.token()
            if intent and preview_hash(pub)!=intent:raise Problem('投递期间回执正文被修改；恢复文件已保留，请人工核对',409)
            pub.update(changes);pub['events']=[*pub.get('events',[]),{'at':now(),**event}]
            k.vault.commit([pub],token);return pub

    def receipt(self,pub,changes):
        # Write acknowledgement before updating Markdown; restart recovery performs reads only.
        intent=preview_hash(pub)
        data={'intent':intent,'changes':changes,'at':now()}
        atomic(self.kernel.vault.safe('.opencontent/delivery-recovery/'+pub['oc_id']+'.json'),json.dumps(data,ensure_ascii=False).encode())
        return self.persist(pub['oc_id'],changes,{'status':changes.get('delivery_status','ACKNOWLEDGED')},intent)

    def confirm(self,uid,confirmation,reviewer,expected):
        k=self.kernel;pub=require_object(k.read()[0],uid,'Publication')
        with self.lock(pub['artifact'],pub['channel']):
            objects,errors=k.read();pub=require_object(objects,uid,'Publication')
            if pub['delivery_status']!='PREPARED':raise Problem('此预览已关闭或已提交，请查询回执',409)
            if pub['action']=='publish' and not self.publish_allowed(pub['channel']):
                raise Problem('当前账号已设为仅送草稿箱，禁止调用发表接口；请在微信后台完成发表。',403)
            if not isinstance(reviewer,str) or not reviewer.strip():raise Problem('请填写确认发表的用户姓名')
            if preview_hash(pub)!=confirmation or k.vault.token()!=expected:raise Problem('预览已变化，请重新核对',409)
            a=require_object(objects,pub['artifact'],'Artifact');g=k.quality(objects,a,errors=errors)
            if not g['approved'] or g['context_hash']!=pub['context_hash'] or g['decision']['oc_id']!=pub['decision']:
                raise Problem('批准版本已变化，请重新审查',409)
            if pub.get('build'):
                self.verify_current_build(pub,expected)
            else:self.verify_legacy(objects,pub,a,g)
            adapter=self.adapter(pub['channel'])
            if adapter.identity()!=pub['destination']:raise Problem('微信公众号账号已变化',409)
            if 'delivery_confirmation' in pub and digest(pub.get('delivery_assets',{}))!=pub['delivery_confirmation']:raise Problem('图片映射在确认后变化，请重新核对',409)
            if pub.get('delivery_assets'):
                self.delivery_payload(pub)
                for asset in pub['build']['assets']:adapter.verify_image(pub['delivery_assets'][asset['hash']]['url'],asset)
            # Token acquisition is not a content write; fail before creating uncertain intent.
            if hasattr(adapter,'token'):adapter.token()
            if pub['action']=='publish' and digest(one_article(adapter.get_draft(pub['media_id'])))!=pub['remote_before_hash']:
                raise Problem('微信草稿在预览后被编辑，已阻止发表',409)
            with k.vault.lock():
                if pub['action']=='publish' and not self.publish_allowed(pub['channel']):
                    raise Problem('投递准备期间账号改为仅送草稿箱，已阻止发表。',403)
                if k.vault.token()!=expected or k.source_issues(k.read()[0],a['project']):raise Problem('投递准备期间本地内容变化',409)
                if pub.get('build'):self.verify_current_build(pub,expected)
                pub=deepcopy(pub);pub.update(delivery_status='SENDING',confirmed_by=reviewer,confirmed_at=now(),intent_hash=confirmation)
                pub['events'].append({'at':now(),'status':'SENDING'});k.vault.commit([pub],expected)
            try:
                if pub['action']=='draft':
                    pub=self.upload_assets(pub,adapter)
                    if pub.get('build'):
                        self.verify_current_build(pub)
                    payload=self.delivery_payload(pub)
                    pub=self.persist(uid,{'send_phase':'DRAFT_WRITE','remote_payload_hash':digest(payload)},{'status':'DRAFT_WRITE'},confirmation)
                    result=adapter.add_draft(payload)
                    # media_id is returned data, not part of the immutable draft intent.
                    changes={'remote_media_id':remote_id(result.get('media_id')),'delivery_status':'UNKNOWN'}
                else:
                    result=adapter.submit(pub['media_id'])
                    changes={'publish_id':remote_id(result.get('publish_id')),'delivery_status':'SUBMITTED'}
                self.receipt(pub,changes)
            except RemoteRejected as e:
                return self.receipt(pub,{'delivery_status':'FAILED','last_error':str(e)})
            except Exception:
                # Do not overwrite a saved acknowledgement if the local domain write failed.
                return self.persist(uid,{'delivery_status':'UNKNOWN','last_error':'提交结果未知；请只读核验。若 ID 丢失，需从微信后台找回。'},
                    {'status':'UNKNOWN'},confirmation)
            try:return self.reconcile(uid)
            except Problem as e:
                return self.persist(uid,{'last_error':str(e)},{'status':'QUERY_FAILED'},confirmation)

    def reconcile(self,uid,recovery_id=None):
        k=self.kernel;initial=require_object(k.read()[0],uid,'Publication')
        if 'channel' not in initial:raise Problem('手动登记没有 API 回执')
        with self.lock(initial['artifact'],initial['channel']):
            pub=require_object(k.read()[0],uid,'Publication')
            if pub['delivery_status'] in ('PREPARED','CANCELLED'):raise Problem('此预览尚未投递或已取消')
            if preview_hash(pub)!=pub.get('intent_hash'):raise Problem('回执投递内容被修改，不能自动恢复',409)
            if pub.get('send_phase')=='ASSET_UPLOAD':raise Problem('尚未发稿；请先只读恢复正文图片回执，禁止重传',409)
            adapter=self.adapter(pub['channel'])
            if adapter.identity()!=pub['destination']:raise Problem('请恢复原公众号配置再核验',409)
            if pub.get('build'):
                if not isinstance(pub.get('remote_payload_hash'),str) or not re.fullmatch(r'[0-9a-f]{64}',pub['remote_payload_hash']):raise Problem('远端载荷冻结身份缺失，禁止自动恢复',409)
                self.delivery_payload(pub)
                for asset in pub['build']['assets']:adapter.verify_image(pub['delivery_assets'][asset['hash']]['url'],asset)
            else:
                objects,errors=k.read();a=require_object(objects,pub['artifact'],'Artifact')
                self.verify_legacy(objects,pub,a,k.quality(objects,a,errors=errors))
            saved=k.vault.safe('.opencontent/delivery-recovery/'+uid+'.json')
            if saved.exists():
                data=json.loads(saved.read_text(encoding='utf-8'))
                if data.get('intent')==preview_hash(pub):
                    # Recover identifiers only; final status always comes from a fresh read.
                    ids={key:data['changes'][key] for key in ('remote_media_id','publish_id','article_id') if data['changes'].get(key)}
                    if ids:pub=self.persist(uid,ids,{'status':'RECOVERY_ID'},pub['intent_hash'])
            if recovery_id:
                key='remote_media_id' if pub['action']=='draft' else 'publish_id'
                if pub.get(key) and pub[key]!=recovery_id:raise Problem('已有回执 ID，不允许替换',409)
                candidate=remote_id(recovery_id)
                # Bind only after readback verifies content; never write with supplied recovery IDs.
            else:candidate=pub.get('remote_media_id' if pub['action']=='draft' else 'publish_id')
            if not candidate:raise Problem('提交 ID 未收到；请在微信后台查找草稿 media_id / 发表 publish_id，再进行只读恢复。不要重复提交。',409)
            if pub['action']=='draft':
                remote=one_article(adapter.get_draft(candidate));valid=article_matches(self.delivery_payload(pub),remote)
                if recovery_id and not valid:raise Problem('提供的恢复 ID 内容与本次投递不匹配',409)
                changes={'remote_media_id':candidate,'delivery_status':'REMOTE_DRAFT' if valid else 'CONFLICT','verified_at':now(),
                    'remote_hash':digest(remote),'last_error':'' if valid else '微信草稿内容与批准投递内容不同'}
            else:
                status=adapter.status(candidate);state=status.get('publish_status')
                if status.get('publish_id',candidate)!=candidate:raise Problem('微信发表查询返回了不同任务 ID',409)
                if type(state) is not int or state not in range(7):raise Problem('微信发表状态无法识别',503)
                if recovery_id and state!=0:raise Problem('手动恢复 ID 须等待发表成功后核验正文；尚不能绑定此 ID',409)
                changes={'publish_id':candidate,'remote_status':state,'verified_at':now(),'last_error':''}
                if state==1:changes['delivery_status']='SUBMITTED'
                elif state in (2,3,4):changes.update(delivery_status='FAILED',last_error={2:'原创审核失败',3:'常规发表失败',4:'平台审核不通过'}[state])
                elif state in (5,6):changes.update(delivery_status='WITHDRAWN',last_error='文章已被删除或封禁')
                else:
                    aid=remote_id(status.get('article_id'));remote=one_article(adapter.article(aid))
                    valid=article_matches(self.delivery_payload(pub),remote)
                    if recovery_id and not valid:raise Problem('恢复任务的文章内容不匹配',409)
                    items=status.get('article_detail',{}).get('item',[])
                    if len(items)!=1:raise Problem('发表回执文章数量不符',409)
                    url=items[0].get('article_url','');parts=urlsplit(url)
                    if parts.scheme!='https' or parts.hostname!='mp.weixin.qq.com' or parts.username or parts.password:
                        raise Problem('发表回执不是有效的微信文章链接',409)
                    changes.update(article_id=aid,url=url,remote_hash=digest(remote),delivery_status='PUBLISHED' if valid else 'CONFLICT',
                        published_at=pub.get('published_at') or now(),last_error='' if valid else '已发表文章与投递内容不同，请人工核对')
            pub=self.receipt(pub,changes)
            if pub['delivery_status']=='PUBLISHED':self.mark_published(pub)
            return pub

    def mark_published(self,pub):
        k=self.kernel
        with k.vault.lock():
            objects,errors=k.read();a=deepcopy(objects[pub['artifact']]);p=deepcopy(objects[pub['project']]);g=k.quality(objects,a,errors=errors)
            if g['approved'] and g['context_hash']==pub['context_hash']:
                token=k.vault.token();a['state']='PUBLISHED';changes=[a]
                # A project is published only when every artifact has a current verified receipt.
                artifacts=linked(objects,pub['project'],'Artifact')
                def has_current_receipt(other):
                    quality=k.quality(objects,other,errors=errors)
                    return quality['approved'] and any(r.get('artifact')==other['oc_id'] and
                        r.get('delivery_status')=='PUBLISHED' and r.get('context_hash')==quality['context_hash']
                        for r in linked(objects,pub['project'],'Publication'))
                complete=all(has_current_receipt(other) for other in artifacts)
                if complete and p['state'] not in ('PUBLISHED','LEARNING'):
                    p['history'].append({'from':p['state'],'to':'PUBLISHED','at':now(),'basis':pub['oc_id']});p['state']='PUBLISHED';changes.append(p)
                if a!=objects[a['oc_id']] or len(changes)>1:k.vault.commit(changes,token)

    def cancel_preview(self,uid,expected):
        pub=require_object(self.kernel.read()[0],uid,'Publication')
        with self.lock(pub['artifact'],pub['channel']),self.kernel.vault.lock():
            pub=require_object(self.kernel.read()[0],uid,'Publication')
            if pub['delivery_status']!='PREPARED' or self.kernel.vault.token()!=expected:raise Problem('仅可取消当前未投递预览',409)
            return self.persist(uid,{'delivery_status':'CANCELLED'},{'status':'CANCELLED'})
