async (page) => {
  const checks=[];
  const check=(name,pass,detail)=>{checks.push({name,pass,detail});if(!pass)throw Error(name+': '+detail)};
  try{
    await page.request.post((await page.evaluate(()=>location.origin))+'/reset');
    await page.reload();
    await page.waitForFunction(()=>window.previewReady||window.previewError);
    check('preview_loaded',await page.evaluate(()=>!!window.previewReady),await page.locator('#cockpit').innerText());
    const out = await page.evaluate(()=>fixture.artifact_output);
    const before=await page.evaluate(()=>uiCalls.filter(c=>c.body));
    await page.getByRole('button',{name:/1.*准备/}).click();
    await page.getByLabel('告诉我你的想法').fill('把读书笔记写成一篇清楚的文章');
    check('prepare_first_input',await page.locator('.oc-content > :first-child').evaluate(el=>el.classList.contains('oc-start')),'start precedes optional discovery');
    check('stage_contract_visible',await page.locator('.oc-step-guide').count()===1,'one input / adjustment / output guide');
    check('navigation_does_not_mutate',await page.evaluate(n=>uiCalls.filter(c=>c.body).length===n,before.length),'navigation must not start jobs or create projects');
    await page.evaluate(()=>go('project'));
    check('editor_then_output',await page.locator('.oc-editor-pane').count()===1&&await page.locator('.oc-output-pane').count()===1,'separate input and current draft output');
    await page.getByRole('button',{name:'讲得更清楚',exact:true}).click();
    check('preset_fills_input',await page.getByLabel('给这个项目的指令').inputValue().then(s=>s.includes('保留原有事实')),'existing preset still usable');
    await page.getByRole('button',{name:'生成改稿提案',exact:true}).click();
    await page.waitForFunction(async()=>{const j=await plugin.api('/jobs');return j.some(x=>x.status==='SUCCEEDED')});
    await page.evaluate(()=>view.render());
    check('proposal_keeps_draft_unapproved',await page.evaluate(async()=>!(await plugin.api('/objects/'+fixture.second)).gate.approved),'model output does not approve');
    await page.getByRole('button',{name:'采用并检查',exact:true}).click();
    await page.waitForFunction(async()=>{const h=await plugin.api('/conversation/history',{project:fixture.project});return h.turns.some(t=>t.applied)});
    await page.waitForFunction(async()=>!(await plugin.api('/jobs')).some(x=>['RUNNING','QUEUED'].includes(x.status)));
    await page.evaluate(()=>view.render());
    check('output_updates_after_apply',await page.locator('.oc-output-pane').innerText().then(s=>s.includes('合成 UI 改稿候选')),'accepted revision appears in output');
    await page.getByRole('button',{name:'下一步：检查当前稿件',exact:true}).click();
    await page.locator('.oc-check-next').waitFor();
    check('reaches_check',await page.locator('.oc-check-next').count()===1,'footer goes to current artifact check');
    check('approval_is_explicit',await page.getByRole('button',{name:'批准当前版本',exact:true}).count()===1,'separate human action');
    const second=await page.evaluate(()=>fixture.second);
    await page.evaluate(async()=>{const original=plugin.api;plugin.api=async(route,body)=>{const r=await original(route,body);if(route==='/objects/'+fixture.second){r.gate.status='FAIL';r.gate.approved=false;r.gate.issues=['已审阅来源发生变化'];for(const v of Object.values(r.gate.axes||{}))v.status='PASS'}return r};await go('inspector');plugin.api=original});
    check('stale_gate_never_says_all_passed',!(await page.locator('.oc-check-summary').innerText()).includes('全部检查已通过'),'axis PASS does not override authoritative FAIL');
    await page.evaluate(()=>go('publishing',fixture.first));
    await page.getByRole('button',{name:'Markdown',exact:true}).click();
    await page.getByRole('button',{name:'生成本地交付包',exact:true}).click();
    await page.locator('.oc-delivery-result').waitFor();
    check('delivery_output_persists',await page.locator('.oc-delivery-result').innerText().then(s=>s.includes('交付文件已生成')),'visible result and path after export');
    check('no_account_writes',await page.evaluate(()=>!uiCalls.some(c=>['/publications/confirm','/channels/cover'].includes(c.route))),'local export never publishes');
    await page.evaluate(()=>document.querySelectorAll('.preview-notice').forEach(el=>el.remove()));
    await page.evaluate(()=>go('project',fixture.first));
    for(const width of [320,440,1000]){
      await page.setViewportSize({width,height:950});
      check('no_horizontal_overflow_'+width,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'controls fit');
      await page.screenshot({path:out+'/create-light-'+width+'.png',fullPage:true});
    }
    await page.evaluate(()=>document.body.classList.add('dark'));
    await page.setViewportSize({width:1000,height:950});
    await page.screenshot({path:out+'/create-dark-1000.png',fullPage:true});
    await page.evaluate(receipt=>fetch('/receipt',{method:'POST',body:JSON.stringify(receipt)}),{passed:true,native_obsidian:false,real_kernel:true,model:'synthetic',checks,artifact:second,runtime:await page.evaluate(()=>fixture.runtime),plugin_dir:await page.evaluate(()=>fixture.plugin_dir)});
    return {passed:true,checks};
  }catch(error){await page.evaluate(receipt=>fetch('/receipt',{method:'POST',body:JSON.stringify(receipt)}),{passed:false,error:error.message,checks});return {passed:false,error:error.message,checks}}
}
