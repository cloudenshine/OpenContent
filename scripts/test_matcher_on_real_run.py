import json, re
from opencontent.quote_matcher import match_or_find_quote

with open(r'F:\Obsidian_vault\.opencontent\runs\03cc13456ecc4d69b28f8dd01ff6c145\request.json', 'r', encoding='utf-8') as f:
    req = json.load(f)
m_map = {o['oc_id']: o['body'] for o in req.get('objects', []) if o.get('type') == 'Material'}

with open(r'F:\Obsidian_vault\.opencontent\runs\03cc13456ecc4d69b28f8dd01ff6c145\stdout.log', 'r', encoding='utf-8') as f:
    raw = f.read()

json_block = re.search(r'```json\s*([\s\S]*?)\s*```', raw).group(1)
res = json.loads(json_block)

for i, ev in enumerate(res.get('evidence', [])):
    mid = ev['material']
    quote = ev['quote']
    m_body = m_map.get(mid, '')
    matched, _ = match_or_find_quote(quote, m_body)
    print(f'Evidence {i}: matched={matched}')
