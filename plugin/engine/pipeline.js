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

module.exports = {
  DEFAULT_FEEDING_DIRS,
  extractNoteSummary,
  scanIntakeSources,
  clusterNotes,
  generateIdeationCandidates
};
