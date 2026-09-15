from pathlib import Path

k_file = Path(r"D:\Workspaces\codex_work\OpenContent\opencontent\kernel.py")
text = k_file.read_text(encoding="utf-8")

old_check = """        # Ignore extra benign meta fields returned by LLMs (e.g. reasoning, thought, comments)
        cleaned = {k: v for k, v in result.items() if k in keys}
        if not keys.issubset(cleaned.keys()):
            missing = keys - set(cleaned.keys())
            raise Problem(f"Agent response missing required fields: {', '.join(missing)}")
        result = cleaned"""

new_check = """        # Forbidden state or approval tampering from Agent response
        forbidden_fields = {"state", "approved", "approval", "token"}
        if any(f in result for f in forbidden_fields):
            raise Problem("Agent returned unexpected fields; state/approval changes are forbidden")
        
        # Allow benign LLM thought / commentary / reasoning fields, but strictly require all expected schema keys
        cleaned = {k: v for k, v in result.items() if k in keys}
        if not keys.issubset(cleaned.keys()):
            missing = keys - set(cleaned.keys())
            raise Problem(f"Agent response missing required fields: {', '.join(missing)}")
        result = cleaned"""

if old_check in text:
    text = text.replace(old_check, new_check)
    k_file.write_text(text, encoding="utf-8")
    print("kernel.py forbidden fields check restored while allowing benign reasoning fields!")
else:
    print("old_check not found in kernel.py")
