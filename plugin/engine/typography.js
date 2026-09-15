/**
 * High-aesthetic Typography & Multi-channel Publishing Engine
 * Offers 3 native theme renderers:
 * 1. Elegant Serif (优雅衬线) - Editorial & Humanities
 * 2. Academic Minimalist (学术极简) - Monograph & Technical
 * 3. Modern Tech Dark (科技深色) - Future & Engineering
 * 
 * Supports one-click Rich Text HTML clipboard export for WeChat Official Accounts, Zhihu, and Feishu.
 */

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

module.exports = {
  THEMES,
  cleanReaderText,
  renderArticleHtml,
  copyRichTextToClipboard
};
