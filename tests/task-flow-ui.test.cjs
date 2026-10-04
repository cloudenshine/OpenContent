const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');

const source=fs.readFileSync(path.join(__dirname,'../plugin/main.js'),'utf8');
const sandbox={module:{exports:{}},Buffer,require:name=>name==='obsidian'?{
  Plugin:class{},ItemView:class{},Modal:class{},PluginSettingTab:class{},Notice:class{}
}:require(name),window:{setTimeout,clearTimeout,setInterval,clearInterval}};
vm.runInNewContext(source+'\nmodule.exports.Cockpit=Cockpit;',sandbox);
const Cockpit=sandbox.module.exports.Cockpit;

test('primary navigation is the four-step author journey',()=>{
  const view=Object.create(Cockpit.prototype);
  assert.equal(view.stepForTab('board'),'prepare');
  assert.equal(view.stepForTab('project'),'create');
  assert.equal(view.stepForTab('conversation'),'create');
  assert.equal(view.stepForTab('inspector'),'check');
  assert.equal(view.stepForTab('inbox'),'check');
  assert.equal(view.stepForTab('publishing'),'deliver');
  assert.deepEqual(Array.from(view.flowSteps(),x=>[x.id,x.title]),[
    ['prepare','准备'],['create','创作'],['check','检查'],['deliver','交付']
  ]);
});

test('journey status tells a new author where to start and what completion means',()=>{
  const view=Object.create(Cockpit.prototype);
  view.selected=null;view.artifact=null;
  assert.match(view.journeyState({projects:[]}).message,/从这里开始/);

  const draft={oc_id:'a',title:'样稿',gate:{status:'PASS',approved:false}};
  view.selected='p';view.artifact='a';
  let state=view.journeyState({projects:[{oc_id:'p',title:'作品甲',effective_state:'REVIEWING',artifacts:[draft]}]});
  assert.match(state.message,/检查已通过/);
  assert.match(state.next,/批准当前版本/);

  draft.gate.approved=true;
  state=view.journeyState({projects:[{oc_id:'p',title:'作品甲',effective_state:'APPROVED',artifacts:[draft]}]});
  assert.match(state.message,/已批准/);
  assert.match(state.next,/交付/);
});

test('quality axes are presented in reader language instead of internal jargon',()=>{
  const view=Object.create(Cockpit.prototype);
  assert.deepEqual(
    ['EVIDENCE','LOGIC','ORIGINALITY','VOICE','UTILITY'].map(x=>view.axisLabel(x)),
    ['事实依据','逻辑完整','独立表达','表达自然','读者价值']
  );
});

test('main source exposes human workflow labels and hides old feature navigation',()=>{
  for(const phrase of ['当前作品','准备','创作','检查','交付','批准当前版本','更多创作能力','公众号','小红书','Markdown','富文本']){
    assert.ok(source.includes(phrase),phrase);
  }
  assert.ok(!source.includes("[['board','首页'],['project','写作'],['publishing','发布']]"),'old feature navigation should be removed');
});
