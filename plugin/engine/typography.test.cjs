/**
 * Tests for Typography Engine
 */

const test = require('node:test');
const assert = require('node:assert/strict');
const typography = require('./typography.js');

test('typography.renderArticleHtml: renders 3 distinct themes with inline styles', () => {
  const md = `# 文章标题

这是首段介绍内容。包含 **加粗文字** 和 \`代码标记\`。

## 二级小节

- 关键点一
- 关键点二

> 这是一段关键引文
`;

  const serifHtml = typography.renderArticleHtml(md, 'serif');
  assert.ok(serifHtml.includes('Songti SC'));
  assert.ok(serifHtml.includes('<h1 style='));
  assert.ok(serifHtml.includes('<blockquote style='));

  const academicHtml = typography.renderArticleHtml(md, 'academic');
  assert.ok(academicHtml.includes('PingFang SC'));
  assert.ok(academicHtml.includes('border-bottom: 1px solid #111'));

  const techDarkHtml = typography.renderArticleHtml(md, 'techDark');
  assert.ok(techDarkHtml.includes('#0f172a'));
  assert.ok(techDarkHtml.includes('#38bdf8'));
});
