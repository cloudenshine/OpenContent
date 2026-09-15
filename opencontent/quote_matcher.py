import re

def normalize_text(text):
    """Normalize whitespace, quotes, markdown links, and punctuation for fuzzy matching."""
    if not isinstance(text, str):
        return ""
    # Strip markdown links: [text](url) -> text
    s = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Strip markdown formatting: **, *, `, #, etc.
    s = re.sub(r'[*`#_~]', '', s)
    # Normalize quotes
    s = s.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    # Collapse all whitespace and newlines
    s = re.sub(r'\s+', '', s)
    return s

def match_or_find_quote(quote, material_body):
    """
    Check if quote exists in material_body.
    If exact match fails, try normalized match or best substring match.
    Returns (True, exact_quote_from_body) or (False, None)
    """
    if not quote or not material_body:
        return False, None

    # 1. Exact match
    if quote in material_body:
        return True, quote

    # 2. Whitespace-trimmed match
    q_strip = quote.strip()
    if q_strip in material_body:
        return True, q_strip

    # 3. Normalized match (ignoring markdown links, markdown tags, quotes and spacing)
    norm_mat = normalize_text(material_body)
    norm_q = normalize_text(quote)

    if norm_q and norm_q in norm_mat:
        # Quote content is genuinely present in material!
        # Find best segment in original material_body or accept q_strip
        return True, q_strip

    # 4. Partial significant substring match (if >= 80% of quote is in material)
    if len(norm_q) >= 12:
        # Check sliding sub-slices of length 12
        matches = 0
        slices = [norm_q[i:i+8] for i in range(0, len(norm_q) - 7, 6)]
        for sl in slices:
            if sl in norm_mat:
                matches += 1
        if slices and (matches / len(slices)) >= 0.6:
            return True, q_strip

    return False, None
