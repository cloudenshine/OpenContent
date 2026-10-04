"""Authoritative deterministic Markdown build; no network IO or model execution.

Application policy: PNG/JPEG, <=10 MB, <=24 million pixels, Vault attachment
directories only. These limits are deliberately not claims about platform limits.
"""
import base64
from html import escape
from html.parser import HTMLParser
import io
import ipaddress
import json
from pathlib import Path, PureWindowsPath
import re
from urllib.parse import unquote, urlsplit
import warnings

import mistune
from PIL import Image
from .vault import Problem, digest
from .domain import require_object
from .handoff import reader_body, write_once

RENDERER_VERSION = 'opencontent.image-text.v1'
THEMES = json.loads((Path(__file__).parent/'resources/themes.json').read_text(encoding='utf-8'))
THEME_VERSION = digest(THEMES)
MAX_BYTES = 10_000_000
MAX_PIXELS = 24_000_000


def decode_image(raw):
    if not raw or len(raw) > MAX_BYTES:
        raise Problem('图片超过应用字节上限或为空')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in ('PNG', 'JPEG') or image.width*image.height > MAX_PIXELS or getattr(image, 'n_frames', 1) != 1:
                    raise Problem('仅接受应用像素上限内的静态 PNG/JPEG')
                mime = 'image/png' if image.format == 'PNG' else 'image/jpeg'
                width, height = image.size; image.verify()
            with Image.open(io.BytesIO(raw)) as image: image.load()
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise Problem('图片无法完整解码或超过应用像素上限') from None
    return {'mime':mime, 'size':len(raw), 'width':width, 'height':height, 'hash':digest(raw)}


def asset_path(vault, value):
    value = unquote(value)
    if (not value or '\\' in value or ':' in value or '?' in value or '#' in value or '\x00' in value
            or PureWindowsPath(value).drive or value.startswith('/') or '..' in Path(value).parts):
        raise Problem('图片必须先显式导入 Vault 附件，禁止网络或越界路径')
    # Never expose arbitrary Vault files, settings, credentials, or internal objects.
    if Path(value).parts[0] not in ('Attachments', 'attachments', 'assets'):
        raise Problem('图片只允许使用 Attachments、attachments 或 assets 内已导入附件')
    if Path(value).suffix.lower() not in ('.png', '.jpg', '.jpeg'):
        raise Problem('导出图片文件名必须使用 PNG/JPG/JPEG 扩展名')
    return value, vault.safe(value)


def load_asset(vault, value, alt='', position=0, caption=''):
    relative, path = asset_path(vault, value)
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise Problem('图片缺失或超过应用字节上限')
    raw = path.read_bytes()
    return {'path':relative, **decode_image(raw), 'alt':alt, 'position':position, 'caption':caption}, raw


def safe_link(value):
    if any(ord(c) < 32 for c in value) or '\\' in value:
        raise Problem('危险链接被阻止')
    try:
        p = urlsplit(value)
        if p.scheme != 'https' or not p.hostname or p.username or p.password or p.port not in (None,443):
            raise ValueError()
        host=p.hostname.lower()
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if host=='localhost' or '.' not in host or host.endswith(('.local','.localhost','.internal')):raise ValueError()
            if ':' in host or re.fullmatch(r'(?:0x[0-9a-f]+|\d+)(?:\.(?:0x[0-9a-f]+|\d+)){0,3}',host):raise ValueError()
            if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', host): raise ValueError()
        else:
            mapped = getattr(address, 'ipv4_mapped', None)
            if not address.is_global or mapped is not None and not mapped.is_global: raise ValueError()
        return value
    except ValueError:
        raise Problem('只接受公开 HTTPS 链接，禁止危险协议与私网链接') from None


def public_markdown(artifact):
    text = reader_body(artifact)
    if text.startswith('---\n'):
        pieces = text.split('\n---\n',1)
        if len(pieces) != 2: raise Problem('正文 frontmatter 无法安全移除')
        text = pieces[1].lstrip()
    if re.search(r'\[\[[0-9a-f]{32}(?:\||\]\])',text):
        raise Problem('正文含未登记内部 Claim ID')
    # Imported image paths contain task identities. Their URL is validated by
    # ArticleRenderer; only visible prose/alt/captions must reject internal IDs.
    visible=re.sub(r'(!\[[^\]]*\])\(([^\s)]+)([^)]*)\)',r'\1\3',text)
    if re.search(r'(?<![0-9a-f])[0-9a-f]{32}(?![0-9a-f])', visible) or any(cid in visible for cid in artifact.get('derived_from',[])):
        raise Problem('正文直接暴露内部 Claim ID')
    if re.search(r'(?:(?<![A-Za-z0-9])[A-Za-z]:[\\/]|file://|/(?:Users|home|root|tmp|etc|var|mnt|private|Volumes)/|\\\\[^\s\\]+\\)',text):
        raise Problem('读者正文含机器绝对路径，请先删除')
    return text


class ArticleRenderer(mistune.HTMLRenderer):
    def __init__(self, vault, asset_sink=None):
        super().__init__(escape=True); self.vault=vault; self.assets=[]; self.data={}; self.asset_sink=asset_sink

    def image(self, text, url, title=None):
        alt=re.sub('<[^>]+>','',text)
        for value in (alt,title or alt):public_markdown({'body':value,'derived_from':[]})
        asset, raw=load_asset(self.vault,url,alt,len(self.assets),title or alt)
        token='oc-asset:'+asset['hash']; asset['token']=token
        if self.asset_sink is not None: self.asset_sink[asset['hash']]=raw
        self.assets.append(asset); self.data[token]='data:'+asset['mime']+';base64,'+base64.b64encode(raw).decode()
        return '<img src="'+token+'" alt="'+escape(alt,quote=True)+'"><br><em>'+escape(title or alt)+'</em>'

    def link(self, text, url, title=None):
        return super().link(text, safe_link(url), title)


class StyleHTML(HTMLParser):
    """Add fixed theme styles to trusted parser output, never authored CSS/HTML."""
    def __init__(self, theme):
        super().__init__(convert_charrefs=False); self.theme=theme; self.parts=[]
    def handle_starttag(self,tag,attrs):
        key={'section':'containerStyle','h1':'h1Style','h2':'h2Style','h3':'h3Style','p':'pStyle',
             'blockquote':'blockquoteStyle','strong':'strongStyle','code':'codeStyle','ul':'listStyle','ol':'listStyle','hr':'dividerStyle'}.get(tag)
        style=self.theme.get(key,'') if key else {'img':'max-width:100%;height:auto;', 'table':'border-collapse:collapse;width:100%;',
              'td':'border:1px solid #aaa;padding:8px;', 'th':'border:1px solid #aaa;padding:8px;',
              'pre':'white-space:pre-wrap;overflow-wrap:anywhere;'}.get(tag,'')
        if style: attrs=[*attrs,('style',style)]
        self.parts.append('<'+tag+''.join(' '+k+'="'+escape(v or '',quote=True)+'"' for k,v in attrs)+'>')
    def handle_endtag(self,tag): self.parts.append('</'+tag+'>')
    def handle_data(self,data): self.parts.append(data)
    def handle_entityref(self,name): self.parts.append('&'+name+';')
    def handle_charref(self,name): self.parts.append('&#'+name+';')


def render(vault, artifact, theme='serif', asset_sink=None):
    if theme not in THEMES: raise Problem('未知排版主题')
    public_markdown({'body':artifact.get('title',''),'derived_from':[]})
    text=public_markdown(artifact); renderer=ArticleRenderer(vault, asset_sink)
    body=mistune.create_markdown(renderer=renderer,plugins=['table','strikethrough'])(text)
    parser=StyleHTML(THEMES[theme]); parser.feed('<section><h1>'+escape(artifact['title'])+'</h1>'+body+'</section>')
    frozen=''.join(parser.parts)
    semantic=digest({'artifact':artifact['oc_id'],'title':artifact['title'],'body':artifact['body'],'assets':renderer.assets,
                     'mother':artifact.get('mother_dependency'),'pages':artifact.get('pages')})
    return {'renderer_version':RENDERER_VERSION,'theme':theme,'theme_version':THEME_VERSION,'render_hash':digest(frozen),
            'semantic_hash':semantic,'assets':renderer.assets,'token_html':frozen,'markdown':'# '+artifact['title']+'\n\n'+text,
            'html':inline_assets(frozen,renderer.data)}


def inline_assets(content, mapping):
    return re.sub(r'src="(oc-asset:[0-9a-f]{64})"',lambda m:'src="'+escape(mapping[m[1]],quote=True)+'"',content)


def complete_semantic(vault, artifact, result, asset_sink=None):
    page_assets=[]
    for index,page in enumerate(artifact.get('pages',[])):
        for resource in page.get('resources',[]):
            asset,raw=load_asset(vault,resource,position=index);page_assets.append(asset)
            if asset_sink is not None: asset_sink[asset['hash']]=raw
    result['page_assets']=page_assets
    return digest({'semantic':result['semantic_hash'],'page_assets':page_assets}) if page_assets else result['semantic_hash']


def semantic_binding(kernel, artifact):
    result=render(kernel.vault,artifact)
    binding=complete_semantic(kernel.vault, artifact, result)
    return binding if result['assets'] or artifact.get('mother_dependency') or artifact.get('pages') else None


def build(kernel, aid, expected=None, theme='serif', approved=False, asset_sink=None):
    with kernel.vault.mutex:
        if expected is not None and kernel.vault.token()!=expected: raise Problem('构建输入已变化',409)
        objects,errors=kernel.read(); a=require_object(objects,aid,'Artifact')
        quality=kernel.quality(objects,a,errors=errors)
        if quality.get('dependency_status')=='STALE':raise Problem('母稿变化，渠道稿已过期',409)
        if approved and not quality['approved']: raise Problem('正式交付必须独立审查并人工批准当前稿件',409)
        result=render(kernel.vault,a,theme,asset_sink)
        observed=complete_semantic(kernel.vault,a,result,asset_sink)
        if quality.get('semantic_hash') and observed != quality['semantic_hash']:
            raise Problem('图片或页面资源在批准检查与构建之间变化',409)
        result['semantic_hash']=observed
        if expected is not None and kernel.vault.token()!=expected:raise Problem('构建期间输入变化',409)
        identity={'artifact':aid,'context_hash':quality['context_hash'],'semantic_hash':result['semantic_hash'],
                  'review':(quality['review'] or {}).get('oc_id'),'decision':(quality['decision'] or {}).get('oc_id'),
                  'renderer_version':result['renderer_version'],'theme':theme,'theme_version':THEME_VERSION,
                  'render_hash':result['render_hash'],'assets':result['assets']}
        return {**result,**identity,'build_id':digest(identity),'status':'APPROVED_BUILD' if quality['approved'] else 'UNAPPROVED_PREVIEW',
                'token':kernel.vault.token()}


def export_build(kernel, aid, expected, theme='serif'):
    with kernel.vault.lock():
        frozen={}
        result=build(kernel,aid,expected,theme,approved=True,asset_sink=frozen)
        relative='OpenContent-Exports/'+aid+'/'+result['build_id']
        root=kernel.vault.safe(relative)
        write_once(root/'article.md',result['markdown'].encode())
        write_once(root/'preview.html',document(result['html']).encode())
        for asset in result['assets']:
            raw=frozen[asset['hash']]
            if digest(raw)!=asset['hash']:raise Problem('冻结图片校验失败',409)
            write_once(root/asset['path'],raw)
        if build(kernel,aid,theme=theme,approved=True)['build_id']!=result['build_id'] or kernel.vault.token()!=expected:
            raise Problem('导出期间正文、批准或依赖变化；未创建有效交付清单',409)
        manifest={k:v for k,v in result.items() if k not in ('html','token_html','markdown','token')}
        write_once(root/'manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2).encode())
        return {**manifest,'path':relative,'status':'LOCAL_HANDOFF_ONLY'}


def document(content):
    return '<!doctype html><html lang="zh"><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data:; style-src \'unsafe-inline\'"><title>OpenContent preview</title><body>'+content+'</body></html>'
