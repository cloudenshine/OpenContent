(async()=>{
  const plugin=app.plugins.plugins.opencontent;
  const before=await plugin.api('/jobs');
  if(!before.some(j=>j.status==='RUNNING'))throw new Error('No live agent job: responsiveness evidence requires concurrent execution');
  const started=performance.now();
  const view=app.workspace.getLeavesOfType('opencontent-cockpit')[0].view;
  view.tab='inbox';await view.render();
  const inboxRendered=document.querySelector('.oc-root').innerText.includes('需要你的判断');
  view.tab='project';await view.render();
  let file=app.vault.getAbstractFileByPath('响应性验收.md');
  if(!file)file=await app.vault.create('响应性验收.md','# 宿主响应性验收\n\n任务运行时可以继续打开和编辑普通笔记。\n');
  const leaf=app.workspace.getLeaf('split');await leaf.openFile(file);
  const editor=leaf.view.editor;
  if(!editor)throw new Error('Native Markdown editor missing');
  editor.setCursor({line:0,ch:0});
  const nativeEditorAvailable=editor.getValue().includes('宿主响应性验收');
  const elapsedMs=performance.now()-started;
  const after=await plugin.api('/jobs');
  const evidence={at:new Date().toISOString(),vault:app.vault.getName(),before:before[0].status,after:after[0].status,inboxRendered,nativeEditorAvailable,elapsedMs};
  if(!inboxRendered||!nativeEditorAvailable)throw new Error(JSON.stringify(evidence));
  return evidence;
})()
