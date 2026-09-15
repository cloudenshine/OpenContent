// Debug only the explicitly launched isolated Obsidian instance on loopback 9337.
import fs from 'node:fs';
const targets=await (await fetch('http://127.0.0.1:9337/json/list')).json();
const target=targets.find(t=>t.type==='page' && t.url.startsWith('app://obsidian.md'));
if(!target)throw new Error('Isolated Obsidian page not found');
const socket=new WebSocket(target.webSocketDebuggerUrl);let seq=0;const pending=new Map();
await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
socket.onmessage=event=>{const msg=JSON.parse(event.data);if(pending.has(msg.id)){const {resolve,reject}=pending.get(msg.id);pending.delete(msg.id);msg.error?reject(new Error(JSON.stringify(msg.error))):resolve(msg.result);}};
async function send(method,params={}){return await new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));});}
try{
  if(process.argv[2]==='front'){
    await send('Page.bringToFront');console.log('Requested renderer activation; native hidden windows may remain hidden');
  }else if(process.argv[2]==='screenshot'){
    const result=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});fs.writeFileSync(process.argv[3],Buffer.from(result.data,'base64'));console.log(process.argv[3]);
  }else{
    const expression=process.argv[2]==='file'?fs.readFileSync(process.argv[3],'utf8'):process.argv[2]||'JSON.stringify({title:document.title,text:document.body.innerText.slice(0,10000)})';
    const result=await send('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
    if(result.exceptionDetails)throw new Error(JSON.stringify(result.exceptionDetails));console.log(JSON.stringify(result.result.value??result.result));
  }
}finally{socket.close();}
