const test=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const source=fs.readFileSync(require('node:path').join(__dirname,'../plugin/main.js'),'utf8');
const sandbox={module:{exports:{}},require:name=>name==='obsidian'?{
  Plugin:class{},ItemView:class{},Modal:class{},PluginSettingTab:class{},Notice:class{}
}:require(name)};
vm.runInNewContext(source,sandbox);
const Plugin=sandbox.module.exports;
test('opening an existing note reuses its tab; a new note never splits the editor',async()=>{
  const p=new Plugin(),opened=[];
  const file={path:'note.md'};
  const existing={view:{file},parent:{},openFile:async f=>opened.push(f)};
  let revealed,requested;
  const fresh={parent:{},openFile:async f=>opened.push(f)};
  p.app={vault:{getAbstractFileByPath:()=>file},workspace:{getLeavesOfType:()=>[existing],revealLeaf:async leaf=>revealed=leaf,getLeaf:kind=>{requested=kind;return fresh;}}};
  await p.openNote('note.md');assert.equal(revealed,existing);assert.equal(requested,undefined);
  p.app.workspace.getLeavesOfType=()=>[];p.editorLeaf=null;
  await p.openNote('note.md');assert.equal(requested,'tab');assert.equal(revealed,fresh);
});
function setup(){
  const right={},main={};const leaves=[];const opened=[];
  function leaf(root){return {view:{selected:'project',artifact:'article',composers:{project:'unsent instruction'},render:async()=>{}},
    getRoot:()=>root,loadIfDeferred:async()=>{},setViewState:async()=>{},detach(){leaves.splice(leaves.indexOf(this),1);this.detached=true;}};}
  const workspace={rightSplit:right,getLeavesOfType:()=>leaves.filter(l=>l.plugin!==false),
    getLeaf:()=>assert.fail('must not open a main-window leaf'),
    getRightLeaf:()=>{const l=leaf(right);leaves.push(l);opened.push(l);return l;},revealLeaf:async l=>{workspace.revealed=l;}};
  const p=new Plugin();p.app={workspace};p.settings={};p.connection={};
  return {p,workspace,right,main,leaves,opened,leaf};
}
test('first open goes to right sidebar; concurrent opens reuse it',async()=>{
  const x=setup();await Promise.all([x.p.open(),x.p.open('conversation'),x.p.open('project')]);
  assert.equal(x.opened.length,1);assert.equal(x.workspace.revealed.getRoot(),x.right);
  assert.equal(x.workspace.revealed.view.tab,'project');
});
test('old main-window panel migrates without detaching user documents',async()=>{
  const x=setup(),old=x.leaf(x.main),document=x.leaf(x.main);document.plugin=false;x.leaves.push(old,document);
  await x.p.open('conversation');
  assert.equal(old.detached,true);assert.equal(document.detached,undefined);
  assert.equal(x.opened[0].view.composers.project,'unsent instruction');
});
test('deferred right panel is loaded and duplicates retired',async()=>{
  const x=setup(),right=x.leaf(x.right),old=x.leaf(x.main);x.leaves.push(old,right);
  right.loadIfDeferred=async()=>{right.loaded=true;};await x.p.open();
  assert.equal(right.loaded,true);assert.equal(x.opened.length,0);assert.equal(old.detached,true);
});
test('failed sidebar creation preserves old panel and never falls back to main',async()=>{
  const x=setup(),old=x.leaf(x.main);x.leaves.push(old);x.workspace.getRightLeaf=()=>null;
  await assert.rejects(x.p.open(),/右侧栏/);assert.equal(old.detached,undefined);
});
test('unloading prevents queued panel creation',async()=>{
  const x=setup();x.p.unloading=true;await x.p.open();assert.equal(x.opened.length,0);
});

test('missing checkout falls back to the kernel installed beside the plugin',()=>{
  const os=require('node:os'),path=require('node:path');const base=fs.mkdtempSync(path.join(os.tmpdir(),'oc-runtime-'));
  try{const bundled=path.join(base,'.obsidian/plugins/opencontent/kernel');fs.mkdirSync(path.join(bundled,'opencontent'),{recursive:true});fs.writeFileSync(path.join(bundled,'opencontent/__main__.py'),'');
    const p=new Plugin();p.settings={kernelPath:path.join(base,'removed-checkout')};p.app={vault:{adapter:{getBasePath:()=>base}}};
    assert.equal(p.runtimeDirectory(),bundled);
    fs.unlinkSync(path.join(bundled,'opencontent/__main__.py'));assert.throws(()=>p.runtimeDirectory(),/运行内核缺失/);
  }finally{fs.rmSync(base,{recursive:true,force:true});}
});


test('managed old runtime follows current plugin version while explicit checkout remains selected',()=>{
  const os=require('node:os'),path=require('node:path');const base=fs.mkdtempSync(path.join(os.tmpdir(),'oc-version-'));
  try{
    const pluginDir=path.join(base,'.obsidian/plugins/opencontent');const old=path.join(pluginDir,'kernel'),fresh=path.join(pluginDir,'kernel-0.8.0'),custom=path.join(base,'checkout');
    for(const folder of [old,fresh,custom]){fs.mkdirSync(path.join(folder,'opencontent'),{recursive:true});fs.writeFileSync(path.join(folder,'opencontent/__main__.py'),'');}
    const p=new Plugin();p.settings={kernelPath:old};p.manifest={version:'0.8.0'};p.app={vault:{adapter:{getBasePath:()=>base}}};
    assert.equal(p.runtimeDirectory(),fresh);p.settings.kernelPath=custom;assert.equal(p.runtimeDirectory(),custom);
  }finally{fs.rmSync(base,{recursive:true,force:true});}
});
