// Preserve earlier generated UI-test attempts outside the active domain folder.
(async()=>{
  if(app.vault.adapter.getBasePath()!=='D:\\Workspaces\\OpenContent\\validation-vault')throw new Error('Wrong Vault');
  const p=app.plugins.plugins.opencontent,keep=window.ocWorkflowEvidence.project;
  const board=await p.api('/board');
  if(board.jobs.some(j=>['QUEUED','RUNNING'].includes(j.status)))throw new Error('Active job');
  const candidates=board.projects.filter(o=>o.title.startsWith('v0.3 原生工作流验收 ')&&o.oc_id!==keep);
  const planned=[];
  for(const project of candidates){
    const detail=await p.api('/objects/'+project.oc_id);
    if(project.state!=='CAPTURED'||detail.objects.some(o=>o.type!=='Material'||!o.title.startsWith('v0.3-原生捕获验收-')))throw new Error('Unexpected fixture content');
    for(const object of [project,...detail.objects]){
      if(!/^OpenContent\/(Project|Material)\/[0-9a-f]{32}\.md$/.test(object.path))throw new Error('Unexpected path');
      planned.push({from:object.path,to:'_Validation-History/v0.3/'+object.type+'/'+object.oc_id+'.md'});
    }
  }
  for(const folder of ['_Validation-History','_Validation-History/v0.3','_Validation-History/v0.3/Project','_Validation-History/v0.3/Material']){
    if(!app.vault.getAbstractFileByPath(folder))await app.vault.createFolder(folder);
  }
  for(const move of planned){
    if(!move.to.startsWith('_Validation-History/v0.3/')||app.vault.getAbstractFileByPath(move.to))throw new Error('Unsafe target');
    await app.vault.rename(app.vault.getAbstractFileByPath(move.from),move.to);
  }
  await p.open('board');return {archived:planned,kept:keep};
})()
