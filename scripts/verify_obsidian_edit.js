(async()=>{
  const plugin=app.plugins.plugins.opencontent;
  const board=await plugin.api('/board');
  const project=board.projects.find(p=>p.title==='软件门禁验收样本（合成内容与审查）');
  const artifact=project.artifacts[0];
  if(!artifact.gate.approved)throw new Error('Synthetic fixture must begin approved');
  const file=app.vault.getAbstractFileByPath(artifact.path);
  const original=await app.vault.read(file);
  const changed=original+'\n软件验收中的外部编辑：这次变更必须使原批准失效。\n';
  let evidence;
  try{
    await app.vault.process(file,current=>{if(current!==original)throw new Error('Concurrent edit');return changed;});
    const detail=await plugin.api('/objects/'+artifact.oc_id);
    if(detail.gate.approved||detail.gate.status!=='BLOCKED')throw new Error('Approval survived edit');
    const view=app.workspace.getLeavesOfType('opencontent-cockpit')[0].view;
    view.selected=project.oc_id;view.artifact=artifact.oc_id;view.tab='inspector';await view.render();
    const diff=[...document.querySelectorAll('.oc-root details')].find(d=>d.querySelector('summary')?.textContent.includes('Diff'));
    diff.open=true;
    if(!diff.innerText.includes('软件验收中的外部编辑'))throw new Error('Diff did not show current edit');
    evidence={at:new Date().toISOString(),artifact:artifact.oc_id,editInvalidatedApproval:true,diffRendered:true,issues:detail.gate.issues};
  }finally{
    await app.vault.process(file,current=>{if(current!==changed)throw new Error('External edit encountered; original not restored');return original;});
  }
  evidence.originalRestored=(await plugin.api('/objects/'+artifact.oc_id)).gate.approved;
  return evidence;
})()
