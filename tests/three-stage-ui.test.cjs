// These are UI-code -> authenticated HTTP -> actual kernel E2Es, not native
// Obsidian acceptance. The thin element/host double is explicitly a fixture.
const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const {spawn}=require('node:child_process');
class Element{
  constructor(tag='div'){this.tagName=tag;this.children=[];this.events={};this.attrs={};this.value='';}
  appendChild(c){this.children.push(c);return c;}setAttribute(k,v){this.attrs[k]=v;}removeAttribute(k){delete this.attrs[k];}
  addEventListener(k,f){this.events[k]=f;}async dispatch(k){return this.events[k]?.({});}
  async click(){if(!this.disabled)return this.dispatch('click');}replaceChildren(){this.children=[];}empty(){this.replaceChildren();}addClass(){}
}
const flatten=n=>[n,...n.children.flatMap(flatten)];
test('writing target, proposal/apply, Critic and social buttons reach real HTTP kernel',{timeout:45000},async()=>{
  const child=spawn(process.env.PYTHON||'python',[path.join(__dirname,'helpers/three_stage_http_bridge.py')],{cwd:path.join(__dirname,'..'),stdio:['pipe','pipe','pipe'],windowsHide:true});
  let errors='';child.stderr.on('data',d=>{errors+=d;});
  const config=await new Promise((resolve,reject)=>{
    let buffer='';const timer=setTimeout(()=>reject(Error('bridge startup timeout '+errors)),10000);
    child.stdout.on('data',d=>{buffer+=d;if(buffer.includes('\n')){clearTimeout(timer);resolve(JSON.parse(buffer.split('\n')[0]));}});
    child.once('exit',code=>{clearTimeout(timer);reject(Error('bridge exited '+code+' '+errors));});
  });
  const calls=[],notices=[];let modalRoot;
  async function api(route,body){
    calls.push({route,body});const response=await fetch(`http://127.0.0.1:${config.port}${route}`,{
      method:body===undefined?'GET':'POST',headers:{Authorization:'Bearer '+config.token,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)});
    const result=await response.json();if(!response.ok)throw Error(result.error);return result;
  }
  const sandbox={module:{exports:{}},Buffer,document:{createElement:t=>new Element(t)},require:n=>n==='obsidian'?{
    Plugin:class{},ItemView:class{},PluginSettingTab:class{},Notice:class{constructor(text){notices.push(text);}},
    Modal:class{constructor(){this.contentEl=new Element();modalRoot=this.contentEl;}open(){this.onOpen();}close(){this.onClose();}}
  }:require(n)};
  sandbox.window={setTimeout,clearTimeout,setInterval,clearInterval};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../plugin/main.js'),'utf8')+'\nmodule.exports.Cockpit=Cockpit;',sandbox);
  const plugin={app:{vault:{getAbstractFileByPath:()=>null}},settings:{},api,openNote:async()=>{}};
  const view=new sandbox.module.exports.Cockpit({},plugin);view.app=plugin.app;view.render=async()=>{};
  const waited=new Set();
  async function waitJob(){
    for(let i=0;i<150;i++){const rows=await api('/jobs');const job=rows.find(j=>!waited.has(j.id));if(job&&!['QUEUED','RUNNING'].includes(job.status)){assert.equal(job.status,'SUCCEEDED',JSON.stringify(job));waited.add(job.id);return job;}await new Promise(r=>setTimeout(r,20));}
    throw Error('job timeout '+JSON.stringify({jobs:await api('/jobs'),notices}));
  }
  try{
    let data=await api('/board'),p=data.projects[0];const root=new Element();view.artifact=config.second;view.chatMode='revise';
    await view.conversation(root,data,p);
    const nodes=flatten(root);nodes.find(n=>n.attrs['aria-label']==='想做什么').value='revise';
    nodes.find(n=>n.attrs['aria-label']==='给这个项目的指令').value='只修改选定第二稿';
    await nodes.find(n=>n.attrs['aria-label']==='给这个项目的指令').dispatch('input');
    await nodes.find(n=>n.textContent==='发送').click();await waitJob();
    const sent=calls.find(c=>c.route==='/conversation/send');assert.equal(sent.body.target_artifact_id,config.second);
    let history=await api('/conversation/history',{project:config.project});assert.equal(history.turns[0].revision.artifact,config.second);
    const originalFirst=(await api('/objects/'+config.first)).object.body;
    data=await api('/board');p=data.projects[0];const applyRoot=new Element();await view.conversation(applyRoot,data,p);
    await flatten(applyRoot).find(n=>n.textContent==='采用并检查').click();await waitJob();
    const reviewed=await api('/objects/'+config.second);assert.equal(reviewed.gate.review.artifact,config.second);assert.equal(reviewed.gate.approved,false);
    assert.equal((await api('/objects/'+config.first)).object.body,originalFirst);
    assert.equal(calls.find(c=>c.route==='/jobs'&&c.body).body.target_artifact_id,config.second);
    data=await api('/board');p=data.projects[0];view.chatMode='illustrate';view.composers[config.project]='生成两张合成图片';
    const imageRoot=new Element();await view.conversation(imageRoot,data,p);
    const imageMode=flatten(imageRoot).find(n=>n.attrs['aria-label']==='想做什么');imageMode.value='illustrate';
    await flatten(imageRoot).find(n=>n.textContent==='发送').click();await waitJob();
    for(let index=0;index<2;index++){
      data=await api('/board');p=data.projects[0];const candidates=new Element();await view.conversation(candidates,data,p);
      await flatten(candidates).filter(n=>n.textContent==='检查并插入到目标稿件')[index].click();
      const turns=(await api('/conversation/history',{project:config.project})).turns;
      assert.equal(turns.find(t=>t.images?.length===2).applied_images.length,index+1);
    }
    assert.equal((await api('/objects/'+config.second)).gate.approved,false);
    const socialRoot=new Element();data=await api('/board');p=data.projects[0];const detail=await api('/objects/'+p.oc_id);
    await view.socialPanel(socialRoot,data,p,detail);
    flatten(socialRoot).find(n=>n.attrs['aria-label']==='小红书母稿').value=config.first;
    flatten(socialRoot).find(n=>n.attrs['aria-label']==='图文读者与表达意图').value='合成验收：向初学者解释来源边界';
    await flatten(socialRoot).find(n=>n.textContent==='生成小红书独立候选').click();const socialJob=await waitJob();
    const variant=await api('/objects/'+socialJob.detail.candidate);assert.equal(variant.object.channel,'xiaohongshu');assert.equal(variant.gate.approved,false);
    await view.socialPreview(variant.object,variant,false);assert.ok(flatten(modalRoot).some(n=>String(n.textContent).includes('UNAPPROVED_PREVIEW')));
    assert.ok(flatten(modalRoot).find(n=>n.tagName==='iframe').srcdoc.includes('data:image/png;base64,'));
    await assert.rejects(()=>view.socialPreview(variant.object,variant,true),/独立渠道稿/);
    const build=await api('/build',{artifact:config.first,token:(await api('/board')).token});assert.equal(build.status,'APPROVED_BUILD');
    assert.ok(build.html.includes('<section'));assert.ok(!build.html.includes('[['));
    assert.ok(!notices.some(n=>/已发表/.test(n)));
    fs.mkdirSync(path.join(__dirname,'../.execution'),{recursive:true});
    fs.writeFileSync(path.join(__dirname,'../.execution/normal-ui-regressions.json'),JSON.stringify({fixture:true,native:false,passed:true,routes:calls.map(c=>c.route),jobs:[...waited],checks:['target','revision','critic','continuous_images','social_preview','unapproved_export_rejected','build']},null,2));
  }finally{
    child.stdin.end('\n');await new Promise(resolve=>{if(child.exitCode!==null)return resolve();child.once('exit',resolve);setTimeout(()=>{child.kill();resolve();},5000).unref();});
  }
});

test('native selection excludes frontmatter duplicates and maps CRLF/emoji to codepoints',async()=>{
  const sandbox={module:{exports:{}},Buffer,require:n=>n==='obsidian'?{Plugin:class{},ItemView:class{},Modal:class{},PluginSettingTab:class{},Notice:class{}}:require(n),window:{setTimeout,clearTimeout,setInterval,clearInterval}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../plugin/main.js'),'utf8')+'\nmodule.exports.Cockpit=Cockpit;',sandbox);
  const body='中文😀开头\n第二段🚀选区。';
  for(const ending of ['\n','\r\n']){
    const raw=('---\ntitle: '+body.split('\n')[0]+'\nsummary: |\n  '+body.replace(/\n/g,'\n  ')+'\n---\n\n'+body+'\n').replace(/\n/g,ending);
    const selected='🚀选区',from=raw.lastIndexOf(selected),to=from+selected.length;
    const view=Object.create(sandbox.module.exports.Cockpit.prototype);
    view.plugin={api:async()=>({object:{oc_id:'a',path:'a.md',body},input_snapshot:{base_hash:'base'}})};
    view.app={workspace:{activeEditor:{file:{path:'a.md'},editor:{getValue:()=>raw,getSelection:()=>selected,posToOffset:x=>x,getCursor:x=>x==='from'?from:to}}},vault:{adapter:{read:async()=>raw}}};
    const result=await view.captureArtifactSelection('a');
    assert.equal(result.selection.start,Array.from(body.slice(0,body.indexOf(selected))).length);
    assert.equal(result.selection.end-result.selection.start,Array.from(selected).length);
  }
});
