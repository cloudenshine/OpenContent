"""Prepare a self-contained opt-in trial; explicit files only, no user Vault or runtime logs."""
import hashlib
import json
from pathlib import Path
import zipfile
from release_files import plugin_files
ROOT=Path(__file__).resolve().parent.parent

def build(root=ROOT):
    root=Path(root);version=json.loads((root/'plugin/manifest.json').read_text(encoding='utf-8'))['version']
    suite=json.loads((root/'tests/fixtures/ideation-quality.json').read_text(encoding='utf-8'))
    files={'START-HERE.md':(root/'docs/TRIAL-QUICKSTART.md').read_bytes(),
           'PRIVACY.md':(root/'PRIVACY.md').read_bytes(),'LICENSE':(root/'LICENSE').read_bytes(),
           'quality/ideation-quality.json':(root/'tests/fixtures/ideation-quality.json').read_bytes(),
           'trial-status.json':json.dumps({'version':version,'external_participants':0,'external_trial':'NOT_STARTED','editorial_review':'PENDING','host_ui':'NOT_VERIFIED','public_release':'BLOCKED'},indent=2).encode()}
    for name in ('first-use','return-use','host-checks','editorial-review'):
        files['feedback/'+name+'.csv']=(root/('docs/trial-forms/'+name+'.csv')).read_bytes()
    for source,relative in plugin_files(root):files['SampleVault/.obsidian/plugins/opencontent/'+relative]=source.read_bytes()
    files['SampleVault/.obsidian/community-plugins.json']=b'["opencontent"]'
    files['SampleVault/Welcome.md']='# 人工编写的试用仓库\n\n先阅读包内 START-HERE.md。Research 是聚焦资料，SameOrigin 是同源检查演示。材料仅用于软件测试，不是现实研究证据。\n'.encode()
    for category,directory in [('focused','Research'),('same-origin','SameOrigin')]:
        case=next(c for c in suite['cases'] if c['category']==category)
        for note in case['notes']:files['SampleVault/'+directory+'/'+note['name']]=note['body'].encode()
    files['FILES.sha256.json']=json.dumps({name:hashlib.sha256(data).hexdigest() for name,data in files.items()},indent=2).encode()
    dist=root/'dist';dist.mkdir(exist_ok=True);target=dist/f'opencontent-trial-{version}.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,data in files.items():archive.writestr(name,data)
    with zipfile.ZipFile(target) as archive:assert archive.testzip() is None
    return {'archive':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'files':len(files),'external_trial':'NOT_STARTED'}

if __name__=='__main__':print(json.dumps(build(),ensure_ascii=False,indent=2))
