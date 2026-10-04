"""The sourced clause stays verbatim; additions still require human review."""
import re
from opencontent.vault import Problem
from opencontent.rendering import public_markdown


def validate(mother, candidate):
    pages=candidate.get('pages')
    if not isinstance(pages,list) or not 1<=len(pages)<=12:raise Problem('图文计划需有 1–12 个语义页面')
    for page in pages:
        if not isinstance(page,dict) or set(page)!={'role','purpose','source_excerpt','claims','title','body','resources'}:
            raise Problem('逐页计划字段无效')
        for key in ('role','purpose','source_excerpt','title','body'):
            if not isinstance(page[key],str) or not page[key].strip():raise Problem('页面文字与目的不能为空')
        excerpt=page['source_excerpt']
        if len(excerpt.strip())<8 or excerpt not in mother['body']:raise Problem('页面原文片段缺失、过短或不属于母稿')
        cleaned=lambda text:re.sub(r'\[\[[0-9a-f]{32}(?:\|[^\]]+)?\]\]','',text)
        if cleaned(excerpt).strip() not in cleaned(page['body']):raise Problem('页面不能删改来源片段的限定语、否定或数字')
        if not isinstance(page['claims'],list) or any(c not in mother['derived_from'] for c in page['claims']):raise Problem('页面主张不属于母稿')
        if not isinstance(page['resources'],list) or len(page['resources'])>2 or not all(isinstance(r,str) for r in page['resources']):raise Problem('每页最多两份真实附件')
        public_markdown({'body':page['body'],'derived_from':page['claims']})
    return pages
