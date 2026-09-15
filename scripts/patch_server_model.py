from pathlib import Path

server_path = Path(r"D:\Workspaces\codex_work\OpenContent\opencontent\server.py")
text = server_path.read_text(encoding="utf-8")

old_code = "if route == '/providers/activate': return activate_cli(jobs,body['name'])"
new_code = "if route == '/providers/activate': return activate_cli(jobs,body['name'],model=body.get('model'))"

if old_code in text:
    text = text.replace(old_code, new_code)
    server_path.write_text(text, encoding="utf-8")
    print("server.py patched successfully!")
else:
    print("Pattern not found in server.py")
