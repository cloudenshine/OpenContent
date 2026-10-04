"""WeChat Official Accounts API. Fixed destination, bounded IO, no write retries."""
import json
import threading
import time
import urllib.request
import urllib.parse
import uuid
from .vault import Problem

class UnknownOutcome(Problem): pass
class RemoteRejected(Problem): pass


def platform_image_url(url):
    try:
        p=urllib.parse.urlsplit(url)
        if p.scheme!='https' or p.hostname not in ('mmbiz.qpic.cn','mmbiz.qlogo.cn') or p.username or p.password or p.port not in (None,443):
            raise ValueError()
        return url
    except (ValueError,TypeError):raise Problem('正文图片回执不是受信任的微信 HTTPS 资源 URL') from None

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None

class WeChat:
    def __init__(self, appid, secret, transport=None):
        self.appid, self.secret = appid, secret
        self.transport = transport or self.http
        self.cached_token = ''; self.expires = 0
        self.mutex = threading.RLock()

    def identity(self): return {'kind':'wechat', 'appid':self.appid}

    @staticmethod
    def http(path, body, content_type, write):
        request = urllib.request.Request('https://api.weixin.qq.com'+path, data=body,
            headers={'Content-Type':content_type}, method='POST')
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        try:
            with opener.open(request, timeout=15) as response:
                raw = response.read(2_000_001)
                if len(raw)>2_000_000: raise ValueError('oversized')
                value = json.loads(raw)
                if not isinstance(value,dict): raise ValueError('invalid object')
                return value
        except Exception:
            error = UnknownOutcome if write else Problem
            raise error('微信连接失败或响应无法核验；写入结果可能未知，请查询回执，勿重复提交。',503) from None

    @staticmethod
    def check(value):
        if not isinstance(value,dict): raise UnknownOutcome('微信响应格式无法核验',503)
        code = value.get('errcode',0)
        if code != 0:
            hints={48001:'账号没有此接口权限，请检查认证及接口权限。',40164:'请在微信后台配置当前出口 IP 白名单。',
                40001:'访问令牌无效。',40013:'AppID 无效。',40125:'AppSecret 无效。',
                40007:'素材 ID 无效或不属于当前账号。',53503:'草稿未通过检查，请在微信后台核对。',
                53504:'此草稿需要在微信后台发表。',53505:'请先在微信后台保存草稿。'}
            if type(code) is not int: raise UnknownOutcome('微信错误响应无法核验',503)
            if code == -1: raise UnknownOutcome('微信系统繁忙，写入结果须核验。',503)
            raise RemoteRejected(f'微信接口错误 {code}：'+hints.get(code,'请检查账号权限及请求内容。'),422)
        return value

    def token(self):
        with self.mutex:
            if self.cached_token and time.monotonic()<self.expires: return self.cached_token
            body={'grant_type':'client_credential','appid':self.appid,'secret':self.secret,'force_refresh':False}
            value=self.check(self.transport('/cgi-bin/stable_token',json.dumps(body).encode(),'application/json',False))
            token=value.get('access_token'); expires=value.get('expires_in')
            if not isinstance(token,str) or not token or type(expires) is not int or expires<60:
                raise Problem('微信访问令牌响应无效',503)
            self.cached_token=token; self.expires=time.monotonic()+expires-60
            return token

    def call(self, endpoint, payload, write=False):
        value=self.transport('/cgi-bin/'+endpoint+'?access_token='+urllib.parse.quote(self.token(),safe=''),
            json.dumps(payload,ensure_ascii=False).encode('utf-8'),'application/json; charset=utf-8',write)
        if isinstance(value,dict) and value.get('errcode') in (40001,40014,42001):
            self.cached_token=''; self.expires=0
        return self.check(value)

    def add_draft(self, article): return self.call('draft/add',{'articles':[article]},True)
    def get_draft(self, media_id): return self.call('draft/get',{'media_id':media_id})
    def submit(self, media_id): return self.call('freepublish/submit',{'media_id':media_id},True)
    def status(self, publish_id): return self.call('freepublish/get',{'publish_id':publish_id})
    def article(self, article_id): return self.call('freepublish/getarticle',{'article_id':article_id})

    def upload_cover(self, raw, mime):
        boundary='OpenContent'+uuid.uuid4().hex
        extension='png' if mime=='image/png' else 'jpg'
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="media"; filename="cover.{extension}"\r\n'
              f'Content-Type: {mime}\r\n\r\n').encode()+raw+f'\r\n--{boundary}--\r\n'.encode()
        path='/cgi-bin/material/add_material?type=image&access_token='+urllib.parse.quote(self.token(),safe='')
        return self.check(self.transport(path,body,'multipart/form-data; boundary='+boundary,True))

    def upload_image(self, raw, mime):
        boundary='OpenContent'+uuid.uuid4().hex
        extension='png' if mime=='image/png' else 'jpg'
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="media"; filename="body.{extension}"\r\n'
              f'Content-Type: {mime}\r\n\r\n').encode()+raw+f'\r\n--{boundary}--\r\n'.encode()
        path='/cgi-bin/media/uploadimg?access_token='+urllib.parse.quote(self.token(),safe='')
        value=self.check(self.transport(path,body,'multipart/form-data; boundary='+boundary,True))
        platform_image_url(value.get('url'))
        return value

    def verify_image(self, url, asset):
        from .rendering import decode_image, MAX_BYTES
        url=platform_image_url(url)
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        try:
            with opener.open(urllib.request.Request(url),timeout=15) as response:raw=response.read(MAX_BYTES+1)
            remote=decode_image(raw)
            # A platform transform is not silently trusted. Explicit import/rebuild is
            # required when remote bytes differ from the frozen local asset.
            if remote['hash']!=asset['hash']:raise ValueError()
            return {'url':url,'hash':remote['hash'],'width':remote['width'],'height':remote['height']}
        except Exception:raise Problem('平台图片回读与冻结资产不符或无法核验；禁止投递',409) from None
