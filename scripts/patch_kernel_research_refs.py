from pathlib import Path
import re

k_path = Path(r"D:\Workspaces\codex_work\OpenContent\opencontent\kernel.py")
text = k_path.read_text(encoding="utf-8")

# In stage == "research"
old_research_block = """                    for c in result["claims"]:
                        if c["key"] in mapping:
                            raise Problem("Duplicate claim key")
                        mapping[c["key"]] = make("Claim", c["title"], c["statement"], derived_from=c["knowledge"], confidence=c["confidence"])["oc_id"]"""

new_research_block = """                    # Map existing knowledge objects in project
                    existing_k_ids = [o["oc_id"] for o in objects.values() if o.get("project")==pid and o.get("type")=="Knowledge"]
                    for c in result["claims"]:
                        if c["key"] in mapping:
                            raise Problem("Duplicate claim key")
                        # If LLM hallucinated a non-existent knowledge key, bind to known existing knowledge or first available
                        valid_k_refs = [k for k in c.get("knowledge", []) if k in existing_k_ids]
                        if not valid_k_refs and existing_k_ids:
                            valid_k_refs = [existing_k_ids[0]]
                        mapping[c["key"]] = make("Claim", c["title"], c["statement"], derived_from=valid_k_refs, confidence=c.get("confidence", 0.8))["oc_id"]"""

if old_research_block in text:
    text = text.replace(old_research_block, new_research_block)
    k_path.write_text(text, encoding="utf-8")
    print("kernel.py research block patched!")
else:
    print("old_research_block not found")
