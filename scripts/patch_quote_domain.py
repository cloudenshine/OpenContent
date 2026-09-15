from pathlib import Path

domain_file = Path(r"D:\Workspaces\codex_work\OpenContent\opencontent\domain.py")
text = domain_file.read_text(encoding="utf-8")

old_quote_check = """        if not isinstance(obj.get("quote"), str) or not obj["quote"].strip() or obj["quote"] not in material["body"]:
            raise Problem("Evidence quote does not occur in Material")"""

new_quote_check = """        from .quote_matcher import match_or_find_quote
        quote_str = str(obj.get("quote", "")).strip()
        matched, real_quote = match_or_find_quote(quote_str, material.get("body", ""))
        if not matched:
            raise Problem("Evidence quote does not occur in Material")
        if real_quote:
            obj["quote"] = real_quote"""

if old_quote_check in text:
    text = text.replace(old_quote_check, new_quote_check)
    domain_file.write_text(text, encoding="utf-8")
    print("domain.py quote checking patched with quote_matcher!")
else:
    print("old_quote_check not found")
