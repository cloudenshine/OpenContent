"""Read-only official documentation capture. No accounts or API credentials."""
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
import json
from pathlib import Path
import urllib.request

root=Path(__file__).resolve().parent.parent/'docs'/'market-evidence'/'wechat'
root.mkdir(parents=True,exist_ok=True)
class Text(HTMLParser):
    def __init__(self):super().__init__();self.parts=[];self.links=[];self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'):self.skip+=1
        if tag=='a':self.links.extend(v for k,v in attrs if k=='href')
    def handle_endtag(self,tag):
        if tag in ('script','style'):self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip and data.strip():self.parts.append(data.strip())
urls={
    'token':'https://developers.weixin.qq.com/doc/service/api/base/api_getstableaccesstoken.html',
    'draft-get':'https://developers.weixin.qq.com/doc/service/api/draftbox/draftmanage/api_getdraft.html',
    'article-get':'https://developers.weixin.qq.com/doc/service/api/public/api_freepublishgetarticle.html',
    'cover-upload':'https://developers.weixin.qq.com/doc/service/api/material/permanent/api_addmaterial.html',
    'publish-status':'https://developers.weixin.qq.com/doc/subscription/api/public/api_freepublish_get.html',
    'publish-submit':'https://developers.weixin.qq.com/doc/subscription/api/public/api_freepublish_submit.html',
    'draft-add':'https://developers.weixin.qq.com/doc/service/api/draftbox/draftmanage/api_draft_add',
}
def fetch(item):
    name,url=item
    data=urllib.request.urlopen(url,timeout=25).read(2_000_000).decode('utf-8')
    p=Text();p.feed(data);text='\n'.join(p.parts)
    (root/(name+'.txt')).write_text(text,encoding='utf-8')
    (root/(name+'-links.json')).write_text(json.dumps(p.links,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'name':name,'url':url,'characters':len(text)},ensure_ascii=False))
with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(fetch,urls.items()))
