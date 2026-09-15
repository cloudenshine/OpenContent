import json
import os
import urllib.request
from pathlib import Path

def discover_available_models(cli_name):
    """Dynamically discover models available from the local Codex or Claude environment."""
    models = []
    
    # 1. Try querying local OpenAI-compatible endpoint (e.g. opencodex / local proxy on port 10100)
    try:
        req = urllib.request.Request("http://127.0.0.1:10100/v1/models", headers={"User-Agent": "OpenContent"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("data", []):
                mid = item.get("id")
                if mid and mid not in [m["id"] for m in models]:
                    models.append({"id": mid, "name": mid, "source": "local_proxy"})
    except Exception:
        pass

    # 2. Inspect ~/.codex/model-catalogs/*.json
    try:
        catalog_dir = Path.home() / ".codex" / "model-catalogs"
        if catalog_dir.is_dir():
            for cat_file in catalog_dir.glob("*.json"):
                try:
                    cdata = json.loads(cat_file.read_text(encoding="utf-8"))
                    for m in cdata.get("models", []):
                        slug = m.get("slug")
                        disp = m.get("display_name", slug)
                        if slug and slug not in [item["id"] for item in models]:
                            models.append({"id": slug, "name": disp, "source": "codex_catalog"})
                except Exception:
                    pass
    except Exception:
        pass

    # 3. Add well-known flagship models according to selected CLI
    if cli_name == "claude":
        claude_defaults = [
            {"id": "claude-3-7-sonnet-latest", "name": "Claude 3.7 Sonnet (Latest)", "source": "preset"},
            {"id": "claude-3-5-sonnet-latest", "name": "Claude 3.5 Sonnet (Latest)", "source": "preset"},
            {"id": "claude-3-5-haiku-latest", "name": "Claude 3.5 Haiku (Fast)", "source": "preset"},
            {"id": "claude-3-opus-latest", "name": "Claude 3 Opus", "source": "preset"},
            {"id": "sonnet", "name": "Sonnet (Default Alias)", "source": "preset"},
            {"id": "opus", "name": "Opus (Default Alias)", "source": "preset"}
        ]
        for m in claude_defaults:
            if m["id"] not in [item["id"] for item in models]:
                models.append(m)
    else:
        codex_defaults = [
            {"id": "gpt-5.6-sol", "name": "GPT-5.6 Sol (Flagship)", "source": "preset"},
            {"id": "gpt-5.6-terra", "name": "GPT-5.6 Terra (Balanced)", "source": "preset"},
            {"id": "gpt-5.6-luna", "name": "GPT-5.6 Luna", "source": "preset"},
            {"id": "gpt-5.3-codex-spark", "name": "GPT-5.3 Codex Spark (High Speed)", "source": "preset"},
            {"id": "gpt-5.5", "name": "GPT-5.5", "source": "preset"},
            {"id": "gpt-5.4", "name": "GPT-5.4", "source": "preset"},
            {"id": "gpt-5.4-mini", "name": "GPT-5.4 Mini", "source": "preset"},
            {"id": "o3-mini", "name": "o3-mini (Reasoning)", "source": "preset"},
            {"id": "o3", "name": "o3 (Full Reasoning)", "source": "preset"},
            {"id": "gpt-4o", "name": "GPT-4o", "source": "preset"}
        ]
        for m in codex_defaults:
            if m["id"] not in [item["id"] for item in models]:
                models.append(m)

    return models

if __name__ == "__main__":
    print("Codex models:", len(discover_available_models("codex")))
    print("Claude models:", len(discover_available_models("claude")))
