const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
class Element{
  constructor(tag='div'){this.tagName=tag;this.children=[];this.events={};this.attrs={};this.value='';this.isConnected=true;}
  appendChild(child){this.children.push(child);child.parent=this;return child;}
  setAttribute(k,v){this.attrs[k]=v;}getAttribute(k){return this.attrs[k];}removeAttribute(k){delete this.attrs[k];}
  addEventListener(k,fn){this.events[k]=fn;}async dispatch(k,event={}){return this.events[k]?.(event);}
  async click(){if(!this.disabled)return this.dispatch('click');}replaceChildren(){this.children=[];}empty(){this.replaceChildren();}addClass(){}
  remove(){if(this.parent)this.parent.children=this.parent.children.filter(c=>c!==this);}
}
const flatten=n=>[n,...n.children.flatMap(flatten)];
function setup({note=false,failStart=false,noProvider=false,running=false,createError=false}={}){
  const calls=[];const project={oc_id:'p',title:'文章',goal:'目标',audience:'读者',effective_state:'CAPTURED',artifacts:[],counts:{Material:0}};
  const data={projects:[],inbox:[],jobs:running?[{id:'job',project:'p',status:'RUNNING'}]:[],token:'original',diagnostics:[]};
  const app={workspace:{getActiveFile:()=>note?{extension:'md',path:'读书.md',name:'读书.md',basename:'读书'}:null},vault:{adapter:{readBinary:async()=>Buffer.from('selected bytes')}}};
  const sandbox={module:{exports:{}},Buffer,document:{createElement:t=>new Element(t)},require:n=>n==='obsidian'?{Plugin:class{},ItemView:class{constructor(){this.app=app;}},Modal:class{},PluginSettingTab:class{},Notice:class{}}:require(n)};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../plugin/main.js'),'utf8')+'\nmodule.exports.Cockpit=Cockpit;',sandbox);
  const plugin={app,settings:{},remember:async()=>{},api:async(route,body)=>{
    calls.push({route,body});
    if(route==='/providers')return {available:[],active:noProvider?{}:{codex:{}}};
    if(route==='/projects/selected'){if(createError)throw Error('材料已变化');return project;}
    if(route==='/objects/p')return {object:project,objects:[],token:'fresh'};
    if(route==='/conversation/history')return {turns:[],token:'fresh'};
    if(['/jobs','/conversation/send'].includes(route)){if(failStart)throw Error('暂不可用');return {id:'job'};}
    if(route==='/cancel')return {};
    throw Error('Unexpected '+route);
  }};
  const view=new sandbox.module.exports.Cockpit({},plugin);view.render=async()=>{};
  const root=new Element();return {root,view,plugin,data,calls,project,nodes:()=>flatten(root)};
}
test('one idea starts discussion; empty input never creates an article',async()=>{
  const x=setup();await x.view.board(x.root,x.data);
  const start=x.nodes().find(n=>n.textContent==='一起构思');assert.equal(start.disabled,true);
  await start.click();assert.equal(x.calls.length,0);
  const input=x.nodes().find(n=>n.attrs['aria-label']==='告诉我你的想法');input.value='教新手做读书笔记';await input.dispatch('input');await start.click();
  assert.equal(x.calls.filter(c=>c.route==='/projects/selected').length,1);
  const send=x.calls.find(c=>c.route==='/conversation/send');assert.equal(send.body.instruction,input.value);assert.equal(send.body.token,'fresh');
  assert.equal(x.view.tab,'project');
});
test('current note is visible, hash bound, and submitted without an extra modal',async()=>{
  const x=setup({note:true});x.view.homeGoal='写一篇读书指南';await x.view.board(x.root,x.data);
  assert.ok(x.nodes().some(n=>n.textContent==='使用当前笔记：读书'));
  await x.nodes().find(n=>n.textContent==='开始写作').click();
  const creation=x.calls.find(c=>c.route==='/projects/selected');assert.equal(creation.body.selected[0].path,'读书.md');
  assert.equal(creation.body.selected[0].hash,require('crypto').createHash('sha256').update('selected bytes').digest('hex'));
  assert.equal(x.calls.filter(c=>c.route==='/jobs').length,1);assert.ok(!x.calls.some(c=>c.route==='/conversation/send'));
});
test('removing the current note keeps it out of the request',async()=>{
  const x=setup({note:true});x.view.homeGoal='聊想法';await x.view.board(x.root,x.data);
  const checkbox=x.nodes().find(n=>n.type==='checkbox');checkbox.checked=false;await checkbox.dispatch('change');
  await x.nodes().find(n=>n.textContent==='一起构思').click();
  assert.equal(x.calls.find(c=>c.route==='/projects/selected').body.selected.length,0);
  assert.ok(!x.calls.some(c=>c.route==='/jobs'));
});
test('creation failure preserves input; start failure returns to the saved article',async()=>{
  for(const createError of [true,false]){
    const x=setup({failStart:true,createError});x.view.homeGoal='保留这句话';await x.view.board(x.root,x.data);
    await x.nodes().find(n=>n.textContent==='一起构思').click();
    if(createError){assert.equal(x.view.homeGoal,'保留这句话');assert.ok(!x.calls.some(c=>c.route==='/conversation/send'));}
    else {assert.equal(x.view.startError.project,'p');assert.equal(x.view.tab,'project');assert.equal(x.view.selected,'p');}
  }
});
test('missing assistant does not create an empty project',async()=>{
  const x=setup({noProvider:true});x.view.homeGoal='写文章';await x.view.board(x.root,x.data);
  await x.nodes().find(n=>n.textContent==='一起构思').click();assert.ok(!x.calls.some(c=>c.route==='/projects/selected'));
});
test('running task uses the same action to stop, without submitting a second request',async()=>{
  const x=setup({running:true});await x.view.conversation(x.root,x.data,x.project);
  await x.nodes().find(n=>n.textContent==='停止生成').click();
  assert.equal(x.calls.find(c=>c.route==='/cancel').body.id,'job');assert.ok(!x.calls.some(c=>c.route==='/conversation/send'));
});
test('unsent text survives rerender and failed sends, keyboard obeys button guard',async()=>{
  const x=setup({failStart:true});await x.view.conversation(x.root,x.data,x.project);
  const input=x.nodes().find(n=>n.attrs['aria-label']==='给这个项目的指令');const send=x.nodes().find(n=>n.textContent==='发送');
  await input.dispatch('keydown',{key:'Enter',ctrlKey:true,preventDefault(){}});assert.ok(!x.calls.some(c=>c.route==='/conversation/send'));
  input.value='换一个开头';await input.dispatch('input');await send.click();assert.equal(x.view.composers.p,'换一个开头');
  x.root.empty();await x.view.conversation(x.root,x.data,x.project);
  assert.equal(x.nodes().find(n=>n.attrs['aria-label']==='给这个项目的指令').value,'换一个开头');
});
test('continuing production uses the displayed version without a second confirmation',async()=>{
  const x=setup();await x.view.startProduction(x.project,{token:'displayed-token'});
  assert.equal(x.calls.length,1);assert.equal(x.calls[0].route,'/jobs');assert.equal(x.calls[0].body.token,'displayed-token');
  assert.equal(x.plugin.jobsActive,true);
});
