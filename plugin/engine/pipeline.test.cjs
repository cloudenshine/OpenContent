/**
 * Tests for Auto-Feeding Pipeline
 */

const test = require('node:test');
const assert = require('node:assert/strict');
const pipeline = require('./pipeline.js');

test('pipeline.extractNoteSummary: strips frontmatter, markdown tags and links', () => {
  const md = `---
title: Test
tags: [ai, workflow]
---
# Heading 1
This is a [[test-note|Alias]] of **important** content.
\`\`\`js
console.log('secret');
\`\`\`
> Quote statement here.
`;
  const summary = pipeline.extractNoteSummary(md);
  assert.ok(!summary.includes('---'));
  assert.ok(!summary.includes('console.log'));
  assert.ok(summary.includes('This is a Alias of important content'));
  assert.ok(summary.includes('Quote statement here'));
});

test('pipeline.clusterNotes: clusters notes with high token similarity', () => {
  const notes = [
    { title: '智能体工作流设计', body: '讨论多Agent工作流自动化与节点编排方案。', path: 'note1.md' },
    { title: '智能体提示词工程', body: '关于多Agent工作流中的Prompt设计与节点状态。', path: 'note2.md' },
    { title: '宏观经济与股市', body: '分析全球央行流动性与降息周期影响。', path: 'note3.md' }
  ];

  const clusters = pipeline.clusterNotes(notes, 0.15);
  assert.equal(clusters.length, 1);
  assert.equal(clusters[0].count, 2);
  assert.equal(clusters[0].sources[0].title, '智能体工作流设计');
  assert.equal(clusters[0].sources[1].title, '智能体提示词工程');

  const candidate = pipeline.generateIdeationCandidates(clusters[0]);
  assert.ok(candidate.title.includes('智能体工作流设计'));
  assert.ok(candidate.sources.includes('note1.md'));
  assert.ok(candidate.sources.includes('note2.md'));
});
