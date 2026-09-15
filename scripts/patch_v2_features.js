const fs = require('fs');
const path = require('path');

const mainJsPath = path.join(__dirname, '../plugin/main.js');
let code = fs.readFileSync(mainJsPath, 'utf8');

// 1. In Cockpit.prototype.board: Add Auto-Feeding banner before hero
const heroTarget = "const hero=el(root,'section',undefined,'oc-start');el(hero,'h2','今天想写点什么？');";
const heroReplacement = `// Auto-Feeding Pipeline Banner
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
      el(feedBanner, 'p', '自动监测「得到大脑」、「收件箱」等输入源，跨笔记聚类生成可证伪选题假设。', 'oc-muted');

      if (this.feedingClusters && this.feedingClusters.length) {
        for (const cluster of this.feedingClusters) {
          const candidate = pipelineEngine.generateIdeationCandidates(cluster);
          const card = el(feedBanner, 'div', undefined, 'oc-candidate-card');
          el(card, 'h4', candidate.title);
          el(card, 'p', '🎯 方向：' + candidate.direction);
          el(card, 'p', '💡 逻辑：' + candidate.logic);
          el(card, 'small', '📚 关联来源：' + candidate.sources.join(' + '));
          const adoptBtn = button(card, '一键以此灵感开启创作', async () => {
            this.homeGoal = candidate.direction;
            new Notice('已将选题注入写作框，点击下方「开始写作」即可启动！');
            await this.render();
          }, 'mod-cta');
        }
      }
    }

    const hero=el(root,'section',undefined,'oc-start');el(hero,'h2','今天想写点什么？');`;

if (!code.includes('oc-pipeline-banner')) {
  code = code.replace(heroTarget, heroReplacement);
}

// 2. In Cockpit.prototype.project: Add Dual-Mode (Simple 3-step vs Expert)
const projectSimpleTarget = `    if(p.artifacts.length){
      const draft=p.artifacts.find(a=>a.oc_id===this.artifact)||p.artifacts[0];this.artifact=draft.oc_id;
      const preview=el(root,'section',undefined,'oc-draft');el(preview,'h3','当前稿件');`;

const projectSimpleReplacement = `    const isExpertMode = this.plugin.settings.viewMode === 'expert';

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
      const preview=el(root,'section',undefined,'oc-draft');el(preview,'h3','当前稿件');`;

if (!code.includes('oc-simple-flow')) {
  code = code.replace(projectSimpleTarget, projectSimpleReplacement);
}

// 3. In Cockpit.prototype.inspector: Add Expert Radar Grid & Typography Renderer
const inspectorTarget = "el(root,'h2',a.title);this.issues(root,detail.gate);";
const inspectorReplacement = `el(root,'h2',a.title);
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

    // 原生高颜值排版渲染面板 (Typography Panel)
    if (typographyEngine) {
      const typoPanel = el(root, 'section', undefined, 'oc-typography-panel');
      el(typoPanel, 'h3', '🎨 原生高颜值排版与一键富文本发布');
      el(typoPanel, 'p', '为微信公众号、知乎、语雀等渠道实时渲染内联样式，一键复制富文本即可发布。', 'oc-muted');

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

      const copyBtn = button(typoPanel, '📋 一键复制为富文本 (粘贴到公众号)', async () => {
        try {
          const ok = await typographyEngine.copyRichTextToClipboard(renderedHtml, a.body || '');
          if (ok) new Notice('✅ 已复制富文本排版到剪贴板，直接粘贴到公众号/知乎后台即可！');
          else new Notice('⚠️ 剪贴板 API 暂不可用，可直接打开正文复制');
        } catch(err) {
          new Notice('复制失败: ' + err.message);
        }
      }, 'mod-cta');
    }`;

if (!code.includes('oc-typography-panel')) {
  code = code.replace(inspectorTarget, inspectorReplacement);
}

fs.writeFileSync(mainJsPath, code, 'utf8');
console.log('Features injected into main.js.');
