from pathlib import Path

wb_file = Path(r"D:\Workspaces\codex_work\OpenContent\opencontent\workbench.py")
text = wb_file.read_text(encoding="utf-8")

old_wb_check = """    revision=result['revision']
    if revision is not None:
        if turn['mode']!='revise' or not isinstance(revision,dict) or set(revision)!={'artifact','title','body'}:raise Problem('改稿提案格式无效')"""

new_wb_check = """    revision=result.get('revision')
    if revision is not None:
        if turn['mode']!='revise':
            revision = None
        elif isinstance(revision,dict):
            # Allow LLM to omit unchanged title or add extra metadata
            if 'body' in revision and ('artifact' in revision or 'title' in revision):
                if 'artifact' not in revision:
                    # Default to current project's primary artifact
                    objs = k.read()[0]
                    arts = [o for o in objs.values() if o['type']=='Artifact' and o['project']==pid]
                    if arts: revision['artifact'] = arts[0]['oc_id']
                if 'title' not in revision:
                    objs = k.read()[0]
                    target_a = objs.get(revision.get('artifact'))
                    revision['title'] = target_a['title'] if target_a else '改稿'
                revision = {'artifact': revision['artifact'], 'title': str(revision['title']).strip(), 'body': str(revision['body']).strip()}
            else:
                raise Problem('改稿提案格式无效：缺少正文内容')
        else:
            raise Problem('改稿提案格式无效')"""

if old_wb_check in text:
    text = text.replace(old_wb_check, new_wb_check)
    wb_file.write_text(text, encoding="utf-8")
    print("workbench.py relaxed for LLM revision fields!")
else:
    print("old_wb_check not found in workbench.py")
