import fs from 'node:fs';
import path from 'node:path';
import { ESLint } from 'eslint';

const root=path.resolve(import.meta.dirname,'..');
const checker=new ESLint({cwd:root});
const cases=[
  {name:'required CommonJS host import',code:"module.exports = require('obsidian');",expectedRule:null},
  {name:'unapproved CommonJS import',code:"module.exports = require('unapproved-module');",expectedRule:'@typescript-eslint/no-require-imports'},
  {name:'unsafe HTML assignment',code:'module.exports = (element, value) => { element.innerHTML = value; };',expectedRule:'no-unsanitized/property'},
];
const results=[];
for(const item of cases){
  const [result]=await checker.lintText(item.code,{filePath:path.join(root,'plugin/lint-control.js')});
  const passed=item.expectedRule?result.messages.some(message=>message.ruleId===item.expectedRule&&message.severity===2):result.errorCount===0;
  results.push({name:item.name,passed,errorCount:result.errorCount,messages:result.messages.map(message=>({rule:message.ruleId,severity:message.severity,message:message.message}))});
}
const fixture=path.join(root,'plugin/api-version-negative-control.js');
if(fs.existsSync(fixture))throw new Error('Unexpected existing negative-control file');
try{
  fs.writeFileSync(fixture,"/** @param {import('obsidian').App} app */\nmodule.exports = function requiresNewApi(app) { return app.isDarkMode(); };\n");
  // Deliberately exercise the stricter historical contract independently of
  // the conservative native-tested minimum in the release manifest.
  const compatibility=new ESLint({cwd:root,overrideConfigFile:path.join(root,'eslint.compat.config.mjs'),overrideConfig:{rules:{'obsidianmd/no-unsupported-api':['error',{minAppVersion:'1.8.0'}]}}});
  const [result]=await compatibility.lintFiles([fixture]);
  const messages=result.messages.map(message=>({rule:message.ruleId,severity:message.severity,message:message.message}));
  results.push({name:'API introduced in 1.10.0 rejected by deliberately stricter 1.8.0 negative control',passed:messages.some(message=>message.rule==='obsidianmd/no-unsupported-api'&&message.severity===2&&message.message.includes('1.10.0')),errorCount:result.errorCount,messages});
}finally{
  if(!fixture.startsWith(root+path.sep))throw new Error('Cleanup target outside candidate');
  fs.unlinkSync(fixture);
}
console.log(JSON.stringify({passed:results.every(result=>result.passed),results},null,2));
process.exitCode=results.every(result=>result.passed)?0:1;
