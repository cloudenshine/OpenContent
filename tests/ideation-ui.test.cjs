const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');

// Contract-level DOM harness. It does not stand in for native Obsidian acceptance.
class Element{
  constructor(tag='div'){this.tagName=tag;this.children=[];this.events={};this.attrs={};this.isConnected=true;this.value='';}
  appendChild(child){this.children.push(child);child.parent=this;return child;}
  setAttribute(k,v){this.attrs[k]=v;}
  getAttribute(k){return this.attrs[k];}
  removeAttribute(k){delete this.attrs[k];}
  addEventListener(k,fn){this.events[k]=fn;}
  async dispatch(k){return this.events[k]?.();}
  replaceChildren(){this.children=[];}
  empty(){this.replaceChildren();}
  addClass(){}
  remove(){if(this.parent)this.parent.children=this.parent.children.filter(c=>c!==this);}
}
function flatten(n){return [n,...n.children.flatMap(flatten)];}
const settle=async()=>{for(let i=0;i<6;i++)await new Promise(setImmediate);};
function setup({failed=false,running=false,noProvider=false,history=false}={}){
  const calls=[],timers=[];let modal,saved;
  class Modal{constructor(){this.contentEl=new Element();modal=this;}open(){this.onOpen();}close(){this.onClose();this.contentEl.isConnected=false;}}
  const sandbox={module:{exports:{}},document:{createElement:tag=>new Element(tag)},setTimeout:fn=>timers.push(fn),clearTimeout(){},require:name=>name==='obsidian'?{Plugin:class{},ItemView:class{},PluginSettingTab:class{},Modal,Notice:class{}}:require(name)};
  const source=fs.readFileSync(path.join(__dirname,'../plugin/main.js'),'utf8');
  vm.runInNewContext(source+'\nmodule.exports.Cockpit=Cockpit;',sandbox);
  const plugin={settings:{ideationFolders:[],ideationLimit:24},saveData:async data=>{saved=data;},api:async(route,body)=>{
    calls.push({route,body});
    if(route==='/ideation/scope')return {folders:[{path:'Research',notes:2},{path:'Private',notes:5}]};
    if(route==='/ideation/preview')return {id:'preview',stats:{in_scope:2,selected:2,sampled:false},folders:['Research']};
    if(route==='/providers')return {active:noProvider?{}:{codex:{}},available:[]};
    if(route==='/ideation/start')return {id:'fresh'};
    if(route==='/ideation/retry')return {id:'retried'};
    if(route==='/ideation/status')return {id:body.id,created:new Date().toISOString(),direction:'selected direction',stage:'synthesize',status:running?'RUNNING':failed&&body.id==='original'?'FAILED':'SUCCEEDED',error:'temporary model error',result:{themes:[],cards:[],ideas:[],excluded:[],insufficient:'No viable combination'}};
    throw Error('Unexpected API '+route);
  }};
  const view=new sandbox.module.exports.Cockpit({},plugin);view.data={jobs:history?[{id:'old',detail:{kind:'ideation'}}]:[]};
  view.discoverIdeas(failed?'original':running?'running':null);
  return {calls,timers,plugin,get modal(){return modal;},get saved(){return saved;},nodes:()=>flatten(modal.contentEl)};
}
test('scope selection and count reach preview before any model start',async()=>{
  const x=setup();await settle();
  const label=x.nodes().find(n=>n.tagName==='label'&&n.children.some(c=>String(c.textContent).startsWith('Research')));
  const checkbox=label.children.find(n=>n.tagName==='input');checkbox.checked=true;await checkbox.dispatch('change');
  const count=x.nodes().find(n=>n.attrs['aria-label']==='最多参与综合的资料数（2–60）');count.value='2';await count.dispatch('input');
  const provider=x.nodes().find(n=>n.attrs['aria-label']==='选题综合 CLI');provider.value='codex';
  await x.nodes().find(n=>n.textContent==='按此范围生成选题').dispatch('click');
  const previews=x.calls.filter(c=>c.route==='/ideation/preview');
  assert.deepEqual(Array.from(previews.at(-1).body.folders),['Research']);assert.equal(previews.at(-1).body.limit,2);
  assert.equal(x.calls.filter(c=>c.route==='/ideation/start').length,1);assert.equal(x.saved.ideationLimit,2);
});
test('failed task retry uses recovery endpoint and shows the new receipt',async()=>{
  const x=setup({failed:true});await settle();
  await x.nodes().find(n=>n.textContent==='重试这次任务').dispatch('click');
  assert.equal(x.calls.find(c=>c.route==='/ideation/retry').body.id,'original');
  assert.equal(x.calls.filter(c=>c.route==='/ideation/start').length,0);
  assert.equal(x.calls.filter(c=>c.route==='/ideation/status').at(-1).body.id,'retried');
});
test('configuration error stays in the modal and re-enables the action',async()=>{
  const x=setup({noProvider:true});await settle();
  const start=x.nodes().find(n=>n.textContent==='按此范围生成选题');await start.dispatch('click');
  assert.equal(start.disabled,false);assert.equal(start.attrs['aria-busy'],undefined);
  assert.ok(x.nodes().some(n=>n.attrs.role==='alert'&&n.textContent.includes('启用一个本地 CLI')));
  assert.equal(x.calls.filter(c=>c.route==='/ideation/start').length,0);
});
test('closing the modal stops further polling but does not cancel a background job',async()=>{
  const x=setup({running:true});await settle();const before=x.calls.length;
  x.modal.close();await x.timers[0]();await settle();assert.equal(x.calls.length,before);
});

test('new discovery does not present a historical result as the selected scope',async()=>{
  const x=setup({history:true});await settle();
  assert.equal(x.calls.filter(c=>c.route==='/ideation/status').length,0);
});

test('changing direction removes prior results and prevents old polling from restoring them',async()=>{
  const x=setup({running:true});await settle();
  const query=x.nodes().find(n=>n.attrs['aria-label']==='希望探索的方向');
  query.value='新的问题';await query.dispatch('input');
  const before=x.calls.length;await x.timers[0]();await settle();
  assert.equal(x.calls.length,before);
  assert.ok(!x.nodes().some(n=>n.textContent==='正在处理'));
});
