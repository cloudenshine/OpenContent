const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
class Element {
  constructor(tag='div'){this.tagName=tag;this.children=[];this.events={};this.attrs={};this.value='';}
  appendChild(c){this.children.push(c);return c;} setAttribute(k,v){this.attrs[k]=v;} removeAttribute(k){delete this.attrs[k];}
  addEventListener(k,f){this.events[k]=f;} async dispatch(k){return this.events[k]?.({});}
  async click(){if(!this.disabled)return this.dispatch('click');} replaceChildren(){this.children=[];} empty(){this.replaceChildren();} addClass(){}
}
const flatten=n=>[n,...n.children.flatMap(flatten)];
function setup(task,{response={receipt:{status:'SUCCEEDED'}},fail=false,api}={}){
  let root;const calls=[],notices=[];
  const sandbox={module:{exports:{}},Buffer,document:{createElement:t=>new Element(t)},require:n=>n==='obsidian'?{
    Plugin:class{},ItemView:class{},PluginSettingTab:class{},Notice:class{constructor(t){notices.push(t);}},
    Modal:class{constructor(){this.contentEl=new Element();root=this.contentEl;}open(){this.onOpen();}close(){this.onClose();}}
  }:require(n)};
  sandbox.window={setTimeout:sandbox.setTimeout||setTimeout,clearTimeout:sandbox.clearTimeout||clearTimeout,setInterval:sandbox.setInterval||setInterval,clearInterval:sandbox.clearInterval||clearInterval};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../plugin/main.js'),'utf8')+'\nmodule.exports.Cockpit=Cockpit;',sandbox);
  const plugin={app:{},settings:{},api:async(route,body)=>{calls.push({route,body});if(api)return api(route,body);if(fail)throw Error('上游阻断');return response;}};
  const view=new sandbox.module.exports.Cockpit({},plugin);
  view.capabilityTaskModal({oc_id:'p',artifacts:[],goal:'目标'},{objects:[]},{id:task,label:task,desc:'任务'});
  return {calls,notices,nodes:()=>flatten(root),start:()=>flatten(root).find(n=>n.textContent===`启动 ${task}`),field:l=>flatten(root).find(n=>n.attrs['aria-label']===l)};
}
test('long scan submits an explicit supported source, never empty automatic all-web scan',async()=>{
  const x=setup('long-scan');await x.start().click();assert.deepEqual(Array.from(x.calls[0].body.source_ids),['qimao-boy-hot-daily']);assert.equal(x.calls[0].body.raw_data,undefined);
});
test('import mode validates JSON and passes the exact provenance-bearing data',async()=>{
  const x=setup('short-scan');await x.start().click();assert.equal(x.calls.length,0);
  x.field('采集快照 JSON').value='not json';await x.start().click();assert.equal(x.calls.length,0);
  const raw={zhihu:[{title:'真实采集条目',url:'https://www.zhihu.com/question/123',observed_at:'2026-09-30T10:00:00Z'}]};
  x.field('采集快照 JSON').value=JSON.stringify(raw);await x.start().click();assert.equal(JSON.stringify(x.calls[0].body.raw_data),JSON.stringify(raw));
});
test('upstream failure and failed receipt never render success; retry preserves import',async()=>{
  for(const options of [{fail:true},{response:{receipt:{status:'FAILED',error:'数据不足'}}}]){
    const x=setup('short-scan',options);x.field('采集快照 JSON').value='{"zhihu":[]}';await x.start().click();
    assert.ok(!x.nodes().some(n=>n.textContent==='✅ 任务执行完成'));assert.equal(x.start().disabled,false);assert.equal(x.field('采集快照 JSON').value,'{"zhihu":[]}');
  }
});
test('cover passes genre/instruction and has no fake formal-cover selection',async()=>{
  const x=setup('cover',{response:{receipt:{status:'SUCCEEDED'},candidates:[{candidate_id:'v1',path:'Attachments/cover.png',spec:{}}]}});
  x.field('封面题材').value='科幻';x.field('给本次任务的具体指令 / 提示').value='蓝色飞船';await x.start().click();
  assert.equal(x.calls[0].body.genre,'科幻');assert.equal(x.calls[0].body.instruction,'蓝色飞船');assert.ok(!x.nodes().some(n=>n.textContent==='设为项目封面'));
});
test('real UI request reaches authenticated HTTP runtime and persists imported provenance',async()=>{
  const {spawnSync}=require('node:child_process');
  const x=setup('long-scan',{api:async(route,body)=>{
    const r=spawnSync(process.env.PYTHON||'python',[path.join(__dirname,'helpers/capability_http_bridge.py')],{input:JSON.stringify(body),encoding:'utf8',cwd:path.join(__dirname,'..')});
    assert.equal(r.status,0,r.stderr);const result=JSON.parse(r.stdout);if(result.status!==200)throw Error(JSON.stringify(result));return result.data;
  }});
  x.field('市场数据来源').value='import';await x.field('市场数据来源').dispatch('change');
  x.field('采集快照 JSON').value=JSON.stringify({qimao:[1,2,3].map(i=>({title:`输入作品${i}`,author:'测试来源',url:`https://www.qimao.com/shuku/${i}/`,observed_at:'2026-09-30T10:00:00Z',rank:i,genre:'科幻'}))});
  await x.start().click();assert.ok(x.nodes().some(n=>n.textContent==='✅ 任务执行完成'),x.nodes().map(n=>n.textContent).join('\n'));
  assert.ok(x.nodes().some(n=>String(n.textContent).includes('import')));
});
test('test-only cover artifacts are visibly distinguished from production results',async()=>{
  const x=setup('cover',{response:{mode:'fixture',receipt:{status:'SUCCEEDED',execution_mode:'fixture'},candidates:[{candidate_id:'v1',path:'test.png',spec:{},provenance:{test_only:true}}]}});
  await x.start().click();assert.ok(x.nodes().some(n=>n.textContent==='🧪 测试夹具执行完成（非真实生图）'));assert.ok(!x.nodes().some(n=>n.textContent==='✅ 任务执行完成'));
});
test('cover UI reaches HTTP runtime and a labelled fixture provider with verified image files',async()=>{
  const {spawnSync}=require('node:child_process');
  const x=setup('cover',{api:async(route,body)=>{
    const r=spawnSync(process.env.PYTHON||'python',[path.join(__dirname,'helpers/capability_http_bridge.py')],{input:JSON.stringify(body),encoding:'utf8',cwd:path.join(__dirname,'..')});
    assert.equal(r.status,0,r.stderr);const result=JSON.parse(r.stdout);if(result.status!==200)throw Error(JSON.stringify(result));return result.data;
  }});
  x.nodes().find(n=>n.tagName==='select').value='fanqie';
  await x.start().click();assert.ok(x.nodes().some(n=>n.textContent==='🧪 测试夹具执行完成（非真实生图）'),x.nodes().map(n=>n.textContent).join('\n'));
  assert.ok(x.nodes().some(n=>String(n.textContent).includes('600×800')));
});
