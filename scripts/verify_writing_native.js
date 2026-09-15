// Execute only through scripts/obsidian_cdp.mjs in the dedicated UX fixture vault.
(async()=>{
  const expected='D:\\Workspaces\\codex_work\\OpenContent\\.ux-validation\\vault';
  if(app.vault.adapter.getBasePath()!==expected)throw Error('Wrong validation vault');
  const plugin=app.plugins.plugins.opencontent;
  const checks=[];
  const check=(name,pass)=>{checks.push({name,pass:!!pass});if(!pass)throw Error(name);};
  const wait=async predicate=>{for(let i=0;i<100;i++){if(await predicate())return;await new Promise(r=>setTimeout(r,100));}throw Error('Timed out');};
  const file=app.vault.getAbstractFileByPath('读书笔记.md')||await app.vault.create('读书笔记.md','# 把笔记变成文章\n\n先明确想写给谁，再选一两段读书笔记作为资料。围绕一个具体问题写作，比把全部摘录堆在一起更容易理解。\n');
  await plugin.openNote(file.path);await plugin.open('board');
  const view=app.workspace.getLeavesOfType('opencontent-cockpit')[0].view;
  await view.render();
  const root=()=>view.contentEl;
  const nav=[...root().querySelectorAll('.oc-nav>button')].map(b=>b.textContent);
  check('three_primary_navigation_items',JSON.stringify(nav)===JSON.stringify(['首页','写作','发布']));
  check('current_note_visible',root().innerText.includes('使用当前笔记：读书笔记'));
  const providers=await plugin.api('/providers');check('local_cli_automatically_available',Object.keys(providers.active).length>0);
  const input=root().querySelector('[aria-label="告诉我你的想法"]');
  const goal='给新手写一篇读书笔记指南 · 界面验收 '+Date.now();
  input.value=goal;input.dispatchEvent(new Event('input',{bubbles:true}));
  await view.render();check('home_input_survives_refresh',root().querySelector('[aria-label="告诉我你的想法"]').value===goal);
  const before=(await plugin.api('/board')).projects.length;
  const original=plugin.api;let submitted;
  plugin.api=async function(route,body){if(route==='/jobs'){submitted=body;throw Error('界面验收：模拟助手暂不可用');}return original.call(this,route,body);};
  try{
    [...root().querySelectorAll('button')].find(b=>b.textContent==='开始写作').click();
    await wait(()=>view.tab==='project'&&root().innerText.includes('文章已保存，助手暂未开始'));
  }finally{plugin.api=original;}
  const after=await plugin.api('/board');
  check('one_click_creates_exactly_one_article',after.projects.length===before+1);
  const project=after.projects.find(p=>p.title===goal);
  check('selected_note_captured_once',project?.counts.Material===1);
  check('production_receives_fresh_token',submitted?.project===project.oc_id&&typeof submitted.token==='string');
  check('failed_generation_stays_in_saved_article',view.selected===project.oc_id&&root().innerText.includes('无需重新创建'));
  await wait(()=>root().querySelector('.oc-composer'));
  check('writing_and_conversation_share_page',!!root().querySelector('.oc-composer'));
  const editor=root().querySelector('[aria-label="给这个项目的指令"]');editor.value='这句话还没有发送';editor.dispatchEvent(new Event('input',{bubbles:true}));await view.render();
  check('conversation_input_survives_refresh',root().querySelector('[aria-label="给这个项目的指令"]').value==='这句话还没有发送');
  check('narrow_sidebar_has_no_horizontal_overflow',root().scrollWidth<=root().clientWidth+1);
  return {at:new Date().toISOString(),vault:expected,checks,modelExecuted:false,jobSubmission:'intercepted failure; project and material used real Kernel HTTP',project:project.oc_id};
})()
