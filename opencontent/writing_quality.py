"""Small, versioned writing adaptations; no upstream tool execution or model scoring."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent / 'writing_skills'
WRITING_TASKS = frozenset(('draft', 'write', 'continue', 'revise', 'plan', 'critique'))


def writing_policy(task, *, fiction=False):
    """Return the exact active instructions and traceable local adaptation metadata."""
    if task not in WRITING_TASKS:
        return None
    names = ['fiction.md' if fiction else 'substance.md']
    if task != 'plan':
        names.append('voice.md')
    texts = [(ROOT / name).read_text(encoding='utf-8').strip() for name in names]
    scope = {
        'plan': '本次只规划：辨明核心问题/戏剧问题与材料边界，提出适合体裁的组织方式；不要提前生成整篇正文。',
        'revise': '本次定向改稿：只在用户指定范围内应用这些方法，保留未要求改动的观点与文字。',
        'critique': '本次独立审稿：用这些方法检查当前稿件，给出具体位置、读者影响和最小修改建议；不要代写全文，不因格式合规自动通过。',
    }.get(task, '本次写稿或续写：完成有实质内容的草稿，再精修语言；检查不应出现在读者正文中。')
    instructions = '\n\n'.join([scope, *texts])
    manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
    active_sources = ['oh-story', 'humanizer-zh'] if fiction else ['huashu-report', 'humanizer-zh']
    if task == 'plan':
        active_sources = ['oh-story'] if fiction else ['huashu-report']
    return {
        'id': manifest['id'], 'version': manifest['version'], 'task': task,
        'mode': 'fiction' if fiction else 'evidence-bound', 'modules': names,
        'sources': [s for s in manifest['sources'] if s['id'] in active_sources],
        'sha256': hashlib.sha256(instructions.encode('utf-8')).hexdigest(),
        'instructions': instructions,
    }


def attach_writing_policy(request, task, *, fiction=False):
    policy = writing_policy(task, fiction=fiction)
    if policy:
        # Keep the existing concise editorial core; add it for Narrative nonfiction only.
        if not fiction and not request.get('editorial_guidance'):
            from .editorial import WRITING
            request['editorial_guidance'] = WRITING
        request['writing_quality'] = {k: v for k, v in policy.items() if k != 'instructions'}
        request['instructions'] += '\n\n' + policy['instructions']
        # Trace the actual composed guidance, not just the supplemental module.
        # Source material/schema are still captured in the existing full request.
        prompt = {key: request.get(key, '') for key in ('instructions', 'editorial_guidance')}
        request['writing_quality']['prompt_sha256'] = hashlib.sha256(
            json.dumps(prompt, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
        ).hexdigest()
    return request
