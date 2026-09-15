from pathlib import Path

prov_file = Path(r"D:\Workspaces\codex_work\OpenContent\opencontent\providers.py")
text = prov_file.read_text(encoding="utf-8")

old_parse = """        text = output.read_text(encoding="utf-8").strip()
        if text.startswith("```json\\n") and text.endswith("```"):
            text = text[8:-3]
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise Problem("Agent final response is not valid JSON") from e"""

new_parse = """        from .json_cleaner import robust_extract_json
        raw_text = output.read_text(encoding="utf-8").strip()
        try:
            return robust_extract_json(raw_text)
        except Exception as e:
            raise Problem("Agent final response is not valid JSON: " + str(e)) from e"""

if old_parse in text:
    text = text.replace(old_parse, new_parse)
    prov_file.write_text(text, encoding="utf-8")
    print("providers.py updated with robust_extract_json!")
else:
    print("old_parse block not found")
