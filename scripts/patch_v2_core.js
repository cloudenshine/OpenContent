const fs = require('fs');
const path = require('path');

const mainJsPath = path.join(__dirname, '../plugin/main.js');
let code = fs.readFileSync(mainJsPath, 'utf8');

// 1. Add requires for engine modules at top
const engineRequires = `
let domainEngine, pipelineEngine, typographyEngine;
try {
  domainEngine = require('./engine/domain.js');
  pipelineEngine = require('./engine/pipeline.js');
  typographyEngine = require('./engine/typography.js');
} catch(e) {
  try {
    domainEngine = require('../plugin/engine/domain.js');
    pipelineEngine = require('../plugin/engine/pipeline.js');
    typographyEngine = require('../plugin/engine/typography.js');
  } catch(e2) {}
}
`;

if (!code.includes('domainEngine')) {
  code = code.replace("const AXES = ['Evidence','Logic','Originality','Voice','Utility'];", "const AXES = ['Evidence','Logic','Originality','Voice','Utility'];\n" + engineRequires);
}

// 2. Update DEFAULTS with viewMode, typographyTheme, feedingFolders
if (!code.includes("viewMode: 'simple'")) {
  code = code.replace(
    "const DEFAULTS = {python: 'python'",
    "const DEFAULTS = {viewMode: 'simple', typographyTheme: 'serif', feedingFolders: ['得到大脑','我的知识库/收件箱','收件箱','00_Inbox','Clippings'], python: 'python'"
  );
}

// 3. Add mode toggle and shield in Cockpit.renderOnce
const navTarget = "const nav=el(root,'nav',undefined,'oc-nav');";
const navReplacement = `const nav=el(root,'nav',undefined,'oc-nav');
    // Dual-Mode bar
    const modeBar = el(root, 'div', undefined, 'oc-mode-bar');
    const isExpert = this.plugin.settings.viewMode === 'expert';
    const modeBadge = el(modeBar, 'span', isExpert ? '🛡️ 专家门禁模式' : '⚡ 极简创作模式', 'oc-mode-badge ' + (isExpert ? 'expert' : 'simple'));
    modeBadge.title = '点击切换：默认极简3步流 vs 深度五轴门禁与雷达';
    modeBadge.onclick = async () => {
      this.plugin.settings.viewMode = isExpert ? 'simple' : 'expert';
      await this.plugin.saveData(this.plugin.settings);
      await this.render();
    };
    const modeHint = el(modeBar, 'span', isExpert ? '已展开完整证明链与对抗审核' : '轻量3步：选题 → 论据 → 正文', 'oc-muted');
    modeHint.style.fontSize = '11px';`;

if (!code.includes('oc-mode-bar')) {
  code = code.replace(navTarget, navReplacement);
}

fs.writeFileSync(mainJsPath, code, 'utf8');
console.log('Engine requires, defaults, and dual-mode bar injected.');
