from pathlib import Path

k_file = Path(r"D:\Workspaces\codex_work\OpenContent\opencontent\kernel.py")
text = k_file.read_text(encoding="utf-8")

old_check = """        keys = {"distill": {"knowledge", "idea"}, "research": {"claims", "evidence"}, "draft": {"artifact"},
                "critique": {"axes", "claims_complete", "conflict_resolution", "summary"}}[stage]
        if set(result) != keys:
            raise Problem("Agent returned unexpected fields; state/approval changes are forbidden")"""

new_check = """        keys = {"distill": {"knowledge", "idea"}, "research": {"claims", "evidence"}, "draft": {"artifact"},
                "critique": {"axes", "claims_complete", "conflict_resolution", "summary"}}[stage]
        # Ignore extra benign meta fields returned by LLMs (e.g. reasoning, thought, comments)
        cleaned = {k: v for k, v in result.items() if k in keys}
        if not keys.issubset(cleaned.keys()):
            missing = keys - set(cleaned.keys())
            raise Problem(f"Agent response missing required fields: {', '.join(missing)}")
        result = cleaned"""

if old_check in text:
    text = text.replace(old_check, new_check)
    k_file.write_text(text, encoding="utf-8")
    print("kernel.py apply_result relaxed for benign extra fields!")
else:
    print("old_check not found in kernel.py")
