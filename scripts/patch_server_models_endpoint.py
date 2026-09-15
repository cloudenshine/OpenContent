from pathlib import Path

server_path = Path(r"D:\Workspaces\codex_work\OpenContent\opencontent\server.py")
text = server_path.read_text(encoding="utf-8")

# 1. Import model_discovery
old_import = "from .providers import detect_cli, activate_cli"
new_import = "from .providers import detect_cli, activate_cli\nfrom .model_discovery import discover_available_models"

if old_import in text and "discover_available_models" not in text:
    text = text.replace(old_import, new_import)

# 2. Add GET /models route
old_route = "if route == '/providers': return {'available':detect_cli(),'active':{n:p.capabilities() for n,p in jobs.providers.items()},'notice':getattr(jobs,'provider_notice',None) if not jobs.providers else None}"
new_route = """if route == '/models':
                cli = list(jobs.providers.keys())[0] if jobs.providers else 'codex'
                current_model = getattr(list(jobs.providers.values())[0], 'model', None) if jobs.providers else None
                return {'cli': cli, 'current': current_model, 'models': discover_available_models(cli)}
            if route == '/providers': return {'available':detect_cli(),'active':{n:p.capabilities() for n,p in jobs.providers.items()},'notice':getattr(jobs,'provider_notice',None) if not jobs.providers else None}"""

if old_route in text and "route == '/models'" not in text:
    text = text.replace(old_route, new_route)

server_path.write_text(text, encoding="utf-8")
print("server.py updated with /models route!")
