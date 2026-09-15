"""Create an isolated profile; never modify the user's registered Vaults."""
import hashlib
import json
from pathlib import Path
import shutil
import time

root=Path(__file__).resolve().parent.parent
vault=root/'validation-vault';profile=root/'.validation-profile'
vault.mkdir(exist_ok=True);profile.mkdir(exist_ok=True)
vid=hashlib.sha256(str(vault).encode()).hexdigest()[:16]
(profile/'obsidian.json').write_text(json.dumps({'vaults':{vid:{'path':str(vault),'ts':int(time.time()*1000),'open':True}}}),encoding='utf-8')
(vault/'.obsidian').mkdir(exist_ok=True)
(vault/'.obsidian'/'community-plugins.json').write_text('["opencontent"]',encoding='utf-8')
(vault/'.obsidian'/'app.json').write_text('{"safeMode": false}',encoding='utf-8')
# Use the already-installed application update, without network download or installation.
source=Path.home()/'AppData'/'Roaming'/'obsidian'/'obsidian-1.13.7.asar'
if source.exists():shutil.copy2(source,profile/source.name)
(vault/'验收材料.md').write_text('# 内容生产与可追溯性\n\n这是一份本地产品设计备忘录，供真实 Agent 提炼和批判，不代表外部实证研究。\n\n内容生产系统应将用户可读的 Markdown 作为知识与内容的真源。任务队列、锁和执行轨迹可以保存在 SQLite 中。\n\n材料、知识、主张与证据之间需要保留来源关系。文章的重要主张应能回到所引用的原文，证据不足时应阻止批准。\n\n自动审查可以提出意见，但最终批准应由用户作出。正文、资料或编辑政策变化后，旧的批准不能继续代表新版本。\n\n这组原则的限制是：精确引文匹配不能证明语义正确，保留来源也不能保证来源本身可靠。质量判断仍需说明理由。\n',encoding='utf-8')
print(json.dumps({'profile':str(profile),'vault':str(vault),'vault_id':vid},ensure_ascii=False))
