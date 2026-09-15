const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path'),os=require('node:os');
const {EventEmitter}=require('node:events');
const source=fs.readFileSync(path.join(__dirname,'../plugin/main.js'),'utf8');
function setup(behavior){
  const base=fs.mkdtempSync(path.join(os.tmpdir(),'oc-doctor-ui-'));
  fs.mkdirSync(path.join(base,'opencontent'));fs.writeFileSync(path.join(base,'opencontent/__main__.py'),'');fs.writeFileSync(path.join(base,'doctor.py'),'');
  let call,child;
  const sandbox={module:{exports:{}},setTimeout,clearTimeout,require:name=>name==='obsidian'?{Plugin:class{},ItemView:class{},Modal:class{},PluginSettingTab:class{},Notice:class{}}:name==='child_process'?{spawn:(exe,args,options)=>{
    call={exe,args,options};child=new EventEmitter();child.stdout=new EventEmitter();child.stderr=new EventEmitter();child.kill=()=>{child.killed=true;child.emit('close',null);};queueMicrotask(()=>behavior(child));return child;
  }}:require(name)};
  vm.runInNewContext(source,sandbox);const p=new sandbox.module.exports();p.settings={kernelPath:base,python:'C:/Python312/python.exe',codex:'C:/AI CLI/codex.exe'};p.app={vault:{adapter:{getBasePath:()=>base}}};
  return {p,base,call:()=>call,child:()=>child,close:()=>fs.rmSync(base,{recursive:true,force:true})};
}
const report=passed=>({schema:1,passed,checks:[{status:passed?'PASS':'FAIL',message:passed?'环境正常':'缺少依赖',action:passed?'':'安装 requirements.txt'}]});
test('doctor uses argv, hidden window, no shell and preserves failure report',async()=>{
  const x=setup(c=>{c.stdout.emit('data',JSON.stringify(report(false)));c.emit('close',1);});
  try{const r=await x.p.runDoctor();assert.equal(r.passed,false);assert.equal(r.checks[0].action,'安装 requirements.txt');
    assert.equal(x.call().options.shell,false);assert.equal(x.call().options.windowsHide,true);assert.ok(x.call().args.includes('C:/AI CLI/codex.exe'));assert.equal(x.p.doctors.size,0);
  }finally{x.close();}
});
test('missing Python has actionable message with no raw subprocess details',async()=>{
  const x=setup(c=>c.emit('error',new Error('raw private process details')));
  try{await assert.rejects(x.p.runDoctor(),e=>/无法启动所选 Python/.test(e.message)&&!e.message.includes('raw private'));assert.equal(x.p.doctors.size,0);}finally{x.close();}
});
test('malformed report and mismatched exit code cannot appear successful',async()=>{
  for(const [output,code] of [['bad json',0],[JSON.stringify(report(true)),1],[JSON.stringify({schema:1,passed:true,checks:[]}),0]]){
    const x=setup(c=>{c.stdout.emit('data',output);c.emit('close',code);});
    try{await assert.rejects(x.p.runDoctor(),/有效结果/);}finally{x.close();}
  }
});
test('oversized output terminates only the owned diagnostic process',async()=>{
  const x=setup(c=>c.stdout.emit('data','x'.repeat(70000)));
  try{await assert.rejects(x.p.runDoctor(),/输出异常/);assert.equal(x.child().killed,true);}finally{x.close();}
});
test('unloaded plugin refuses a new diagnostic process',async()=>{
  const x=setup(()=>assert.fail('must not spawn'));x.p.unloading=true;
  try{await assert.rejects(x.p.runDoctor(),/正在关闭/);assert.equal(x.call(),undefined);}finally{x.close();}
});
