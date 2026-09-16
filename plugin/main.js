/* Thin desktop cockpit. All domain rules and long-running work live in the Kernel. */
const {Plugin, ItemView, Modal, Setting, PluginSettingTab, Notice, requestUrl, FileSystemAdapter} = require('obsidian');
const {spawn} = require('child_process');
const path = require('path');
const fs = require('fs');
const VIEW = 'opencontent-cockpit';
const DEFAULTS = {viewMode: 'simple', typographyTheme: 'serif', preferredModel: '', feedingFolders: ['得到大脑','我的知识库/收件箱','收件箱','00_Inbox','Clippings'], python: 'python', kernelPath: '', codex: '', skillRoots: '', reviewer: '', lastProject: '', lastArtifact: '', ideationFolders: [], ideationLimit: 24, ideationDirection: ''};
const LABELS = {CAPTURED:'已捕获', DISTILLED:'已提炼', IDEA:'想法', RESEARCHING:'研究中', ARGUMENT_READY:'论证就绪', DRAFTING:'起草中', REVIEWING:'待审查', APPROVED:'已批准', PUBLISHED:'已发布', LEARNING:'观察记录'};
const AXES = ['Evidence','Logic','Originality','Voice','Utility'];

const crypto = require('crypto');

const pipelineEngine = (() => {

const DEFAULT_FEEDING_DIRS = [
  '得到大脑',
  '我的知识库/收件箱',
  '收件箱',
  '00_Inbox',
  'Clippings'
];

function digest(content) {
  return crypto.createHash('sha256').update(content, 'utf8').digest('hex');
}

/**
 * Extract clean text and key phrases from Markdown file
 */
function extractNoteSummary(content, maxLength = 600) {
  // Strip YAML frontmatter
  const clean = content.replace(/^---[\s\S]*?---\s*/, '').trim();
  // Strip code blocks and links markdown formatting
  const plainText = clean
    .replace(/```[\s\S]*?```/g, '')
    .replace(/\[\[(?:[^\]|]+\|)?([^\]]+)\]\]/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/[#*`>_-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  return plainText.slice(0, maxLength);
}

/**
 * Scan configured intake folders for notes
 */
async function scanIntakeSources(appVault, customFolders = []) {
  const targetDirs = customFolders.length ? customFolders : DEFAULT_FEEDING_DIRS;
  const items = [];

  // If running in Obsidian runtime
  if (appVault && typeof appVault.getMarkdownFiles === 'function') {
    const allFiles = appVault.getMarkdownFiles();
    for (const file of allFiles) {
      if (targetDirs.some(dir => file.path.startsWith(dir + '/') || file.path.startsWith(dir + '\\'))) {
        const content = await appVault.read(file);
        items.push({
          path: file.path,
          name: file.name,
          title: file.basename,
          body: extractNoteSummary(content),
          rawLength: content.length,
          mtime: file.stat?.mtime || Date.now(),
          hash: digest(content)
        });
      }
    }
  }

  return items;
}

/**
 * Cluster notes into thematic clusters using n-gram / token frequency overlap
 */
function clusterNotes(notes, threshold = 0.15) {
  const tokenized = notes.map(note => {
    const text = (note.title + ' ' + note.body).toLowerCase();
    // Match chinese 2-grams and english words
    const tokens = new Set();
    const words = text.match(/[a-zA-Z0-9_\u4e00-\u9fa5]+/g) || [];
    for (const w of words) {
      if (w.length >= 2) tokens.add(w);
      if (/[\u4e00-\u9fa5]/.test(w)) {
        for (let i = 0; i < w.length - 1; i++) {
          tokens.add(w.slice(i, i + 2));
        }
      }
    }
    return { ...note, tokens };
  });

  const clusters = [];
  const assigned = new Set();

  for (let i = 0; i < tokenized.length; i++) {
    if (assigned.has(i)) continue;
    const current = tokenized[i];
    const group = [current];
    assigned.add(i);

    for (let j = i + 1; j < tokenized.length; j++) {
      if (assigned.has(j)) continue;
      const target = tokenized[j];
      
      // Jaccard similarity
      let intersection = 0;
      for (const t of current.tokens) {
        if (target.tokens.has(t)) intersection++;
      }
      const union = current.tokens.size + target.tokens.size - intersection;
      const sim = union > 0 ? intersection / union : 0;

      if (sim >= threshold) {
        group.push(target);
        assigned.add(j);
      }
    }

    if (group.length >= 2) {
      clusters.push({
        topic: group[0].title + ' 等多源关联',
        sources: group.map(g => ({ path: g.path, title: g.title, body: g.body, hash: g.hash })),
        count: group.length
      });
    }
  }

  return clusters;
}

/**
 * Generate candidate ideation cards from cluster
 */
function generateIdeationCandidates(cluster) {
  const sources = cluster.sources.map(s => s.path);
  const titles = cluster.sources.map(s => s.title);
  const sourceA = cluster.sources[0];
  const sourceB = cluster.sources[1] || sourceA;
  const folders = Array.from(new Set(cluster.sources.map(s => {
    const parts = s.path.split('/');
    return parts.length > 1 ? parts.slice(0, -1).join('/') : '.';
  })));

  return {
    id: digest(sources.join(':')).slice(0, 32),
    title: `候选素材组：${titles.slice(0, 2).join(' + ')}${titles.length > 2 ? ` 等 ${titles.length} 篇` : ''}`,
    direction: `围绕「${titles.slice(0, 2).join('」与「')}」的交集展开选题`,
    sources: sources,
    folders: folders,
    clusterSize: cluster.count
  };
}


  return { DEFAULT_FEEDING_DIRS, extractNoteSummary, scanIntakeSources, clusterNotes, generateIdeationCandidates };
})();

const typographyEngine = (() => {
const THEMES = {
  serif: {
    id: 'serif',
    name: '优雅衬线',
    description: '人文、思想随笔、深度长文（类似纽约客/端传媒风格）',
    containerStyle: 'font-family: -apple-system-font, "Songti SC", "SimSun", "Noto Serif SC", STSong, serif; line-height: 1.85; color: #2c2c2c; background-color: #fcfcfb; padding: 24px; max-width: 680px; margin: 0 auto; letter-spacing: 0.03em;',
    h1Style: 'font-size: 24px; font-weight: 700; color: #111; margin: 28px 0 16px 0; border-bottom: 2px solid #8c7853; padding-bottom: 8px; letter-spacing: 0.05em;',
    h2Style: 'font-size: 20px; font-weight: 600; color: #222; margin: 24px 0 12px 0; border-left: 3px solid #8c7853; padding-left: 10px;',
    h3Style: 'font-size: 17px; font-weight: 600; color: #333; margin: 20px 0 8px 0;',
    pStyle: 'font-size: 15px; margin: 0 0 16px 0; text-align: justify; color: #333;',
    blockquoteStyle: 'margin: 20px 0; padding: 12px 18px; border-left: 3px solid #c4b59d; background: #f7f5f0; color: #555; font-style: normal; border-radius: 0 4px 4px 0;',
    strongStyle: 'color: #8c2d19; font-weight: 600;',
    codeStyle: 'background: #f0ede6; color: #723223; padding: 2px 6px; border-radius: 3px; font-family: monospace; font-size: 14px;',
    listStyle: 'padding-left: 20px; margin-bottom: 16px; font-size: 15px; color: #333;',
    dividerStyle: 'border: none; border-top: 1px dashed #d8d2c4; margin: 32px 0;'
  },
  academic: {
    id: 'academic',
    name: '学术极简',
    description: '严谨论文、行业报告、白皮书风格（黑白灰高对比度）',
    containerStyle: 'font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif; line-height: 1.75; color: #1a1a1a; background-color: #ffffff; padding: 24px; max-width: 680px; margin: 0 auto;',
    h1Style: 'font-size: 22px; font-weight: 700; color: #000; margin: 26px 0 14px 0; border-bottom: 1px solid #111; padding-bottom: 6px;',
    h2Style: 'font-size: 18px; font-weight: 600; color: #111; margin: 22px 0 10px 0; border-bottom: 1px solid #e0e0e0; padding-bottom: 4px;',
    h3Style: 'font-size: 16px; font-weight: 600; color: #222; margin: 18px 0 8px 0;',
    pStyle: 'font-size: 15px; margin: 0 0 14px 0; text-align: justify; color: #2a2a2a;',
    blockquoteStyle: 'margin: 16px 0; padding: 10px 16px; border-left: 2px solid #222; background: #fafafa; color: #444;',
    strongStyle: 'color: #000; font-weight: 700;',
    codeStyle: 'background: #f3f3f3; color: #000; padding: 2px 4px; border-radius: 2px; font-family: Consolas, monospace; font-size: 13.5px;',
    listStyle: 'padding-left: 20px; margin-bottom: 14px; font-size: 14.5px; color: #2a2a2a;',
    dividerStyle: 'border: none; border-top: 1px solid #eaeaea; margin: 28px 0;'
  },
  techDark: {
    id: 'techDark',
    name: '科技深色',
    description: '前沿极客、技术布道、现代数码风格（深空灰配科技蓝/紫霓虹）',
    containerStyle: 'font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif; line-height: 1.8; color: #e2e8f0; background-color: #0f172a; padding: 28px; max-width: 680px; margin: 0 auto; border-radius: 8px;',
    h1Style: 'font-size: 24px; font-weight: 700; color: #38bdf8; margin: 28px 0 16px 0; border-bottom: 1px solid #1e293b; padding-bottom: 8px;',
    h2Style: 'font-size: 20px; font-weight: 600; color: #818cf8; margin: 24px 0 12px 0; padding-left: 8px; border-left: 3px solid #38bdf8;',
    h3Style: 'font-size: 17px; font-weight: 600; color: #cbd5e1; margin: 20px 0 8px 0;',
    pStyle: 'font-size: 15px; margin: 0 0 16px 0; color: #cbd5e1; text-align: justify;',
    blockquoteStyle: 'margin: 20px 0; padding: 12px 16px; border-left: 3px solid #6366f1; background: #1e293b; color: #94a3b8; border-radius: 4px;',
    strongStyle: 'color: #38bdf8; font-weight: 600;',
    codeStyle: 'background: #1e293b; color: #f43f5e; padding: 2px 6px; border-radius: 4px; font-family: Consolas, monospace; font-size: 14px;',
    listStyle: 'padding-left: 20px; margin-bottom: 16px; font-size: 15px; color: #cbd5e1;',
    dividerStyle: 'border: none; border-top: 1px solid #334155; margin: 30px 0;'
  }
};

/**
 * Render Markdown body into rich HTML with theme inline styles
 */
function cleanReaderText(markdown) {
  let text = String(markdown || '').replace(/^---[\s\S]*?---\s*/, '').trim();
  // Clean internal claim link tags like [[claim-id]] or [[claim-id|alias]]
  return text.replace(/\[\[([0-9a-f]{32})(?:\|[^\]]+)?\]\]/g, '');
}

function renderArticleHtml(markdown, themeId = 'serif', title = '') {
  const theme = THEMES[themeId] || THEMES.serif;
  
  const text = cleanReaderText(markdown);
  const lines = text.split(/\r?\n/);
  const htmlParts = [];

  const firstNonEmpty = lines.find(l => l.trim().length > 0) || '';
  if (title && !firstNonEmpty.startsWith('# ')) {
    htmlParts.push(`<h1 style="${theme.h1Style}">${escapeHtml(title)}</h1>`);
  }

  let inList = false;
  let inBlockquote = false;
  let quoteBuffer = [];

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const line = rawLine.trim();

    if (!line) {
      if (inList) { htmlParts.push('</ul>'); inList = false; }
      if (inBlockquote) {
        htmlParts.push(`<blockquote style="${theme.blockquoteStyle}">${formatInline(quoteBuffer.join('<br>'), theme)}</blockquote>`);
        inBlockquote = false;
        quoteBuffer = [];
      }
      continue;
    }

    if (line.startsWith('# ')) {
      htmlParts.push(`<h1 style="${theme.h1Style}">${formatInline(line.slice(2), theme)}</h1>`);
    } else if (line.startsWith('## ')) {
      htmlParts.push(`<h2 style="${theme.h2Style}">${formatInline(line.slice(3), theme)}</h2>`);
    } else if (line.startsWith('### ')) {
      htmlParts.push(`<h3 style="${theme.h3Style}">${formatInline(line.slice(4), theme)}</h3>`);
    } else if (line.startsWith('> ')) {
      inBlockquote = true;
      quoteBuffer.push(escapeHtml(line.slice(2)));
    } else if (/^[-*]\s+/.test(line)) {
      if (!inList) { htmlParts.push(`<ul style="${theme.listStyle}">`); inList = true; }
      htmlParts.push(`<li>${formatInline(line.replace(/^[-*]\s+/, ''), theme)}</li>`);
    } else if (/^---+$/.test(line) || /^===+$/.test(line)) {
      htmlParts.push(`<hr style="${theme.dividerStyle}" />`);
    } else {
      htmlParts.push(`<p style="${theme.pStyle}">${formatInline(line, theme)}</p>`);
    }
  }

  if (inList) htmlParts.push('</ul>');
  if (inBlockquote) {
    htmlParts.push(`<blockquote style="${theme.blockquoteStyle}">${formatInline(quoteBuffer.join('<br>'), theme)}</blockquote>`);
  }

  return `<section class="opencontent-rendered-article" style="${theme.containerStyle}">\n${htmlParts.join('\n')}\n</section>`;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatInline(text, theme) {
  let res = escapeHtml(text);
  // Bold
  res = res.replace(/\*\*(.*?)\*\*/g, `<strong style="${theme.strongStyle}">$1</strong>`);
  // Inline Code
  res = res.replace(/`([^`]+)`/g, `<code style="${theme.codeStyle}">$1</code>`);
  return res;
}

/**
 * Copy rendered rich text to system clipboard
 */
async function copyRichTextToClipboard(htmlString, plainText) {
  const cleanedText = cleanReaderText(plainText);
  if (typeof navigator !== 'undefined' && navigator.clipboard && typeof ClipboardItem !== 'undefined') {
    const blobHtml = new Blob([htmlString], { type: 'text/html' });
    const blobText = new Blob([cleanedText], { type: 'text/plain' });
    await navigator.clipboard.write([
      new ClipboardItem({
        'text/html': blobHtml,
        'text/plain': blobText
      })
    ]);
    return true;
  }
  return false;
}


  return { THEMES, cleanReaderText, renderArticleHtml, copyRichTextToClipboard };
})();

function el(parent, tag, text, cls) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = String(text);
  if (cls) node.className = cls;
  parent.appendChild(node); return node;
}
function button(parent, text, callback, cls) {
  const b = el(parent,'button',text,cls); b.type='button';
  b.addEventListener('click', async () => {
    b.disabled=true;b.setAttribute('aria-busy','true');
    if(b.feedback)b.feedback.remove();
    try { await callback(); } catch(e) {
      b.feedback=el(parent,'p',e.message,'oc-error oc-feedback');b.feedback.setAttribute('role','alert');
      new Notice(e.message,10000);
    }
    finally { b.disabled=false;b.removeAttribute('aria-busy'); }
  }); return b;
}
function field(parent, label, value='', multiline=false) {
  const wrap = el(parent,'label',undefined,'oc-field'); el(wrap,'span',label);
  const input=el(wrap,multiline?'textarea':'input'); input.value=value;
  input.setAttribute('aria-label',label); return input;
}

class FormModal extends Modal {
  constructor(plugin, title, build) { super(plugin.app); this.plugin=plugin; this.formTitle=title; this.buildForm=build; }
  onOpen() { this.contentEl.empty(); this.contentEl.addClass('oc-modal'); el(this.contentEl,'h2',this.formTitle); this.buildForm(this.contentEl,this); }
  onClose() { this.contentEl.empty(); }
}

class Cockpit extends ItemView {
  constructor(leaf,plugin) { super(leaf); this.plugin=plugin; this.tab='board'; this.selected=plugin.settings.lastProject; this.artifact=plugin.settings.lastArtifact; }
  getViewType(){return VIEW;}
  getDisplayText(){return 'OpenContent';}
  getIcon(){return 'workflow';}
  async onOpen(){ await this.render(); }
  async render(){
    if(this.rendering){this.renderAgain=true;return this.rendering;}
    this.rendering=(async()=>{do{this.renderAgain=false;await this.renderOnce();}while(this.renderAgain);})();
    try{await this.rendering;}finally{this.rendering=null;}
  }
  async renderOnce(){
    const previousScroll=this.contentEl.scrollTop;
    const focused=document.activeElement;
    const inputLabel=focused?.getAttribute('aria-label');
    const typing=['给这个项目的指令','告诉我你的想法'].includes(inputLabel)&&this.contentEl.contains(focused);
    const cursor=typing?[focused.selectionStart,focused.selectionEnd]:null;
    const root=this.contentEl; root.empty(); root.addClass('oc-root');
    const heading=el(root,'div',undefined,'oc-header'); el(heading,'h1','OpenContent');
    el(heading,'p','把你的笔记，写成值得分享的文章。');
    const nav=el(root,'nav',undefined,'oc-nav');
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
    modeHint.style.fontSize = '11px';
    const current=['project','conversation','inspector','inbox'].includes(this.tab)?'project':this.tab;
    for(const [id,title] of [['board','首页'],['project','写作'],['publishing','发布']]){
      const b=button(nav,title,async()=>{this.tab=id;await this.render();},id===current?'mod-cta':'');
      if(id===current)b.setAttribute('aria-current','page');
    }
    const more=el(nav,'details',undefined,'oc-more');el(more,'summary','更多');
    for(const [id,title] of [['sources','材料库'],['inbox','待处理稿件']])button(more,title,async()=>{this.tab=id;await this.render();});
    button(more,'连接设置',()=>this.plugin.configure());
    const content=el(root,'div',undefined,'oc-content');
    let connected=false;
    try{
      const data=await this.plugin.api('/board');connected=true; this.data=data;
      this.plugin.jobsActive=data.jobs.some(j=>['QUEUED','RUNNING'].includes(j.status));
      if(data.diagnostics.length) el(content,'pre','Vault 诊断（已阻止推进）：\n'+data.diagnostics.join('\n'),'oc-error');
      if(!data.projects.some(p=>p.oc_id===this.selected)) this.selected=data.projects[0]?.oc_id||null;
      if(this.tab==='board') await this.board(content,data);
      if(this.tab==='inbox') this.inbox(content,data);
      if(this.tab==='project') await this.project(content,data);
      if(this.tab==='inspector') await this.inspector(content,data);
      if(this.tab==='sources') await this.sources(content,data);
      if(this.tab==='publishing') await this.publishing(content,data);
      if(this.tab==='conversation') await this.project(content,data);
      this.jobs(content,data);
      await this.plugin.remember(this.selected,this.artifact);
      root.scrollTop=previousScroll;
      if(typing){const editor=root.querySelector(`textarea[aria-label="${inputLabel}"]`);if(editor){editor.focus();editor.setSelectionRange(...cursor);}}
    }catch(e){
      if(connected){el(content,'p','当前操作未完成：'+e.message,'oc-error');button(content,'重试当前页面',()=>this.render());return;}
      el(content,'h3','暂时无法连接');
      el(content,'p','笔记仍保存在本地。重新连接后可以继续。');
      button(content,'重新连接',async()=>{await this.plugin.startKernel();await this.render();},'mod-cta');
      const help=el(content,'details');el(help,'summary','查看原因与修复');
      el(help,'p',e.message,'oc-error');
      button(help,'检查本地环境',()=>this.plugin.checkEnvironment());
      button(help,'连接设置',()=>this.plugin.configure());
    }
  }
  projectSelect(root,data){
    const select=el(root,'select'); select.setAttribute('aria-label','正在写的文章');
    for(const p of data.projects){ const opt=el(select,'option',p.title);opt.value=p.oc_id;opt.selected=p.oc_id===this.selected; }
    select.addEventListener('change',async()=>{this.selected=select.value;this.artifact=null;await this.render();});
    return data.projects.find(p=>p.oc_id===this.selected);
  }
  async board(root,data){
    // Auto-Feeding Pipeline Banner
    if (pipelineEngine && this.app?.vault) {
      const feedBanner = el(root, 'section', undefined, 'oc-pipeline-banner');
      const feedHeader = el(feedBanner, 'div', undefined, 'oc-pipeline-header');
      const feedTitle = el(feedHeader, 'div', '⚡ 灵感自动喂养管道 (Auto-Feeding)', 'oc-pipeline-title');
      const scanBtn = button(feedHeader, '扫描新灵感', async () => {
        try {
          scanBtn.textContent = '正在挖掘灵感…';
          scanBtn.disabled = true;
          const notes = await pipelineEngine.scanIntakeSources(this.app.vault, this.plugin.settings.feedingFolders || []);
          if (!notes.length) {
            new Notice('在收件箱/得到大脑等入口未发现新的 Markdown 笔记');
            return;
          }
          const clusters = pipelineEngine.clusterNotes(notes, 0.12);
          if (!clusters.length) {
            new Notice('笔记已扫描（' + notes.length + ' 篇），暂未形成显著跨资料主题聚类');
            return;
          }
          this.feedingClusters = clusters.slice(0, 3);
          new Notice('已发现 ' + clusters.length + ' 组跨资料灵感选题！');
          await this.render();
        } catch(err) {
          new Notice('自动喂养扫描失败: ' + err.message);
        } finally {
          scanBtn.textContent = '扫描新灵感';
          scanBtn.disabled = false;
        }
      });
      el(feedBanner, 'p', '基于本地笔记关键词重合度召回关联素材组。深度选题通过正式选题内核校验片段依据与来源独立性。', 'oc-muted');

      if (this.feedingClusters && this.feedingClusters.length) {
        for (const cluster of this.feedingClusters) {
          const candidate = pipelineEngine.generateIdeationCandidates(cluster);
          const card = el(feedBanner, 'div', undefined, 'oc-candidate-card');
          el(card, 'h4', candidate.title);
          el(card, 'p', '🎯 建议探索方向：' + candidate.direction);
          el(card, 'small', '📚 关联素材（共 ' + candidate.clusterSize + ' 篇）：' + candidate.sources.join('、'));
          button(card, '为此素材组深入选题 (使用正式选题内核)', async () => {
            this.discoverIdeas(null, candidate.folders, candidate.direction);
          }, 'mod-cta');
        }
      }
    }

    const hero=el(root,'section',undefined,'oc-start');el(hero,'h2','今天想写点什么？');
    let sync=()=>{};
    const input=field(hero,'告诉我你的想法',this.homeGoal||'',true);
    input.placeholder='例如：把读书笔记写成一篇新手也能看懂的文章';input.maxLength=4000;
    input.addEventListener('input',()=>{this.homeGoal=input.value;sync();});
    const file=this.app.workspace.getActiveFile()||this.plugin.lastNote;
    let selected=null,check=null;
    if(file?.extension==='md'&&!file.path.split('/').some(p=>p.startsWith('.')||p.startsWith('_')||['OpenContent','OpenContent-Exports','OpenContent-Workspace','Attachments','node_modules','archive'].includes(p))&&!['CONTENT.md','AGENTS.md','SKILL.md'].includes(file.name)){
      const raw=await this.app.vault.adapter.readBinary(file.path);
      selected={path:file.path,hash:require('crypto').createHash('sha256').update(Buffer.from(raw)).digest('hex')};
      const label=el(hero,'label',undefined,'oc-context-chip');check=el(label,'input');check.type='checkbox';
      check.checked=this.homeNotePath===file.path?this.homeUseNote!==false:true;
      el(label,'span','使用当前笔记：'+file.basename);
      check.addEventListener('change',()=>{this.homeNotePath=file.path;this.homeUseNote=check.checked;sync();});
    }
    const scope=el(hero,'p',undefined,'oc-muted');
    const start=button(hero,'开始写作',async()=>{
      const goal=input.value.trim();if(!goal)throw new Error('先写一句你想做什么。');
      const usingNote=Boolean(check?.checked);
      const providers=await this.plugin.api('/providers');
      if(!Object.keys(providers.active).length)throw new Error(providers.notice||'没有可用的写作助手，请在“更多 → 连接设置”检查本地工具。');
      const p=await this.plugin.api('/projects/selected',{title:goal.slice(0,60),goal,audience:'对这个主题感兴趣的普通读者',selected:usingNote?[selected]:[],token:data.token});
      this.selected=p.oc_id;this.artifact=null;this.homeGoal='';this.tab='project';
      await this.plugin.remember(p.oc_id,null);
      try{
        const detail=await this.plugin.api('/objects/'+p.oc_id);
        if(usingNote)await this.plugin.api('/jobs',{project:p.oc_id,token:detail.token});
        else await this.plugin.api('/conversation/send',{project:p.oc_id,instruction:goal,mode:'discuss',token:detail.token});
        this.plugin.jobsActive=true;
      }catch(e){this.startError={project:p.oc_id,message:e.message};if(!usingNote){this.composers||={};this.composers[p.oc_id]=goal;}}
      await this.render();
    },'mod-cta');
    sync=()=>{start.disabled=!input.value.trim();start.textContent=check?.checked?'开始写作':'一起构思';scope.textContent=check?.checked?'只使用这篇笔记和你的要求，交给本地写作助手起草。':'先聊清楚想法，需要资料时再添加。';};sync();
    const actions=el(root,'div',undefined,'oc-actions');
    button(actions,'帮我找选题',()=>this.discoverIdeas());button(actions,'自己选择材料',()=>this.newProject({goal:input.value}));
    if(data.projects.length)el(root,'h2','最近的文章');
    const priority=p=>data.inbox.some(i=>i.project===p.oc_id)?0:p.oc_id===this.plugin.settings.lastProject?1:p.effective_state==='APPROVED'?3:2;
    for(const p of [...data.projects].sort((a,b)=>priority(a)-priority(b))){
      const card=el(root,'article',undefined,'oc-card oc-continue');
      el(card,'h3',p.title);el(card,'p',LABELS[p.effective_state]);
      if(p.planning?.planned_for)el(card,'small','计划发表：'+p.planning.planned_for);
      const pending=data.inbox.filter(i=>i.project===p.oc_id);
      const running=data.jobs.some(j=>j.project===p.oc_id&&['QUEUED','RUNNING'].includes(j.status));
      let label=running?'查看进度':pending.length?'看看稿子':p.effective_state==='APPROVED'?'准备发布':['PUBLISHED','LEARNING'].includes(p.effective_state)?'查看发表记录':'继续写';
      el(card,'p',running?'后台任务正在运行，你可以继续编辑其他笔记。':pending.length?`${pending.length} 篇稿件需要判断；先处理证据和质量问题。`:!p.counts.Material?'捕获一段材料即可开始，不必手工搭建对象。':p.thesis||p.goal,'oc-muted');
      button(card,label,async()=>{
        this.selected=p.oc_id;this.artifact=p.artifacts[0]?.oc_id||null;
        this.tab=['APPROVED','PUBLISHED','LEARNING'].includes(p.effective_state)?'publishing':'project';
        await this.render();
      },'mod-cta');
    }
    if(!data.projects.length)return;
    const overview=el(root,'details');el(overview,'summary','查看全部文章进度');
    const board=el(overview,'div',undefined,'oc-board');
    const columns=[['Captured',['CAPTURED']],['Distilling',['DISTILLED']],['Ideas',['IDEA']],['Researching',['RESEARCHING','ARGUMENT_READY']],['Drafting',['DRAFTING']],['Reviewing',['REVIEWING']],['Ready',['APPROVED']],['Published',['PUBLISHED','LEARNING']]];
    for(const [name,stages] of columns){
      const projects=data.projects.filter(p=>stages.includes(p.effective_state));
      const col=el(board,'section',undefined,'oc-column');el(col,'h3',name+' · '+projects.length);el(col,'small',stages.map(s=>LABELS[s]).join(' / '));
      for(const p of projects){
        const card=el(col,'article',undefined,'oc-card');
        button(card,p.title,async()=>{this.selected=p.oc_id;this.tab='project';await this.render();},'oc-title');
        el(card,'p',p.thesis || p.goal);el(card,'small',`${p.counts.Material} 材料 · ${p.counts.Claim} 主张 · ${p.artifacts.length} 草稿`);
        if(p.state!==p.effective_state) el(card,'p','内容有变更，原批准已失效','oc-error');
      }
    }
  }
  newProject(seed={}){
    new FormModal(this.plugin,'创建内容项目',(root,modal)=>{
      const goal=field(root,'你想写什么',seed.goal||'',true);
      const preferences=el(root,'details');el(preferences,'summary','标题与读者（可选）');
      const title=field(preferences,'文章标题',seed.title||'');const audience=field(preferences,'写给谁看',seed.audience||'对这个主题感兴趣的普通读者');
      el(root,'p','填写目标后自动检索本地笔记，勾选后随项目一起捕获。推荐过程不调用模型。','oc-muted');
      const status=el(root,'p','正在检索…');const list=el(root,'div',undefined,'oc-note-list');
      const chosen=new Map();if(seed.path)chosen.set(seed.path,{path:seed.path,hash:seed.hash});
      let snapshot=null,serial=0,timer=null;
      const refresh=async()=>{const current=++serial;try{
        const result=await this.plugin.api('/discovery',{goal:goal.value});if(current!==serial||!root.isConnected)return;
        snapshot=result;list.replaceChildren();status.textContent=`扫描 ${result.stats.scanned} 篇 · 推荐 ${result.candidates.length} 篇${result.stats.limited?'（达到扫描上限）':''}`;
        for(const n of result.candidates){
          const card=el(list,'article',undefined,'oc-card');const label=el(card,'label');const check=el(label,'input');check.type='checkbox';check.checked=chosen.has(n.path);
          check.addEventListener('change',()=>check.checked?chosen.set(n.path,{path:n.path,hash:n.hash}):chosen.delete(n.path));el(label,'strong',n.title);
          el(card,'small',n.path);el(card,'p',n.excerpt);el(card,'small','相关词：'+(n.matches.join('、')||'未限定主题'));
          for(const p of n.existing_projects)el(card,'p',`已用于「${p.title}」· ${LABELS[p.state]}，可复用材料但请区分新角度。`,'oc-muted');
          button(card,'打开原文',()=>this.plugin.openNote(n.path));
        }
        if(!result.candidates.length)el(list,'p','没有匹配笔记，可改写目标关键词，或先创建空项目。');
      }catch(e){snapshot=null;status.textContent=e.message;}};
      goal.addEventListener('input',()=>{clearTimeout(timer);snapshot=null;serial++;timer=setTimeout(refresh,500);});
      button(root,'刷新推荐',refresh);
      button(root,'创建并捕获所选材料',async()=>{
        if(!snapshot)throw new Error('请等待材料推荐刷新完成。');
        const p=await this.plugin.api('/projects/selected',{title:title.value.trim()||goal.value.trim().slice(0,60),goal:goal.value,audience:audience.value,selected:[...chosen.values()],token:snapshot.token});
        clearTimeout(timer);this.selected=p.oc_id;this.tab='project';modal.close();await this.render();
      },'mod-cta');refresh();
    }).open();
  }
  discoverIdeas(runId=null, initialFolders=null, initialDirection=null){
    new FormModal(this.plugin,'发现选题灵感',(root,modal)=>{
      el(root,'p','先选择围绕同一个读者问题的资料范围，再归纳主题、比较观点并生成写作角度。候选需要你判断，不等于已核实的结论。');
      const query=field(root,'希望探索的方向',initialDirection || this.plugin.settings.ideationDirection||'');
      const range=el(root,'details');el(range,'summary','选择资料目录与数量');
      el(range,'p','未勾选目录时检索全部允许范围；勾选后只使用这些目录及其子目录。根目录只包含根目录笔记。','oc-muted');
      const directories=el(range,'div',undefined,'oc-scope-list');
      const selectedFolders=new Set(initialFolders || this.plugin.settings.ideationFolders||[]);
      const limit=field(range,'最多参与综合的资料数（2–60）',String(this.plugin.settings.ideationLimit||24));limit.type='number';limit.min='2';limit.max='60';
      const scope=el(root,'p','正在准备资料范围…');scope.setAttribute('role','status');
      const provider=el(root,'select');provider.setAttribute('aria-label','选题综合 CLI');const tools=el(root,'div');const list=el(root,'div');
      let snapshot=null,currentRun=runId,serial=0;
      const dirty=()=>{serial++;snapshot=null;currentRun=null;list.replaceChildren();scope.textContent='范围或方向已改变，点击生成即可使用新范围。';};
      query.addEventListener('input',dirty);limit.addEventListener('input',dirty);
      const loadScope=async()=>{
        const r=await this.plugin.api('/ideation/scope');if(!root.isConnected)return;
        const folders=[...r.folders,...[...selectedFolders].filter(p=>!r.folders.some(f=>f.path===p)).map(path=>({path,notes:0,missing:true}))];
        for(const f of folders){const label=el(directories,'label');const check=el(label,'input');check.type='checkbox';check.checked=selectedFolders.has(f.path);
          el(label,'span',`${f.path==='.'?'根目录':f.path} · ${f.notes} 篇${f.missing?'（已不存在，请取消选择）':''}`);
          check.addEventListener('change',()=>{check.checked?selectedFolders.add(f.path):selectedFolders.delete(f.path);dirty();});}
      };
      const prepare=async()=>{const ticket=++serial;const r=await this.plugin.api('/ideation/preview',{direction:query.value,folders:[...selectedFolders],limit:Number(limit.value)});if(!root.isConnected||ticket!==serial)return;
        snapshot=r;scope.textContent=`范围内 ${r.stats.in_scope??r.stats.scanned} 篇，本轮取 ${r.stats.selected} 份资料，归为 ${r.stats.source_families??r.stats.selected} 个来源组。${r.stats.sampled?'这是取样，未覆盖范围内全部资料。':''}${r.stats.limited?'扫描达到上限。':''}开始后会将摘录和已有项目摘要交给所选 CLI。`;};
      const loadProviders=async()=>{const r=await this.plugin.api('/providers');if(!root.isConnected)return;provider.replaceChildren();tools.replaceChildren();
        for(const name of Object.keys(r.active)){const o=el(provider,'option',name);o.value=name;}
        for(const cli of r.available)if(!r.active[cli.name])button(tools,'启用本地 '+cli.name,async()=>{await this.plugin.api('/providers/activate',{name:cli.name});await loadProviders();});
        if(!r.available.length&&!Object.keys(r.active).length)el(tools,'p','请先安装并登录支持的本地 CLI。','oc-error');};
      const show=async()=>{if(!root.isConnected||!currentRun)return;const watching=currentRun;const r=await this.plugin.api('/ideation/status',{id:watching});if(!root.isConnected||currentRun!==watching)return;
        list.replaceChildren();const pending=['QUEUED','RUNNING'].includes(r.status);const seconds=Math.max(0,Math.floor((Date.now()-Date.parse(r.created))/1000));
        const statusNames={QUEUED:'等待开始',RUNNING:'正在处理',SUCCEEDED:'候选已生成',FAILED:'本次失败',CANCELLED:'已取消',INTERRUPTED:'任务中断'};
        el(list,'h3',statusNames[r.status]||r.status);el(list,'p',`${r.stage==='classify'?'阶段 1/2：归纳主题与观点':'阶段 2/2：组合角度并检查重复'}${pending?` · 已用 ${seconds} 秒`:''}`);
        if(r.direction)el(list,'p','本次方向：'+r.direction,'oc-muted');
        if(pending){button(list,'取消这次综合',()=>this.plugin.api('/cancel',{id:r.id}));setTimeout(()=>show().catch(e=>el(list,'p',e.message,'oc-error')),1500);return;}
        if(r.status!=='SUCCEEDED'){
          el(list,'p',r.error||'本次未完成。','oc-error');
          el(list,'p','重试会检查资料版本，并复用仍有效的分类。资料或项目有变化时，请刷新范围重新生成。');
          button(list,'重试这次任务',async()=>{const next=await this.plugin.api('/ideation/retry',{id:r.id});currentRun=next.id;this.plugin.jobsActive=true;await show();});return;
        }
        if(r.adoption?.available===false)el(list,'p',r.adoption.reason+'。请按当前范围重新生成，下面保留历史结果供参考。','oc-error');
        const result=r.result;const themes=el(list,'details');el(themes,'summary',`查看 ${result.themes.length} 个资料主题`);
        if(r.path)button(list,'打开完整灵感笔记',()=>this.plugin.openNote(r.path));
        for(const t of result.themes){el(themes,'h4',t.label);el(themes,'p',t.summary);}
        el(list,'h3',`${result.ideas.length} 个候选角度`);
        for(const idea of result.ideas){const card=el(list,'article',undefined,'oc-card');el(card,'h3',idea.title);el(card,'strong',idea.question);el(card,'p','读者收益：'+idea.promise);
          const plan=el(card,'details');el(plan,'summary','组合理由与论证计划');el(plan,'p',idea.collision);el(plan,'p','新增角度：'+idea.novelty.difference);
          const outline=el(plan,'ol');for(const step of idea.outline)el(outline,'li',step);
          if(idea.gaps.length)el(plan,'p','还需补证：'+idea.gaps.join('；'),'oc-muted');
          const refs=el(card,'details');el(refs,'summary',`查看 ${idea.sources.length} 份资料各自的贡献`);
          for(const source of idea.sources){el(refs,'h4',source.title);el(refs,'p',source.role);const c=result.cards.find(c=>c.source===source.id);if(c)el(refs,'blockquote',c.quote);button(refs,'打开依据原文',()=>this.plugin.openNote(source.path));}
          const adopt=button(card,'采用此角度并创建项目',async()=>{const project=await this.plugin.api('/ideation/create',{run:r.id,idea:idea.id});this.selected=project.oc_id;this.tab='project';modal.close();await this.render();},'mod-cta');adopt.disabled=r.adoption?.available===false;
        }
        if(result.insufficient)el(list,'p',result.insufficient,'oc-muted');
        if(result.excluded.length){const excluded=el(list,'details');el(excluded,'summary',`排除 ${result.excluded.length} 个候选`);
          for(const idea of result.excluded){el(excluded,'strong',idea.title);el(excluded,'p',idea.excluded_reason+'；'+idea.novelty.difference);if(idea.novelty.nearest_project)button(excluded,'继续已有项目',async()=>{this.selected=idea.novelty.nearest_project;this.tab='project';modal.close();await this.render();});}}
      };
      button(root,'刷新资料范围',prepare);
      button(root,'按此范围生成选题',async()=>{
        if(!snapshot)await prepare();if(!snapshot)throw new Error('范围已改变，请重新准备。');if(!provider.value)throw new Error('请先启用一个本地 CLI。');
        Object.assign(this.plugin.settings,{ideationFolders:[...selectedFolders],ideationLimit:Number(limit.value),ideationDirection:query.value});await this.plugin.saveData(this.plugin.settings);
        const r=await this.plugin.api('/ideation/start',{preview:snapshot.id,provider:provider.value});currentRun=r.id;snapshot=null;this.plugin.jobsActive=true;await show();
      },'mod-cta');
      Promise.all([loadScope(),prepare(),loadProviders()]).then(()=>show()).catch(e=>el(list,'p',e.message,'oc-error'));
    }).open();
  }
  async project(root,data){
    const p=this.projectSelect(root,data);if(!p){await this.board(root,data);return;}
    const detail=await this.plugin.api('/objects/'+p.oc_id);
    el(root,'h2',p.title);el(root,'p',`${LABELS[p.effective_state]} · ${p.audience}`,'oc-muted');
    if(this.startError?.project===p.oc_id){
      el(root,'p','文章已保存，助手暂未开始：'+this.startError.message,'oc-error');
      el(root,'p','可以从这里继续，无需重新创建。','oc-muted');
    }
    const materials=detail.objects.filter(o=>o.type==='Material');
    const actions=el(root,'div',undefined,'oc-actions');
    button(actions,materials.length?`资料 · ${materials.length} 篇`:'添加资料',()=>this.selectMaterials(p,data));
    const running=data.jobs.some(j=>j.project===p.oc_id&&['RUNNING','QUEUED'].includes(j.status));
    if(!p.artifacts.length){
      const start=button(actions,running?'正在写作…':'写成初稿',()=>this.startProduction(p,detail),'mod-cta');start.disabled=running||!materials.length;
      if(!materials.length)el(root,'p','可以先聊想法；添加资料后，就能写成有依据的初稿。','oc-muted');
    }
    const isExpertMode = this.plugin.settings.viewMode === 'expert';

    // 默认极简创作流（Simple Mode）：只显示“1. 选题目标 → 2. 论据核心 → 3. 当前初稿”
    if (!isExpertMode) {
      const flowBox = el(root, 'div', undefined, 'oc-simple-flow');
      
      // Step 1: 选题目标
      const s1 = el(flowBox, 'div', undefined, 'oc-flow-step');
      const s1Head = el(s1, 'div', undefined, 'oc-flow-step-header');
      el(s1Head, 'span', '1', 'oc-step-badge');
      el(s1Head, 'span', '我想写什么 (Topic & Goal)');
      el(s1, 'p', p.goal || '暂未设定明确目标', 'oc-muted');

      // Step 2: 核心论据
      const s2 = el(flowBox, 'div', undefined, 'oc-flow-step');
      const s2Head = el(s2, 'div', undefined, 'oc-flow-step-header');
      el(s2Head, 'span', '2', 'oc-step-badge');
      el(s2Head, 'span', 'AI 提炼的核心论据列表 (Verified Claims)');
      const claims = detail.objects.filter(o => o.type === 'Claim');
      if (claims.length) {
        const cList = el(s2, 'div', undefined, 'oc-claim-list');
        for (const c of claims) {
          const cItem = el(cList, 'div', undefined, 'oc-claim-item');
          el(cItem, 'strong', c.title);
          if (c.body) el(cItem, 'div', c.body, 'oc-muted');
        }
      } else {
        el(s2, 'p', '尚未生成结构化论据，可在下方与助手对话或添加资料提炼。', 'oc-muted');
      }

      // Step 3: 正文初稿引导
      const s3 = el(flowBox, 'div', undefined, 'oc-flow-step');
      const s3Head = el(s3, 'div', undefined, 'oc-flow-step-header');
      el(s3Head, 'span', '3', 'oc-step-badge');
      el(s3Head, 'span', '正文草稿与快速导出 (Draft & Publish)');
    }

    if(p.artifacts.length){
      const draft=p.artifacts.find(a=>a.oc_id===this.artifact)||p.artifacts[0];this.artifact=draft.oc_id;
      const preview=el(root,'section',undefined,'oc-draft');el(preview,'h3','当前稿件');
      const prose=el(preview,'div',undefined,'oc-prose');
      const body=draft.body||detail.objects.find(o=>o.oc_id===draft.oc_id)?.body||'';
      const claims=new Set(draft.derived_from||[]);
      el(prose,'p',body.replace(/\[\[([0-9a-f]{32})(?:\|[^\]]+)?\]\]/g,(marker,id)=>claims.has(id)?'':marker));
      button(preview,'打开正文',()=>this.plugin.openNote(draft.path));
      const pending=data.inbox.find(i=>i.artifact===draft.oc_id);
      button(preview,draft.gate?.approved?'查看定稿':pending?.gate.status==='PASS'?'检查并定稿':'查看需要修改的地方',async()=>{this.tab='inspector';await this.render();});
    }
    await this.conversation(root,data,p);
    const management=el(root,'details',undefined,'oc-project-details');el(management,'summary','文章设置与资料详情');
    el(management,'h3','写作目标');el(management,'p',p.goal);el(management,'h3','核心观点');el(management,'p',p.thesis||'写作过程中逐步形成');
    const planned=field(management,'计划发表日期',p.planning?.planned_for||'');planned.type='date';
    button(management,'保存计划',async()=>{await this.plugin.api('/projects/plan',{project:p.oc_id,planned_for:planned.value,token:detail.token});await this.render();});
    const extra=el(management,'div',undefined,'oc-actions');
    button(extra,'添加摘录',()=>this.addMaterial(p,data));
    button(extra,'编辑文章设置',()=>this.plugin.openNote(p.path));
    button(extra,'编辑写作规则',()=>this.plugin.openNote('CONTENT.md'));
    const manual=el(management,'details');el(manual,'summary','高级维护');
    el(manual,'p','可直接编辑 Markdown；结构字段必须保持有效，推进时重新验证证据。');
    button(manual,'添加领域对象',()=>this.manualObject(p,data));
    button(manual,'验证并进入下一状态',()=>{
      new FormModal(this.plugin,'手动状态推进',(box,modal)=>{
        const target=data.states[data.states.indexOf(p.state)+1];el(box,'p',`${p.state} → ${target||'末状态'}`);
        const thesis=field(box,'核心论点',p.thesis||'',true);
        button(box,'验证并推进',async()=>{await this.plugin.api('/advance',{project:p.oc_id,target,token:data.token,thesis:thesis.value||undefined});modal.close();await this.render();});
      }).open();
    });
    for(const kind of ['Material','Knowledge','Idea','Claim','Evidence','Artifact','Review','Publication']){
      const rows=detail.objects.filter(o=>o.type===kind);
      if(!rows.length)continue;
      const section=el(management,'section',undefined,'oc-section');el(section,'h3',({Material:'资料',Knowledge:'知识整理',Idea:'选题',Claim:'文章观点',Evidence:'引用依据',Artifact:'稿件',Review:'检查记录',Publication:'发表记录'})[kind]);
      for(const obj of rows){
        const row=el(section,'div',undefined,'oc-row');
        button(row,obj.title,()=>this.plugin.openNote(obj.path),'oc-link');
        if(kind==='Artifact') button(row,'检查内容',async()=>{this.artifact=obj.oc_id;this.tab='inspector';await this.render();});
        if(kind==='Evidence') el(row,'span',`${obj.relation} · ${obj.quote}`);
      }
    }
  }
  async startProduction(p,detail,options={}){
    await this.plugin.api('/jobs',{...options,project:p.oc_id,token:detail.token});
    this.startError=null;this.plugin.jobsActive=true;await this.render();
  }
  selectMaterials(p,data){
    new FormModal(this.plugin,'从 Vault 选择材料',(root,modal)=>{
      el(root,'p','将所选笔记捕获为带来源路径的 Material 快照；原笔记保持原样。');
      const search=field(root,'筛选笔记'); const list=el(root,'div',undefined,'oc-note-list');const chosen=new Set();
      const draw=()=>{list.replaceChildren();for(const f of this.app.vault.getMarkdownFiles().filter(f=>!f.path.startsWith('OpenContent/')&&f.name!=='CONTENT.md'&&f.path.toLowerCase().includes(search.value.toLowerCase())).slice(0,150)){
        const label=el(list,'label');const input=el(label,'input');input.type='checkbox';input.checked=chosen.has(f.path);input.addEventListener('change',()=>input.checked?chosen.add(f.path):chosen.delete(f.path));el(label,'span',f.path);
      }};search.addEventListener('input',draw);draw();
      button(root,'捕获所选材料',async()=>{
        let token=data.token;
        for(const filePath of chosen){const file=this.app.vault.getAbstractFileByPath(filePath);const body=(await this.app.vault.read(file)).replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/,'').trim();
          const source=this.app.metadataCache.getFileCache(file)?.frontmatter?.source;
          const source_url=typeof source==='string'&&/^https?:\/\//.test(source)?source:undefined;
          await this.plugin.api('/capture',{project:p.oc_id,title:file.basename,body,source:'vault:'+file.path,source_url,token});token=(await this.plugin.api('/board')).token;
        }modal.close();await this.render();
      },'mod-cta');
    }).open();
  }
  addMaterial(p,data){
    new FormModal(this.plugin,'添加来源摘录',(root,modal)=>{
      const title=field(root,'材料名称');const source=field(root,'来源 URL / 笔记路径');const body=field(root,'材料原文','',true);
      button(root,'保存 Material',async()=>{await this.plugin.api('/objects',{project:p.oc_id,type:'Material',title:title.value,body:body.value,fields:{source:source.value},token:data.token});modal.close();await this.render();});
    }).open();
  }
  manualObject(p,data){
    new FormModal(this.plugin,'添加领域对象（无 AI）',(root,modal)=>{
      const select=el(root,'select');select.setAttribute('aria-label','对象类型');
      const samples={Knowledge:{derived_from:['Material ID']},Idea:{derived_from:['Knowledge ID']},Claim:{derived_from:['Knowledge ID'],confidence:'medium'},Evidence:{claim:'Claim ID',material:'Material ID',quote:'材料中的精确原文',relation:'supports'},Artifact:{derived_from:['Claim ID'],author:'你的署名'},Publication:{artifact:'Artifact ID',url:'https://...',published_at:new Date().toISOString()}};
      for(const kind of Object.keys(samples)){const o=el(select,'option',kind);o.value=kind;}
      const title=field(root,'对象名称');const body=field(root,'正文','',true);const metadata=field(root,'关系与属性 JSON',JSON.stringify(samples.Knowledge,null,2),true);
      select.addEventListener('change',()=>{metadata.value=JSON.stringify(samples[select.value],null,2);});
      button(root,'验证并保存',async()=>{await this.plugin.api('/objects',{project:p.oc_id,type:select.value,title:title.value,body:body.value,fields:JSON.parse(metadata.value),token:data.token});modal.close();await this.render();});
    }).open();
  }
  inbox(root,data){
    el(root,'h2','需要你的判断');
    if(!data.inbox.length)el(root,'p','当前没有待决事项。');
    for(const item of data.inbox){
      const box=el(root,'article',undefined,'oc-card');el(box,'h3',item.title);el(box,'p',item.project_title);
      el(box,'strong',item.kind==='approval'?'审查通过 · 等待最终决定':item.kind==='revision'?'已拒绝 · 请修订后重新审查':'证据或质量需要处理');
      this.axes(box,item.gate);this.issues(box,item.gate);
      const actions=el(box,'div',undefined,'oc-actions');
      button(actions,'查看稿件与依据',async()=>{this.selected=item.project;this.artifact=item.artifact;this.tab='inspector';await this.render();});
      const accept=button(actions,'确认定稿',()=>this.decision(item,'accept',data.token),'mod-cta');accept.disabled=item.gate.status!=='PASS';
      button(actions,'退回修改',()=>this.decision(item,'reject',data.token));
      button(actions,'重新检查',async()=>{const detail=await this.plugin.api('/objects/'+item.project);this.startProduction(detail.object,detail,{stage:'critique'});});
    }
  }
  decision(item,decision,token){
    new FormModal(this.plugin,decision==='accept'?'批准当前内容版本':'拒绝并请求修订',(root,modal)=>{
      el(root,'p','此决定绑定正文、来源、主张与 CONTENT.md 的当前版本。后续修改会使批准失效。');
      const reviewer=field(root,'决定人',this.plugin.settings.reviewer);const reason=field(root,'判断理由（至少 8 字）','',true);
      button(root,decision==='accept'?'确认批准':'确认拒绝',async()=>{await this.plugin.api('/decisions',{artifact:item.artifact,decision,reviewer:reviewer.value,reason:reason.value,token});modal.close();await this.render();},'mod-cta');
    }).open();
  }
  axes(root,g){
    const row=el(root,'div',undefined,'oc-axes');for(const axis of AXES){const value=g.axes[axis];const box=el(row,'div',undefined,'oc-axis '+value.status.toLowerCase());el(box,'strong',axis+' · '+value.status);el(box,'p',value.reason);}
  }
  issues(root,g){el(root,'p',g.status==='PASS'?'检查已通过':'还有问题需要处理','oc-gate '+(g.status==='PASS'?'pass':'fail'));if(g.issues.length){const list=el(root,'ul');for(const issue of g.issues)el(list,'li',issue);}}
  async inspector(root,data){
    const p=this.projectSelect(root,data);if(!p)return;
    if(!p.artifacts.length){el(root,'p','还没有稿件，先回到写作继续。');button(root,'继续写作',async()=>{this.tab='project';await this.render();});return;}
    if(!p.artifacts.some(a=>a.oc_id===this.artifact))this.artifact=p.artifacts[0].oc_id;
    const select=el(root,'select');select.setAttribute('aria-label','当前稿件');
    for(const a of p.artifacts){const o=el(select,'option',a.title);o.value=a.oc_id;o.selected=a.oc_id===this.artifact;}
    select.addEventListener('change',async()=>{this.artifact=select.value;await this.render();});
    const detail=await this.plugin.api('/objects/'+this.artifact);const a=detail.object;
    el(root,'h2',a.title);
    // 门禁盾牌与五轴雷达可视化 (Gate & Radar)
    const gateStatus = detail.gate?.status || 'WARN';
    const isApproved = Boolean(detail.gate?.approved);
    const shieldBox = el(root, 'div', undefined, 'oc-gate-shield ' + (gateStatus === 'PASS' ? 'pass' : 'fail'));
    shieldBox.innerHTML = '<span>' + (gateStatus === 'PASS' ? '🛡️ 门禁已通过 (PASS)' : '⚠️ 门禁未通过 / 需修订 (WARN/FAIL)') + '</span>';
    
    // 五轴质量雷达展示卡片 (Five-Axes Radar)
    if (detail.gate?.axes) {
      const radarGrid = el(root, 'div', undefined, 'oc-radar-grid');
      for (const [axisName, axisVal] of Object.entries(detail.gate.axes)) {
        const axCard = el(radarGrid, 'div', undefined, 'oc-radar-card');
        el(axCard, 'div', axisName, 'axis-name');
        const st = (axisVal.status || 'WARN').toLowerCase();
        el(axCard, 'div', axisVal.status || 'WARN', 'axis-val ' + st);
        el(axCard, 'small', axisVal.reason || '', 'oc-muted');
      }
    }

    this.issues(root,detail.gate);

    // 原生排版渲染与交付预览面板 (Typography Panel)
    if (typographyEngine) {
      const typoPanel = el(root, 'section', undefined, 'oc-typography-panel');
      el(typoPanel, 'h3', '🎨 排版渲染与交付预览');
      el(typoPanel, 'p', detail.gate.approved ? '此版本已通过人工定稿，可复制正式富文本交付发布。' : '草稿排版预览。注意：草稿尚未通过人工定稿审查，不得作为正式成品直接发布。', 'oc-muted');

      const picker = el(typoPanel, 'div', undefined, 'oc-theme-picker');
      const currentTheme = this.plugin.settings.typographyTheme || 'serif';
      
      for (const [thId, thObj] of Object.entries(typographyEngine.THEMES)) {
        const btn = el(picker, 'button', thObj.name, 'oc-theme-btn ' + (thId === currentTheme ? 'active' : ''));
        btn.onclick = async () => {
          this.plugin.settings.typographyTheme = thId;
          await this.plugin.saveData(this.plugin.settings);
          await this.render();
        };
      }

      const previewBox = el(typoPanel, 'div', undefined, 'oc-rendered-preview-box');
      const renderedHtml = typographyEngine.renderArticleHtml(a.body || '', currentTheme, a.title || '');
      previewBox.innerHTML = renderedHtml;

      if (detail.gate.approved) {
        button(typoPanel, '📋 复制已批准成品 (富文本)', async () => {
          try {
            const handoffRes = await this.plugin.api('/handoff', {artifact: a.oc_id, token: detail.token});
            const readerMarkdown = handoffRes.article || a.body || '';
            const finalHtml = typographyEngine.renderArticleHtml(readerMarkdown, currentTheme);
            const ok = await typographyEngine.copyRichTextToClipboard(finalHtml, readerMarkdown);
            if (ok) new Notice('✅ 已复制已批准成品富文本到剪贴板，内部 Claim 标记已剔除！');
            else new Notice('⚠️ 剪贴板 API 暂不可用，可直接打开正文复制');
          } catch(err) {
            new Notice('正式交付复制失败: ' + err.message);
          }
        }, 'mod-cta');
      } else {
        button(typoPanel, '📋 复制草稿预览 (未定稿)', async () => {
          try {
            const ok = await typographyEngine.copyRichTextToClipboard(renderedHtml, a.body || '');
            if (ok) new Notice('⚠️ 已复制草稿排版预览。注意：草稿尚未通过人工定稿，非正式成品。');
            else new Notice('⚠️ 剪贴板 API 暂不可用，可直接打开正文复制');
          } catch(err) {
            new Notice('复制失败: ' + err.message);
          }
        });
      }
    }
    const pending=data.inbox.find(i=>i.artifact===a.oc_id);
    if(pending){const accept=button(root,'确认定稿',()=>this.decision(pending,'accept',detail.token),'mod-cta');accept.disabled=detail.gate.status!=='PASS';}
    button(root,'让助手修改',async()=>{this.chatMode='revise';this.tab='project';await this.render();});
    button(root,'重新检查',async()=>{const project=await this.plugin.api('/objects/'+p.oc_id);await this.startProduction(p,project,{stage:'critique'});});
    const checks=el(root,'details');el(checks,'summary','查看检查说明');this.axes(checks,detail.gate);
    button(root,'在编辑器中修订',()=>this.plugin.openNote(a.path));
    button(checks,'手动填写检查结果',()=>this.manualReview(a,detail));
    button(root,'刷新检查',()=>this.render());
    if(detail.gate.approved){
      button(root,'准备公众号草稿',()=>this.prepareDraft(a),'mod-cta');
      button(root,'导出文章',()=>this.handoff(a,detail));
      button(root,'登记微信后台手动发表',()=>this.manualPublication(a,detail));
    }
    el(root,'h3','当前草稿');el(root,'pre',a.body,'oc-prose');
    const diff=el(root,'details');el(diff,'summary','Diff · 与最近审查的草稿比较');
    const reviewed=detail.gate.review?.reviewed_body;
    if(reviewed===undefined)el(diff,'p','尚无已保存的审查快照。');
    else if(reviewed===a.body)el(diff,'p','正文与最近审查一致。资料或政策变化仍会使 Gate 失效。');
    else{el(diff,'h4','审查时');el(diff,'pre',reviewed,'oc-prose');el(diff,'h4','当前');el(diff,'pre',a.body,'oc-prose');}
    const evidence=el(root,'details');el(evidence,'summary','查看引用和原始资料');
    for(const chain of detail.provenance){
      const box=el(evidence,'section',undefined,'oc-card');
      el(box,'strong',chain.claim.title||'Missing Claim');el(box,'p',chain.claim.body);
      el(box,'p',chain.opposes.length?'Contested':chain.supports.length?'Supported':'Unsupported');
      for(const [label,objects] of [['支持证据',chain.supports],['反对证据',chain.opposes],['Derived From · Knowledge',chain.knowledge],['原始材料',chain.materials]]){
        el(box,'h4',label);for(const obj of objects){button(box,obj.title||obj.oc_id,()=>this.plugin.openNote(obj.path),'oc-link');if(obj.quote)el(box,'blockquote',obj.quote);}
      }
      el(box,'p','Used By: '+chain.used_by.join(', '));
    }
    el(root,'h3','Outputs');for(const publication of detail.objects.filter(o=>o.type==='Publication'))button(root,publication.title,()=>this.plugin.openNote(publication.path));
  }
  async sources(root,data){
    const library=await this.plugin.api('/sources');
    el(root,'h2','材料库');el(root,'p','按来源汇总跨项目摘录。原笔记变化会阻止旧版本继续批准或发表；刷新后需重新审查。');
    button(root,'检查来源变化',()=>this.render());
    const filter=field(root,'搜索来源或材料');
    const rows=[];
    const labels={CURRENT:'来源未变',CHANGED:'来源已变',MISSING:'来源缺失',UNTRACKED:'未跟踪原笔记'};
    for(const source of library.sources){
      const card=el(root,'article',undefined,'oc-card');rows.push([card,JSON.stringify(source).toLowerCase()]);
      el(card,'h3',source.source);
      for(const material of source.materials){
        el(card,'p',`${material.project_title} · ${material.title} · ${labels[material.freshness]}`,
          ['CHANGED','MISSING'].includes(material.freshness)?'oc-error':'');
        el(card,'small',`该项目 ${material.artifacts.length} 篇稿件 / ${material.publications.length} 条投递记录需一并核对`);
        button(card,'打开材料',()=>this.plugin.openNote(material.path));
        button(card,'比较并刷新摘录',async()=>{
          const preview=await this.plugin.api('/sources/preview',{material:material.id});
          new FormModal(this.plugin,'核对来源变化',(body,modal)=>{
            el(body,'h3','原摘录');el(body,'pre',preview.material.body,'oc-prose');
            el(body,'h3','原笔记当前正文');el(body,'pre',preview.current_body,'oc-prose');
            const excerpt=field(body,'确认采用的原文摘录',preview.current_body,true);
            el(body,'p','将保存旧版本并更新此摘录；同一来源在其他项目中的摘录需分别确认。');
            button(body,'确认刷新并重新审查',async()=>{await this.plugin.api('/sources/refresh',{material:material.id,body:excerpt.value,source_hash:preview.source_hash,token:preview.token});modal.close();await this.render();},'mod-cta');
          }).open();
        });
        button(card,'复用到项目',()=>{
          new FormModal(this.plugin,'复用现有材料',(body,modal)=>{
            const select=el(body,'select');select.setAttribute('aria-label','复用目标项目');
            for(const p of data.projects){const option=el(select,'option',p.title);option.value=p.oc_id;}
            button(body,'确认复用',async()=>{await this.plugin.api('/sources/reuse',{material:material.id,project:select.value,token:library.token});modal.close();await this.render();});
          }).open();
        });
      }
    }
    filter.addEventListener('input',()=>{for(const [row,text] of rows)row.hidden=!text.includes(filter.value.toLowerCase());});
    if(!rows.length)el(root,'p','捕获当前笔记或选区后，材料会出现在这里。');
  }
  channelForm(existing){
    new FormModal(this.plugin,existing?'更新微信公众号':'连接微信公众号',(root,modal)=>{
      el(root,'p','凭据只提交给本机 Kernel；Windows 使用当前用户 DPAPI 加密保存。请在微信后台确认接口权限及 IP 白名单。不要把 AppSecret 发到对话里。');
      const name=field(root,'账号名称',existing?.name||'');const appid=field(root,'AppID',existing?.appid||'');
      const secret=field(root,'AppSecret');secret.type='password';secret.autocomplete='new-password';
      const env=field(root,'或：AppSecret 环境变量名称');
      el(root,'p','个人未认证公众号：先用 API 送入草稿箱，最后在微信后台发表。获取令牌不代表具有草稿或发表权限。');
      const mode=el(root,'select');mode.setAttribute('aria-label','公众号投递模式');
      for(const [value,text] of [['draft_only','仅送入草稿箱；后台人工发表（默认）'],['draft_and_publish','草稿及 API 发表（已确认具备发表权限）']]){
        const option=el(mode,'option',text);option.value=value;option.selected=(existing?.publish_mode||'draft_only')===value;
      }
      button(root,'在本地保存账号',async()=>{await this.plugin.api('/channels',{name:name.value,appid:appid.value,secret:secret.value,secret_env:env.value,channel_id:existing?.id,publish_mode:mode.value});secret.value='';modal.close();await this.render();},'mod-cta');
    }).open();
  }
  async prepareDraft(a){
    const data=await this.plugin.api('/publications');
    if(!data.channels.length){this.channelForm();return;}
    new FormModal(this.plugin,'准备公众号草稿',(root,modal)=>{
      const select=el(root,'select');select.setAttribute('aria-label','公众号账号');
      for(const c of data.channels){const opt=el(select,'option',`${c.name} · ${c.appid}`);opt.value=c.id;}
      const title=field(root,'公众号标题（32 字）',a.title);const author=field(root,'作者（16 字）');
      const summary=field(root,'摘要（120 字）','',true);const cover=field(root,'封面 thumb_media_id');
      const files=this.app.vault.getFiles().filter(f=>['png','jpg','jpeg'].includes(f.extension.toLowerCase()));
      if(files.length){
        const imageSelect=el(root,'select');imageSelect.setAttribute('aria-label','Vault 封面图片');
        for(const f of files){const opt=el(imageSelect,'option',f.path);opt.value=f.path;}
        button(root,'确认上传所选封面到此账号',async()=>{
          const result=await this.plugin.api('/channels/cover',{channel:select.value,path:imageSelect.value});cover.value=result.media_id;
          new Notice('封面已上传，素材回执已保存在本地。');
        });
      }
      el(root,'p','封面需属于此账号。此处准备单篇图文；正文图片暂需在微信后台处理。下一步先预览，确认后才送入草稿箱。');
      button(root,'生成投递预览',async()=>{
        const preview=await this.plugin.api('/publications/prepare',{artifact:a.oc_id,channel:select.value,action:'draft',token:data.token,
          options:{title:title.value,author:author.value,digest:summary.value,thumb_media_id:cover.value}});
        modal.close();this.tab='publishing';await this.render();this.publicationPreview(preview);
      },'mod-cta');
    }).open();
  }
  publicationPreview(pub){
    new FormModal(this.plugin,pub.action==='draft'?'确认送入微信草稿箱':'确认向公众发表',(root,modal)=>{
      el(root,'p',`账号：${pub.destination.appid} · ${pub.payload.title}`);
      el(root,'p',`作者：${pub.payload.author||'未填写'} · 封面：${pub.payload.thumb_media_id}`);
      el(root,'p','摘要：'+pub.payload.digest);
      el(root,'p',pub.action==='draft'?'本次会在微信账号中创建草稿。':'本次会调用微信发表接口。请先在微信后台核对排版及封面；这不是群发操作。',pub.action==='publish'?'oc-error':'');
      const frame=el(root,'iframe');frame.title='公众号正文预览';frame.className='oc-publish-preview';frame.setAttribute('sandbox','');
      frame.srcdoc='<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'"><style>body{font:16px/1.8 sans-serif;padding:16px;overflow-wrap:anywhere}table{border-collapse:collapse}td,th{border:1px solid #bbb;padding:6px}</style>'+pub.payload.content;
      const reviewer=field(root,'本次投递确认人',this.plugin.settings.reviewer);
      const label=el(root,'label');const agree=el(label,'input');agree.type='checkbox';el(label,'span','我已核对账号、标题、正文、摘要及封面，确认执行本次操作');
      button(root,pub.action==='draft'?'确认送入草稿箱':'确认发表',async()=>{
        if(!agree.checked)throw new Error('请先勾选并核对本次操作');
        const result=await this.plugin.api('/publications/confirm',{publication:pub.oc_id,confirmation:pub.preview_hash,reviewer:reviewer.value,token:pub.token});
        modal.close();this.tab='publishing';await this.render();new Notice('投递状态：'+this.deliveryLabel(result.delivery_status));
      },'mod-cta');
    }).open();
  }
  deliveryLabel(status){return ({PREPARED:'待确认',SENDING:'提交中 / 中断后需核验',UNKNOWN:'结果未知，禁止重复提交',REMOTE_DRAFT:'微信草稿已核验',SUBMITTED:'已受理，尚未发表',PUBLISHED:'已发表并核验',FAILED:'失败',CONFLICT:'远端内容不一致',CANCELLED:'预览已取消',WITHDRAWN:'已删除或封禁'})[status]||'手动登记（未经 API 核验）';}
  async publishing(root,data){
    const outbox=await this.plugin.api('/publications');el(root,'h2','微信公众号 · 发布与反馈');
    if(outbox.channels.some(c=>c.kind==='test'))el(root,'p','软件验收模式：使用模拟微信协议，下面的回执不代表真实公众号发表。','oc-error');
    button(root,'添加公众号',()=>this.channelForm());button(root,'刷新本地回执',()=>this.render());
    el(root,'p','默认送入微信草稿箱，核对后由本人在微信后台发表并登记链接。已确认具备发表权限的账号可单独启用 API 发表。菜单未显示某项不等于该接口必定不可调用，实际权限以微信响应为准。');
    for(const c of outbox.channels){
      const row=el(root,'div',undefined,'oc-card');el(row,'strong',`${c.name} · ${c.appid}`);
      el(row,'p',c.publish_mode==='draft_and_publish'?'已启用 API 发表；仍需微信实际授权':'仅送草稿箱 → 微信后台人工发表');
      button(row,'检查令牌连接',async()=>{const r=await this.plugin.api('/channels/check',{channel:c.id});new Notice(r.note,10000);});
      button(row,'更新账号配置',()=>this.channelForm(c));
    }
    const ready=data.projects.flatMap(p=>p.artifacts.filter(a=>a.gate.approved&&!outbox.publications.some(r=>r.artifact===a.oc_id&&r.current_approval&&['REMOTE_DRAFT','PUBLISHED'].includes(r.delivery_status))));
    for(const a of ready)button(root,'准备草稿：'+a.title,()=>this.prepareDraft(a));
    if(!ready.length)el(root,'p','当前没有已批准稿件。完成审查与用户批准后即可准备草稿。');
    for(const pub of outbox.publications){
      const apiPublish=outbox.channels.find(c=>c.id===pub.channel)?.publish_mode==='draft_and_publish';
      const card=el(root,'article',undefined,'oc-card');el(card,'h3',pub.title);
      el(card,'p',this.deliveryLabel(pub.delivery_status));
      if(!pub.current_approval)el(card,'p','对应内容版本已过期；历史回执保留，新投递须重新审查。','oc-error');
      if(pub.last_error)el(card,'p',pub.last_error,'oc-error');
      if(pub.url){const a=el(card,'a','打开文章');a.href=pub.url;a.rel='noopener noreferrer';a.target='_blank';}
      button(card,'打开回执与历史',()=>this.plugin.openNote(pub.path));
      if(pub.delivery_status==='PREPARED'){
        button(card,'核对并确认',()=>this.publicationPreview({...pub,token:outbox.token}));
        button(card,'取消未提交预览',async()=>{await this.plugin.api('/publications/cancel',{publication:pub.oc_id,token:outbox.token});await this.render();});
      }else if(pub.channel&&pub.delivery_status!=='CANCELLED'){
        button(card,'只读查询微信回执',async()=>{await this.plugin.api('/publications/reconcile',{publication:pub.oc_id});await this.render();});
        if(['SENDING','UNKNOWN'].includes(pub.delivery_status))button(card,'使用后台 ID 恢复',()=>{
          new FormModal(this.plugin,'只读恢复投递结果',(body,modal)=>{
            el(body,'p','仅在提交响应丢失时使用。提供本次草稿的 media_id 或发表任务 publish_id；核验内容匹配后才能绑定，不能借此重新提交。');
            const id=field(body,pub.action==='draft'?'media_id':'publish_id');
            button(body,'核验并恢复回执',async()=>{await this.plugin.api('/publications/reconcile',{publication:pub.oc_id,recovery_id:id.value});modal.close();await this.render();});
          }).open();
        });
      }
      if(pub.submitted_publication)el(card,'p','此草稿已有发表记录，请查询对应发表回执。');
      if(pub.delivery_status==='REMOTE_DRAFT'&&pub.current_approval&&!apiPublish){
        el(card,'p','下一步：在微信后台核对排版并发表，然后登记文章链接。此账号不会调用 freepublish/submit。');
        button(card,'登记后台发表结果',async()=>{const detail=await this.plugin.api('/objects/'+pub.artifact);this.manualPublication(detail.object,detail);});
      }
      if(pub.delivery_status==='REMOTE_DRAFT'&&pub.current_approval&&apiPublish&&!pub.submitted_publication)button(card,'核对草稿并准备发表',async()=>{
        const preview=await this.plugin.api('/publications/prepare',{artifact:pub.artifact,channel:pub.channel,action:'publish',draft_publication:pub.oc_id,token:outbox.token});
        await this.render();this.publicationPreview(preview);
      },'mod-cta');
      if(pub.delivery_status==='PUBLISHED'||!pub.delivery_status)button(card,'记录读者反馈 / 数据观察',()=>this.feedbackForm(pub,outbox.token));
      for(const item of pub.feedback||[]){
        const row=el(card,'div',undefined,'oc-lesson');el(row,'p',`${item.source} · ${item.observation}`);el(row,'p','建议：'+item.suggestion);el(row,'small','判断：'+item.decision);
        if(item.decision==='PENDING')button(row,'判断这条经验',()=>this.lessonDecision(pub,item,outbox.token));
        if(item.decision==='accept')button(row,'带入下一个项目',()=>{
          new FormModal(this.plugin,'用已确认经验创建项目',(body,modal)=>{
            const title=field(body,'项目名称');const goal=field(body,'项目目标','',true);const audience=field(body,'目标读者');
            button(body,'创建并打开',async()=>{const r=await this.plugin.api('/feedback/project',{publication:pub.oc_id,feedback:item.id,title:title.value,goal:goal.value,audience:audience.value,token:outbox.token});this.selected=r.object.oc_id;this.tab='project';modal.close();await this.render();});
          }).open();
        });
      }
    }
  }
  feedbackForm(pub,token){
    new FormModal(this.plugin,'记录这次发表的反馈',(root,modal)=>{
      el(root,'p','填写具体来源与观察，可来自微信后台阅读数据、留言或访谈。暂不自动抓取后台统计。');
      const source=field(root,'反馈来源 / 数据日期');const body=field(root,'观察到的事实','',true);const suggestion=field(root,'建议下次如何改进','',true);
      button(root,'保存待判断反馈',async()=>{await this.plugin.api('/feedback',{publication:pub.oc_id,source:source.value,body:body.value,suggestion:suggestion.value,token});modal.close();await this.render();});
    }).open();
  }
  lessonDecision(pub,item,token){
    new FormModal(this.plugin,'确认可复用的经验',(root,modal)=>{
      el(root,'p',item.suggestion);const reviewer=field(root,'经验判断人',this.plugin.settings.reviewer);const reason=field(root,'接受或拒绝的依据','',true);
      for(const decision of ['accept','reject'])button(root,decision==='accept'?'接受经验':'拒绝经验',async()=>{
        await this.plugin.api('/feedback/decide',{publication:pub.oc_id,feedback:item.id,decision,reviewer:reviewer.value,reason:reason.value,token});modal.close();await this.render();
      });
    }).open();
  }

  manualPublication(a,detail){
    new FormModal(this.plugin,'登记已在微信后台发表的文章',(root,modal)=>{
      el(root,'p','适用于账号无发表接口权限，或在微信后台手动排版的交接。此记录标为人工登记，不会伪装成 API 核验。请先确认微信正文与当前批准稿一致。');
      const url=field(root,'微信文章链接');const date=field(root,'发表时间（ISO）',new Date().toISOString());
      const by=field(root,'登记人',this.plugin.settings.reviewer);const note=field(root,'版本核对与交接说明','',true);
      const label=el(root,'label');const agree=el(label,'input');agree.type='checkbox';el(label,'span','我已核对该链接的正文与当前批准稿一致');
      button(root,'保存人工发表记录',async()=>{
        if(!agree.checked||!by.value.trim()||!note.value.trim())throw new Error('请完成版本核对、署名及说明');
        const parsed=new URL(url.value);if(parsed.protocol!=='https:'||parsed.hostname!=='mp.weixin.qq.com'||parsed.username||parsed.password)throw new Error('请输入微信文章 HTTPS 链接');
        await this.plugin.api('/objects',{project:a.project,type:'Publication',title:'人工微信发表 · '+a.title,body:by.value+'：'+note.value,
          fields:{artifact:a.oc_id,url:url.value,published_at:date.value},token:detail.token});
        modal.close();this.tab='publishing';await this.render();
      });
    }).open();
  }
  handoff(a,detail){
    new FormModal(this.plugin,'交付已批准版本',(root,modal)=>{
      el(root,'p','生成供读者阅读的 Markdown：移除内部主张标记，不自动附加来源脚注。溯源与审查记录保留在本地，正文中主动写入的链接和引用保留。');
      el(root,'p','可用 Ailu 或其他 Markdown 工具打开。这里只创建本地文件，不调用 Ailu 私有 API、不上传、不标记已发布。Ailu 当前 Windows 版本的可写功能仍受其自身支持范围限制。','oc-muted');
      button(root,'生成并打开交付稿',async()=>{
        const result=await this.plugin.api('/handoff',{artifact:a.oc_id,token:detail.token});
        modal.close();await this.plugin.openNote(result.path);new Notice('已生成本地交付稿；项目仍保留原批准状态。');
      },'mod-cta');
    }).open();
  }
  manualReview(a,detail){
    new FormModal(this.plugin,'五轴审查（人工）',(root,modal)=>{
      const reviewer=field(root,'审查人',this.plugin.settings.reviewer);const fields={};
      for(const axis of AXES){const row=el(root,'div');el(row,'h4',axis);const status=el(row,'select');status.setAttribute('aria-label',axis+' status');for(const name of ['WARN','PASS','FAIL']){const o=el(status,'option',name);o.value=name;}fields[axis]={status,reason:field(row,axis+' 依据','',true)};}
      const conflict=field(root,'反对证据处理','',true);const summary=field(root,'审查结论','',true);
      const label=el(root,'label');const complete=el(label,'input');complete.type='checkbox';el(label,'span','我已检查重要事实均登记为 Claim');
      button(root,'保存 Review',async()=>{const axes={};for(const [axis,f]of Object.entries(fields))axes[axis]={status:f.status.value,reason:f.reason.value};await this.plugin.api('/reviews',{artifact:a.oc_id,reviewer:reviewer.value,axes,claims_complete:complete.checked,conflict_resolution:conflict.value,summary:summary.value,token:detail.token});modal.close();await this.render();});
    }).open();
  }
  jobs(root,data){
    if(!data.jobs.length)return;
    const section=el(root,'details',undefined,'oc-jobs');el(section,'summary','运行记录 · '+data.jobs.length);
    for(const job of data.jobs.slice(0,12)){
      const row=el(section,'div',undefined,'oc-card');el(row,'p',`${job.status} · ${job.detail.stage||job.detail.outcome||'production'} · ${job.id.slice(0,8)}`);
      if(job.detail.error)el(row,'pre',job.detail.error,'oc-error');
      if(job.detail.kind==='ideation'){button(row,'查看综合选题',()=>this.discoverIdeas(job.id));continue;}
      if(['RUNNING','QUEUED'].includes(job.status))button(row,'取消任务',async()=>{await this.plugin.api('/cancel',{id:job.id});await this.render();});
      if(['FAILED','CANCELLED','INTERRUPTED'].includes(job.status))button(row,'从当前 Vault 继续',async()=>{if(job.detail.instruction){this.selected=job.project;this.tab='conversation';this.composers||={};this.composers[job.project]=job.detail.instruction;await this.render();return;}const detail=await this.plugin.api('/objects/'+job.project);this.startProduction(detail.object,detail,{resume:job.id,stage:job.detail.stage==='critique'?'critique':undefined});});
    }
  }
  async conversation(root,data,selectedProject){
    const p=selectedProject||this.projectSelect(root,data);if(!p){el(root,'p','说说你想写什么，就能开始。');button(root,'开始写作',()=>this.newProject());return;}
    const [history,providers]=await Promise.all([this.plugin.api('/conversation/history',{project:p.oc_id}),this.plugin.api('/providers')]);
    const panel=el(root,'details',undefined,'oc-tools');el(panel,'summary','写作助手 · '+(Object.keys(providers.active).join(' / ')||'未连接'));
    el(panel,'p','沿用本地工具的模型设置。只带入这篇文章的资料、稿件、规则和最近 12 轮对话。');
    for(const candidate of providers.available){el(panel,'p',candidate.name+' · '+candidate.path);if(!providers.active[candidate.name])button(panel,'启用 '+candidate.name,async()=>{await this.plugin.api('/providers/activate',{name:candidate.name});await this.render();});}
    const provider=el(panel,'select');provider.setAttribute('aria-label','执行 CLI');
    for(const [name,caps] of Object.entries(providers.active)){const option=el(provider,'option',name);option.value=name;option.selected=name===this.chatProvider;el(panel,'p',`${name}：保留项目历史；${caps.image_generation===false?'当前适配器仅支持配图方案': '实际生图取决于 CLI 已配置的图像工具'}`);}
    provider.addEventListener('change',()=>{this.chatProvider=provider.value;});
    if(!Object.keys(providers.active).length)el(root,'p',providers.notice||'还没有可用的写作助手。展开“写作助手”检查连接。','oc-error');
    const composer=el(root,'section',undefined,'oc-composer');
    const transcript=el(root,'div',undefined,'oc-conversation');
    for(const turn of history.turns){
      const card=el(transcript,'article',undefined,'oc-card');el(card,'small',({RUNNING:'正在思考',SUCCEEDED:'已完成',INTERRUPTED:'上次未完成'})[turn.status]||'未完成');
      el(card,'h3','你的指令');el(card,'p',turn.instruction,'oc-prose');el(card,'h3','助手');el(card,'p',turn.reply||'正在运行本地 CLI…','oc-prose');
      const receipt=el(card,'details');el(receipt,'summary','本次记录');button(receipt,'打开记录',()=>this.plugin.openNote(`OpenContent-Workspace/${p.oc_id}/${turn.id}.md`));
      if(turn.revision){const r=turn.revision;const diff=el(card,'details');el(diff,'summary',turn.applied?'已应用的改稿':'核对改稿提案');
        const old=data.projects.find(x=>x.oc_id===p.oc_id)?.artifacts.find(x=>x.oc_id===r.artifact);
        el(diff,'h4','当前正文');el(diff,'pre',old?.body||'请打开稿件核对原文','oc-prose');el(diff,'h4',r.title);el(diff,'pre',r.body,'oc-prose');
        if(!turn.applied)button(diff,'采用并检查',async()=>{
          await this.plugin.api('/conversation/apply',{project:p.oc_id,turn:turn.id,token:history.token});
          try{const latest=await this.plugin.api('/objects/'+p.oc_id);await this.startProduction(p,latest,{stage:'critique'});}
          catch(e){await this.render();new Notice('改稿已保存，检查尚未开始：'+e.message+'。可点击“重新检查”继续。');}
        });
        else button(diff,'重新审查这篇稿件',async()=>{const detail=await this.plugin.api('/objects/'+p.oc_id);this.startProduction(detail.object,detail,{stage:'critique'});});}
      for(const brief of turn.illustrations||[]){const b=el(card,'details');el(b,'summary','配图方案 · '+brief.placement);el(b,'pre',brief.prompt,'oc-prose');button(b,'复制配图指令',()=>navigator.clipboard.writeText(brief.prompt));}
      if(turn.image_status==='BRIEF_ONLY')el(card,'p','本轮仅完成配图方案，没有生成图片。','oc-muted');
      for(const asset of turn.images||[]){const file=this.app.vault.getAbstractFileByPath(asset.path);if(file){const img=el(card,'img');img.src=this.app.vault.getResourcePath(file);img.alt=asset.alt;img.className='oc-generated-image';}
        el(card,'p',asset.placement+' · '+asset.path);button(card,'复制图片 Markdown',()=>navigator.clipboard.writeText(`![${asset.alt.replace(/[\[\]]/g,'')}](${asset.path})`));}
    }
    const mode=el(composer,'select');mode.setAttribute('aria-label','想做什么');
    const modeValue=!p.artifacts.length&&this.chatMode==='revise'?'discuss':this.chatMode||'discuss';
    for(const [id,label] of [['discuss','聊想法'],['revise','改文章'],['illustrate','配张图']]){const o=el(mode,'option',label);o.value=id;o.selected=id===modeValue;o.disabled=id==='revise'&&!p.artifacts.length;}
    mode.addEventListener('change',()=>{this.chatMode=mode.value;});
    this.composers||={};
    const input=field(composer,'给这个项目的指令',this.composers[p.oc_id]||'',true);input.placeholder='说说你想怎么写、哪里需要改…';input.maxLength=8000;
    const running=data.jobs.find(j=>j.project===p.oc_id&&['RUNNING','QUEUED'].includes(j.status));
    const send=button(composer,running?'停止生成':'发送',async()=>{
      if(running){await this.plugin.api('/cancel',{id:running.id});await this.render();return;}
      if(!input.value.trim())return;
      await this.plugin.api('/conversation/send',{project:p.oc_id,instruction:input.value,mode:mode.value,provider:provider.value||undefined,token:history.token});
      this.composers[p.oc_id]='';this.chatProvider=provider.value;this.chatMode=mode.value;this.plugin.jobsActive=true;await this.render();
    },'mod-cta');
    const sync=()=>{send.disabled=!running&&(!input.value.trim()||!Object.keys(providers.active).length);};sync();
    input.addEventListener('input',()=>{this.composers[p.oc_id]=input.value;sync();});
    input.addEventListener('keydown',event=>{if(event.key==='Enter'&&(event.ctrlKey||event.metaKey)&&!event.isComposing&&!running){event.preventDefault();if(!send.disabled)send.click();}});
    el(composer,'small','Ctrl / ⌘ + Enter 发送。修改会先给你看，采用后才写入。','oc-muted');
    if(running)el(composer,'p','正在处理，可以停止；已保存的内容会保留。','oc-muted');
    el(panel,'p','配图使用本地工具已有的图像能力；没有能力时只返回方案。图片可复制到正文中。');
  }
}

class Settings extends PluginSettingTab{
  constructor(app,plugin){super(app,plugin);this.plugin=plugin;}
  display(){const root=this.containerEl;root.empty();el(root,'h2','OpenContent · 本地 Kernel');
    for(const [key,title,desc]of [['kernelPath','项目目录','包含 opencontent/ 与 templates/ 的目录'],['python','Python 可执行文件','Python 3.12+，需安装 requirements.txt'],['codex','Codex 原生可执行文件','可留空；无 Agent 时核心仍可用'],['skillRoots','Skill 发现路径','每行一个目录或 SKILL.md；仅把主动选择的技能提供给 Agent'],['reviewer','默认决定人','本地署名；不是团队身份认证']]){
      new Setting(root).setName(title).setDesc(desc).addText(t=>t.setValue(this.plugin.settings[key]).onChange(async v=>{this.plugin.settings[key]=v;await this.plugin.saveData(this.plugin.settings);}));
    }
        // 从本地 Codex / Claude 智能发现的大模型下拉选择菜单
    const modelSetting = new Setting(root)
      .setName('选择大模型 (AI Model Selection)')
      .setDesc('自动检测本地 Codex / Claude 账户拥有的全部大模型列表。');

    (async () => {
      let modelsList = [];
      try {
        if (this.plugin.connection) {
          const res = await this.plugin.api('/models');
          modelsList = res.models || [];
        }
      } catch(e) {}

      if (!modelsList.length) {
        // Fallback common models
        modelsList = [
          { id: '', name: '⚡ 使用系统默认模型 (System Default)' },
          { id: 'gpt-5.3-codex-spark', name: 'gpt-5.3-codex-spark (极速)' },
          { id: 'gpt-5.6-sol', name: 'gpt-5.6-sol (旗舰高智)' },
          { id: 'gpt-5.6-terra', name: 'gpt-5.6-terra (平衡)' },
          { id: 'gpt-5.6-luna', name: 'gpt-5.6-luna' },
          { id: 'gpt-5.4-mini', name: 'gpt-5.4-mini' },
          { id: 'claude-3-7-sonnet-latest', name: 'Claude 3.7 Sonnet' },
          { id: 'claude-3-5-sonnet-latest', name: 'Claude 3.5 Sonnet' },
          { id: 'o3-mini', name: 'o3-mini' }
        ];
      } else {
        modelsList.unshift({ id: '', name: '⚡ 使用系统默认模型 (System Default)' });
      }

      modelSetting.addDropdown(dd => {
        for (const m of modelsList) {
          dd.addOption(m.id, m.name || m.id);
        }
        dd.setValue(this.plugin.settings.preferredModel || '');
        dd.onChange(async v => {
          this.plugin.settings.preferredModel = v;
          await this.plugin.saveData(this.plugin.settings);
          if (this.plugin.connection) {
            try {
              const providers = await this.plugin.api('/providers');
              const activeName = Object.keys(providers.active)[0];
              if (activeName) {
                await this.plugin.api('/providers/activate', { name: activeName, model: v });
                new Notice('已将模型切换为: ' + (v || '系统默认'));
              }
            } catch(e) {}
          }
        });
      });
    })();

    new Setting(root).setName('检查本地环境').setDesc('离线检查 Python、依赖、内核和目录权限；不读取笔记和密钥。').addButton(b=>b.setButtonText('开始检查').onClick(()=>this.plugin.checkEnvironment()));
    new Setting(root).setName('启动 Kernel').setDesc('后台进程运行任务，不阻塞 Obsidian 编辑。').addButton(b=>b.setButtonText('启动 / 连接').onClick(async()=>{try{await this.plugin.startKernel();new Notice('OpenContent Kernel 已连接');}catch(e){new Notice(e.message);}}));
  }
}

module.exports=class OpenContentPlugin extends Plugin{
  async onload(){
    this.settings=Object.assign({},DEFAULTS,await this.loadData());
    this.registerView(VIEW,leaf=>new Cockpit(leaf,this));
    this.app.workspace.onLayoutReady(()=>{if(!this.unloading)this.open().catch(e=>new Notice(e.message,10000));});
    this.addRibbonIcon('workflow','OpenContent',()=>this.open());
    for(const [id,name,tab]of [['board','Production Board','board'],['inbox','Judgment Inbox','inbox'],['project','Project View','project'],['inspector','Content Inspector','inspector']])this.addCommand({id:'open-'+id,name,callback:()=>this.open(tab)});
    this.addCommand({id:'open-sources',name:'材料库',callback:()=>this.open('sources')});
    this.addCommand({id:'open-publishing',name:'发布与反馈',callback:()=>this.open('publishing')});
    this.addCommand({id:'open-conversation',name:'项目指令台：讨论、改稿与配图',callback:()=>this.open('conversation')});
    this.addCommand({id:'discover-projects',name:'从仓库发现新选题',callback:async()=>{await this.open('board');this.app.workspace.getLeavesOfType(VIEW)[0].view.discoverIdeas();}});
    this.addSettingTab(new Settings(this.app,this));
    this.addCommand({id:'capture-note',name:'捕获当前笔记 / 选区',editorCallback:(editor,view)=>this.captureNote(view.file,editor.getSelection())});
    this.addCommand({id:'continue-project',name:'继续上次内容项目',callback:()=>this.open('project')});
    this.addCommand({id:'configure',name:'配置连接',callback:()=>this.configure()});
    this.addCommand({id:'doctor',name:'检查本地环境',callback:()=>this.checkEnvironment()});
    this.registerEvent(this.app.workspace.on('editor-menu',(menu,editor,view)=>{
      if(view.file)menu.addItem(item=>item.setTitle(editor.getSelection().trim()?'OpenContent：捕获选区为材料':'OpenContent：捕获笔记为材料').setIcon('quote').onClick(()=>this.captureNote(view.file,editor.getSelection())));
    }));
    this.registerEvent(this.app.workspace.on('file-menu',(menu,file)=>{
      if(file.extension==='md')menu.addItem(item=>item.setTitle('OpenContent：捕获为项目材料').setIcon('workflow').onClick(()=>this.captureNote(file)));
    }));
    this.registerEvent(this.app.workspace.on('file-open',file=>{
      if(file?.extension==='md'&&!file.path.startsWith('OpenContent/'))this.lastNote=file;
      for(const leaf of this.app.workspace.getLeavesOfType(VIEW))if(leaf.view.tab==='board')leaf.view.render().catch(e=>new Notice(e.message));
      if(!file||!file.path.startsWith('OpenContent/Artifact/'))return;
      for(const leaf of this.app.workspace.getLeavesOfType(VIEW)){leaf.view.artifact=file.basename;}
    }));
    this.refreshNeeded=true;
    const invalidate=file=>{if(file?.path?.endsWith('.md'))this.refreshNeeded=true;};
    for(const event of ['create','modify','delete'])this.registerEvent(this.app.vault.on(event,invalidate));
    this.registerEvent(this.app.vault.on('rename',(file,oldPath)=>{invalidate(file);invalidate({path:oldPath});}));
    this.registerInterval(window.setInterval(async()=>{
      const leaves=this.app.workspace.getLeavesOfType(VIEW);
      if(!this.connection||this.polling||!leaves.length||(!this.refreshNeeded&&!this.jobsActive))return;
      this.polling=true;this.refreshNeeded=false;
      try{const data=await this.api('/board');this.jobsActive=data.jobs.some(j=>['RUNNING','QUEUED'].includes(j.status));const signature=JSON.stringify([data.token,data.jobs.map(j=>[j.id,j.status,j.updated])]);if(this.signature!==signature){for(const leaf of leaves)await leaf.view.render();}this.signature=signature;}catch(e){this.refreshNeeded=true;}finally{this.polling=false;}
    },2000));
  }
  async remember(project,artifact){
    if(this.settings.lastProject===project&&this.settings.lastArtifact===artifact)return;
    this.settings.lastProject=project||'';this.settings.lastArtifact=artifact||'';
    await this.saveData(this.settings);
  }
  configure(){
    new FormModal(this,'连接你的本地工作环境',(root,modal)=>{
      el(root,'p','内容始终保存在 Vault。Python Kernel 负责状态与审查；Codex 可选，捕获材料不调用模型。');
      const directory=field(root,'OpenContent 项目目录',this.settings.kernelPath);
      const python=field(root,'Python 可执行文件',this.settings.python);
      const codex=field(root,'Codex 原生可执行文件（可选）',this.settings.codex);
      el(root, 'label', '选择使用的大模型');
      const modelSelect = el(root, 'select');
      modelSelect.setAttribute('aria-label', '选择大模型');
      const defOpt = el(modelSelect, 'option', '⚡ 使用系统默认模型 (System Default)');
      defOpt.value = '';

      (async () => {
        try {
          if (this.connection) {
            const res = await this.api('/models');
            for (const m of (res.models || [])) {
              const opt = el(modelSelect, 'option', m.name || m.id);
              opt.value = m.id;
              if (m.id === this.settings.preferredModel) opt.selected = true;
            }
          }
        } catch(e) {}
      })();
      el(root,'p','需要 Python 3.12+、PyYAML 6.0.3 和 Mistune 3.2.0。留空项目目录时使用插件附带内核；依赖清单位于插件 kernel/requirements.txt。AI 工具需先登录。','oc-muted');
      button(root,'检查当前填写的环境',()=>this.checkEnvironment({kernelPath:directory.value.trim(),python:python.value.trim(),codex:codex.value.trim()}));
      button(root,'保存并检查连接',async()=>{
        const newKernel = directory.value.trim();
        const newPython = python.value.trim();
        const newCodex = codex.value.trim();
        const newModel = modelSelect.value;
        const kernelChanged = newKernel !== this.settings.kernelPath || newPython !== this.settings.python || newCodex !== this.settings.codex;

        Object.assign(this.settings, {
          kernelPath: newKernel,
          python: newPython,
          codex: newCodex,
          preferredModel: newModel
        });
        await this.saveData(this.settings);

        if (this.connection) {
          // If only model or non-kernel settings changed, hot-apply directly
          if (!kernelChanged) {
            try {
              const providers = await this.api('/providers');
              const activeName = Object.keys(providers.active)[0];
              if (activeName) {
                await this.api('/providers/activate', { name: activeName, model: newModel });
              }
              modal.close();
              new Notice('已应用设置！当前模型: ' + (newModel || '系统默认'));
              await this.open();
              return;
            } catch(e) {}
          }
          // If kernel path or python changed, perform graceful hot restart
          try {
            await this.api('/shutdown', {});
          } catch(e) {}
          this.connection = null;
          if (this.child) {
            try { this.child.kill(); } catch(e) {}
            this.child = null;
          }
          await new Promise(r => setTimeout(r, 600));
        }

        await this.startKernel();
        const health = await this.api('/health');
        const activeName = Object.keys(health.providers)[0];
        if (activeName && this.settings.preferredModel) {
          try { await this.api('/providers/activate', { name: activeName, model: this.settings.preferredModel }); } catch(e) {}
        }
        modal.close();
        new Notice(Object.keys(health.providers).length ? '已连接，当前模型: ' + (this.settings.preferredModel || '系统默认') : '连接正常，可无 AI 管理材料与审查。');
        await this.open();
      },'mod-cta');
    }).open();
  }
  async captureNote(file,selection=''){
    try{
      file=file||this.lastNote;
      if(!file||file.extension!=='md')throw new Error('先打开一篇 Markdown 笔记，或在文件菜单中选择捕获。');
      if(!this.connection)await this.startKernel();
      const selected=Boolean(selection?.trim());
      const body=selected?selection:(await this.app.vault.read(file)).replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/,'').trim();
      const board=await this.api('/board');
      const frontmatter=this.app.metadataCache.getFileCache(file)?.frontmatter;
      const sourceUrl=typeof frontmatter?.source==='string'&&/^https?:\/\//.test(frontmatter.source)?frontmatter.source:undefined;
      new FormModal(this,selected?'捕获当前选区':'捕获当前笔记',(root,modal)=>{
        el(root,'p',`${file.path} · ${selected?'仅选区':'正文（省略笔记属性）'} · ${body.length} 字符。捕获不会调用 Agent，也不会改写原笔记。`);
        const choice=el(root,'select');choice.setAttribute('aria-label','目标项目');
        const fresh=el(choice,'option','新建内容项目');fresh.value='';
        for(const p of board.projects){const option=el(choice,'option',p.title);option.value=p.oc_id;option.selected=p.oc_id===this.settings.lastProject;}
        const projectFields=el(root,'div');
        const title=field(projectFields,'新项目名称',file.basename+' · 内容项目');
        const goal=field(projectFields,'写作目标','将这份材料转化为一篇有出处、说明边界并提供具体建议的文章。',true);
        const audience=field(projectFields,'目标读者','对这个主题有实际需求的读者');
        const toggle=()=>{projectFields.hidden=Boolean(choice.value);};choice.addEventListener('change',toggle);toggle();
        const excerpt=field(root,'要捕获的内容',body,true);let created=null;
        button(root,'保存到项目',async()=>{
          if(!excerpt.value.trim())throw new Error('捕获内容不能为空。');
          const pid=choice.value||created||(created=(await this.api('/projects',{title:title.value,goal:goal.value,audience:audience.value})).oc_id);
          const current=await this.api('/board');
          const result=await this.api('/capture',{project:pid,title:file.basename+(selected?' · 选区':''),body:excerpt.value,source:'vault:'+file.path,source_url:sourceUrl,token:current.token});
          await this.remember(pid,null);modal.close();new Notice(result.duplicate?'这段材料已在项目中，没有重复添加。':'材料已保存，可以稍后继续写作。');
          await this.open('project');const view=this.app.workspace.getLeavesOfType(VIEW)[0].view;view.selected=pid;await view.render();
        },'mod-cta');
      }).open();
    }catch(e){new Notice(e.message,10000);}
  }
  async open(tab='board'){
    // Serialize ribbon, command and layout-ready opens so only one sidebar leaf is created.
    this.opening=(this.opening||Promise.resolve()).catch(()=>{}).then(()=>this.openInSidebar(tab));
    return this.opening;
  }
  async openInSidebar(tab){
    if(this.unloading)return;
    const workspace=this.app.workspace;
    const existing=workspace.getLeavesOfType(VIEW);
    let leaf=existing.find(item=>item.getRoot()===workspace.rightSplit);
    const previous=existing[0]?.view;
    if(!leaf){
      leaf=workspace.getRightLeaf(false);
      if(!leaf)throw new Error('无法创建右侧栏面板，请检查工作区布局。');
      await leaf.setViewState({type:VIEW,active:true});
    }
    await leaf.loadIfDeferred();
    if(this.unloading){leaf.detach();return;}
    if(previous&&previous!==leaf.view){
      leaf.view.selected=previous.selected||this.settings.lastProject;
      leaf.view.artifact=previous.artifact||this.settings.lastArtifact;
      leaf.view.composers=previous.composers||{};
    }
    leaf.view.tab=tab;await leaf.view.render();
    // Retire only our old main-window/duplicate panels after the replacement is ready.
    for(const old of existing)if(old!==leaf)old.detach();
    await workspace.revealLeaf(leaf);
    if(!this.connection){
      try{await this.startKernel();await leaf.view.render();}catch(e){new Notice(e.message,10000);}
    }
  }
  async openNote(notePath){
    if(!notePath)throw new Error('该溯源对象不存在');
    let file=this.app.vault.getAbstractFileByPath(notePath);
    for(let retry=0;!file&&retry<10;retry++){await new Promise(resolve=>setTimeout(resolve,100));file=this.app.vault.getAbstractFileByPath(notePath);}
    if(!file)throw new Error('文件已保存，Vault 尚未索引，请稍后打开：'+notePath);
    const workspace=this.app.workspace;
    const existing=workspace.getLeavesOfType('markdown').find(leaf=>leaf.view.file?.path===notePath);
    if(existing)this.editorLeaf=existing;
    else if(!this.editorLeaf||!this.editorLeaf.parent||this.editorLeaf.getViewState?.().pinned)this.editorLeaf=workspace.getLeaf('tab');
    await this.editorLeaf.openFile(file);
    await workspace.revealLeaf(this.editorLeaf);
  }
  async startKernel(){
    if(this.connection){try{await this.api('/health');return;}catch(e){this.connection=null;}}
    if(this.starting)return this.starting;
    this.starting=this.launch();try{return await this.starting;}finally{this.starting=null;}
  }
  runtimeDirectory(settings=this.settings){
    const configured=settings.kernelPath?.trim();
    const base=this.app.vault.adapter.getBasePath();
    const directory=this.manifest?.dir||path.join(this.app.vault.configDir||'.obsidian','plugins','opencontent');
    const pluginDir=path.resolve(base,directory);
    const valid=p=>fs.existsSync(path.join(p,'opencontent','__main__.py'));
    const managed=configured&&path.dirname(path.resolve(configured)).toLowerCase()===pluginDir.toLowerCase()&&/^kernel(?:-\d+\.\d+\.\d+)?$/.test(path.basename(configured));
    // A user-selected source checkout stays explicit; installed runtimes follow the plugin version.
    if(configured&&!managed&&valid(configured))return path.resolve(configured);
    const version=this.manifest?.version;
    if(/^\d+\.\d+\.\d+$/.test(version||'')){
      const versioned=path.join(pluginDir,'kernel-'+version);if(valid(versioned))return versioned;
    }
    const bundled=path.join(pluginDir,'kernel');
    if(valid(bundled))return bundled;
    throw new Error('运行内核缺失或配置目录已迁移。请重新安装完整插件包，或在连接设置中选择有效项目目录。');
  }
  checkEnvironment(settings=this.settings){
    new FormModal(this,'本地环境检查',(root)=>{
      el(root,'p','检查不会调用模型或读取笔记、登录与公众号密钥。登录状态需要在所选 CLI 中确认。');
      const result=el(root,'div');result.setAttribute('role','status');
      const run=async()=>{result.replaceChildren();el(result,'p','正在检查…');
        const report=await this.runDoctor(settings);if(!root.isConnected)return;result.replaceChildren();
        el(result,'h3',report.passed?'基础环境检查通过':'需要修复运行环境');
        const labels={PASS:'通过',FAIL:'需修复',WARN:'提示',NOT_CHECKED:'未检查'};
        for(const check of report.checks){el(result,'p',`${labels[check.status]} · ${check.message}`,check.status==='FAIL'?'oc-error':'');if(check.action)el(result,'p',check.action,'oc-muted');}
      };
      button(root,'重新检查',run);
      run().catch(e=>{if(root.isConnected){result.replaceChildren();el(result,'p',e.message,'oc-error');}});
    }).open();
  }
  async runDoctor(settings=this.settings){
    const runtime=this.runtimeDirectory(settings);
    const script=[path.join(runtime,'doctor.py'),path.join(runtime,'scripts','doctor.py')].find(p=>fs.existsSync(p));
    if(!script)throw new Error('环境检查程序缺失，请安装完整的新版插件包。');
    if(!settings.python?.trim())throw new Error('请先填写 Python 3.12+ 的可执行文件路径。');
    if(this.unloading)throw new Error('插件正在关闭，请重新启用后检查。');
    const args=[script,'--runtime',runtime,'--vault',this.app.vault.adapter.getBasePath()];
    if(settings.codex?.trim())args.push('--codex',settings.codex.trim());
    return new Promise((resolve,reject)=>{
      const child=spawn(settings.python.trim(),args,{cwd:runtime,windowsHide:true,shell:false,stdio:['ignore','pipe','pipe']});
      this.doctors||=new Set();this.doctors.add(child);let output='',done=false;
      const finish=(error,result)=>{if(done)return;done=true;clearTimeout(timer);this.doctors.delete(child);error?reject(error):resolve(result);};
      const timer=setTimeout(()=>{finish(new Error('环境检查超时，请检查 Python 路径后重试。'));child.kill();},15000);
      child.stdout.on('data',data=>{output+=data.toString();if(output.length>65536){finish(new Error('环境检查输出异常，请重新安装插件。'));child.kill();}});
      child.stderr.on('data',()=>{});
      child.on('error',()=>finish(new Error('无法启动所选 Python。请安装 Python 3.12+，并在连接设置中填写可执行文件的完整路径。')));
      child.on('close',code=>{
        if(done)return;
        try{const report=JSON.parse(output);
          if(![0,1].includes(code)||report.schema!==1||typeof report.passed!=='boolean'||!Array.isArray(report.checks)||report.checks.length===0||report.checks.some(c=>!['PASS','FAIL','WARN','NOT_CHECKED'].includes(c.status)||typeof c.message!=='string'||typeof c.action!=='string'))throw new Error();
          if(report.passed!==(code===0)||report.passed!==!report.checks.some(c=>c.status==='FAIL'))throw new Error();
          finish(null,report);
        }catch(e){finish(new Error('环境检查未返回有效结果，请重新安装完整插件包并检查 Python 路径。'));}
      });
    });
  }
  async launch(){
    if(!(this.app.vault.adapter instanceof FileSystemAdapter))throw new Error('当前 MVP 仅支持桌面文件系统 Vault');
    const runtime=this.runtimeDirectory();
    if(!this.settings.python?.trim())throw new Error('请设置 Python 3.12+ 可执行文件。');
    const readiness=await this.runDoctor();
    if(!readiness.passed)throw new Error(readiness.checks.filter(c=>c.status==='FAIL').map(c=>c.message+'。'+c.action).join('\n'));
    if(this.unloading)throw new Error('插件正在关闭，请重新启用后连接。');
    const base=this.app.vault.adapter.getBasePath();
    const args=['-m','opencontent','--vault',base,'serve'];
    if(this.settings.codex)args.push('--codex',this.settings.codex);
    for(const root of this.settings.skillRoots.split('\n').map(s=>s.trim()).filter(Boolean))args.push('--skill-root',root);
    const child=spawn(this.settings.python,args,{cwd:runtime,windowsHide:true,shell:false,stdio:['ignore','pipe','pipe']});this.child=child;
    let out='',err='';
    return await new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>{child.kill();reject(new Error('Kernel 启动超时：'+err.slice(-1000)));},15000);
      child.stderr.on('data',data=>{err=(err+data.toString()).slice(-4000);});
      child.on('error',e=>{clearTimeout(timer);reject(new Error('无法启动 Python，请检查可执行文件配置：'+e.message));});
      child.on('exit',code=>{clearTimeout(timer);if(this.child===child){this.connection=null;this.child=null;}reject(new Error('Kernel 已退出 '+code+' '+err));});
      child.stdout.on('data',data=>{out+=data.toString();const line=out.split('\n')[0];if(!out.includes('\n'))return;
        try{const conn=JSON.parse(line);if(!/^http:\/\/127\.0\.0\.1:\d+$/.test(conn.url)||conn.vault.toLowerCase()!==base.toLowerCase()||typeof conn.token!=='string'||conn.token.length<32)throw new Error('Kernel 返回了错误的 Vault / endpoint');this.connection=conn;clearTimeout(timer);resolve();}catch(e){clearTimeout(timer);child.kill();reject(e);}
      });
    });
  }
  async api(route,body){
    if(!this.connection)throw new Error('请启动 Kernel');
    const response=await requestUrl({url:this.connection.url+route,method:body===undefined?'GET':'POST',headers:{Authorization:'Bearer '+this.connection.token,'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),throw:false});
    if(response.status>=400)throw new Error(response.json.error||'Kernel 请求失败');return response.json;
  }
  onunload(){
    this.unloading=true;
    if(this.connection)this.api('/shutdown',{}).catch(()=>{});
    for(const child of this.doctors||[])child.kill();
    // Cooperative shutdown cancels owned agent process groups; no global process kill.
    this.app.workspace.detachLeavesOfType(VIEW);
  }
};
