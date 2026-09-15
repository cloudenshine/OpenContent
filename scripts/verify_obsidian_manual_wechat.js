(async()=>{
 const p=app.plugins.plugins.opencontent;const board=await p.api('/board');
 const project=board.projects.find(x=>x.artifacts.some(a=>a.title==='合成验收草稿'&&a.gate.approved));
 if(!project)throw Error('Synthetic approved fixture missing');
 const artifact=project.artifacts.find(a=>a.title==='合成验收草稿'&&a.gate.approved);const detail=await p.api('/objects/'+artifact.oc_id);
 const view=app.workspace.getLeavesOfType('opencontent-cockpit')[0].view;view.manualPublication(artifact,detail);
 const modal=document.querySelector('.oc-modal');const field=(name,value)=>modal.querySelector(`[aria-label="${name}"]`).value=value;
 field('微信文章链接','https://mp.weixin.qq.com/s?software_fixture=manual');field('登记人','软件验收人');field('版本核对与交接说明','人工登记界面软件验收，链接不是实际发表文章。');modal.querySelector('input[type="checkbox"]').checked=true;
 [...modal.querySelectorAll('button')].find(b=>b.textContent==='保存人工发表记录').click();
 for(let i=0;i<40&&document.querySelector('.oc-modal');i++)await new Promise(r=>setTimeout(r,100));
 const list=await p.api('/publications');const pub=list.publications.find(r=>r.url==='https://mp.weixin.qq.com/s?software_fixture=manual');
 if(!pub||pub.delivery_status||!pub.body.includes('软件验收'))throw Error('Manual record not distinct');
 const fs=require('fs');const reportPath='D:/Workspaces/OpenContent/docs/obsidian-lifecycle-v0.4.json';const report=JSON.parse(fs.readFileSync(reportPath,'utf8'));
 report.checks.push({name:'manual_fallback_clearly_distinct_from_api_verification',pass:true});report.manual_check_at=new Date().toISOString();fs.writeFileSync(reportPath,JSON.stringify(report,null,2));
 const file=app.vault.getAbstractFileByPath(pub.path);if(!file||!file.path.startsWith('OpenContent/Publication/'))throw Error('Wrong fixture file');
 await app.vault.rename(file,'_Validation-History/v0.4/Publication/'+file.name);await p.open('publishing');
 return {manual_fallback:'PASS',channels:(await p.api('/publications')).channels.length,diagnostics:(await p.api('/board')).diagnostics};
})()
