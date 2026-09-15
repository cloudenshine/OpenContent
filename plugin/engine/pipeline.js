/**
 * Auto-Feeding Pipeline for OpenContent
 * Automatically scans and monitors note entrypoints (得到大脑, 收件箱, Web Clipper, etc.)
 * Detects topic clusters, extracts candidate materials, and generates ideation prompts.
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

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
  const sourceA = cluster.sources[0];
  const sourceB = cluster.sources[1];

  return {
    id: digest(sourceA.path + sourceB.path).slice(0, 32),
    title: `基于「${sourceA.title}」与「${sourceB.title}」的深度综合选题`,
    direction: `探究 ${sourceA.title} 提出的核心实践，与 ${sourceB.title} 中的方法论如何交叉验证并落地。`,
    sources: [sourceA.path, sourceB.path],
    logic: `来源一提供一手观察与案例事实，来源二提供结构化方法与验证边界。两者结合可形成完整闭环。`,
    readerBenefit: `让读者既获得微观执行抓手，又具备宏观判定标准，避免单一来源的信息偏差。`
  };
}

module.exports = {
  DEFAULT_FEEDING_DIRS,
  extractNoteSummary,
  scanIntakeSources,
  clusterNotes,
  generateIdeationCandidates
};
