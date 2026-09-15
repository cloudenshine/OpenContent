def robust_extract_json(text):
    """Robustly extract and clean JSON from raw Agent/LLM output."""
    import json
    import re
    
    if not isinstance(text, str):
        raise ValueError("Input must be string")
        
    s = text.strip()
    
    # 1. Direct try
    try:
        return json.loads(s)
    except Exception:
        pass
        
    # 2. Markdown block extraction (```json ... ``` or ``` ...)
    md_matches = re.findall(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', s, re.IGNORECASE)
    for block in md_matches:
        try:
            return json.loads(block.strip())
        except Exception:
            pass

    # 3. Bracket matching: find outermost { ... }
    first_brace = s.find('{')
    last_brace = s.rfind('}')
    if first_brace != -1 and last_brace > first_brace:
        candidate = s[first_brace:last_brace+1]
        try:
            return json.loads(candidate)
        except Exception:
            # Try removing trailing commas
            cleaned = re.sub(r',\s*([}\]])', r'\1', candidate)
            try:
                return json.loads(cleaned)
            except Exception:
                pass
                
    raise ValueError("No valid JSON found in Agent output")
