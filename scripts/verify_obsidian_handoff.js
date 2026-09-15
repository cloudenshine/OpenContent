(async()=>{
  if(app.vault.adapter.getBasePath()!=='D:\\Workspaces\\OpenContent\\validation-vault')throw new Error('Wrong Vault');
  const p=app.plugins.plugins.opencontent, aid='82c7bb494c1548e6950bd8751a034b7c';
  const checks=[];const check=(name,ok)=>{checks.push({name,pass:Boolean(ok)});if(!ok)throw new Error(name);};
  const wait=async test=>{for(let i=0;i<80;i++){if(await test())return;await new Promise(r=>setTimeout(r,100));}throw new Error('UI wait timed out');};
  const click=(scope,label)=>{const b=[...scope.querySelectorAll('button')].find(b=>b.textContent===label);if(!b)throw new Error('Missing button '+label);b.click();};
  const detail=await p.api('/objects/'+aid);
  check('fixture_is_explicitly_synthetic_and_approved',detail.object.title==='合成验收草稿'&&detail.gate.approved);
  await p.open('inspector');const view=app.workspace.getLeavesOfType('opencontent-cockpit')[0].view;
  view.selected=detail.object.project;view.artifact=aid;await view.render();
  click(document.querySelector('.oc-root'),'交付 Markdown / Ailu');
  await wait(()=>document.querySelector('.oc-modal'));
  check('handoff_discloses_local_only',document.querySelector('.oc-modal').textContent.includes('不上传、不标记已发布'));
  click(document.querySelector('.oc-modal'),'生成并打开交付稿');
  await wait(()=>p.editorLeaf?.view.file?.path.startsWith('OpenContent-Exports/'));
  const file=p.editorLeaf.view.file;const body=await app.vault.read(file);
  check('approved_file_opened_in_native_editor',body.includes('[^oc1]')&&!body.includes('[['));
  check('handoff_does_not_publish',(await p.api('/objects/'+aid)).project.state==='APPROVED');
  const real=await p.api('/objects/9db0eba7dddc4a07a46d5df7ffdf45d8');
  check('real_article_still_requires_human',!real.gate.approved);
  view.selected=real.object.project;view.artifact=real.object.oc_id;await view.render();
  check('unapproved_article_has_no_handoff_button',![...document.querySelectorAll('.oc-root button')].some(b=>b.textContent==='交付 Markdown / Ailu'));
  await p.open('board');await new Promise(r=>setTimeout(r,3000));
  const api=p.api;let calls=0;
  p.api=async function(route,...args){if(route==='/board')calls++;return api.call(this,route,...args);};
  let idleCalls,refreshCalls;
  try{
    await new Promise(r=>setTimeout(r,6500));idleCalls=calls;
    // A genuine Vault modify event must refresh, then restore this software-test source.
    const project=window.ocWorkflowEvidence.project;const d=await p.api('/objects/'+project);
    const m=app.vault.getAbstractFileByPath(d.objects.find(o=>o.type==='Material').path);const original=await app.vault.read(m);
    try{await app.vault.modify(m,original+'\nIdle refresh fixture\n');await wait(()=>calls>idleCalls);refreshCalls=calls-idleCalls;}
    finally{await app.vault.modify(m,original);}
  }finally{p.api=api;}
  check('idle_view_makes_zero_board_requests',idleCalls===0);
  check('vault_edit_triggers_refresh',refreshCalls>0);
  const evidence={...window.ocWorkflowEvidence,completed_at:new Date().toISOString(),handoff:file.path,idle_window_ms:6500,idle_board_requests:idleCalls,checks:[...window.ocWorkflowEvidence.checks,...checks]};
  window.ocWorkflowEvidence=evidence;return evidence;
})()
