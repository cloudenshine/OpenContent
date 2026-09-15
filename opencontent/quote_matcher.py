"""Precise quote locator and verifier. No arbitrary fuzzy substring thresholding."""
import re

def normalize_text(text):
    """Normalize whitespace, quotes, markdown links, and punctuation for alignment."""
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


def _extract_tokens_of_interest(text):
    """Extract numbers, dates, units, and negation words to guard semantic fidelity."""
    if not isinstance(text, str):
        return set()
    numbers = set(re.findall(r'\d+(?:\.\d+)?', text))
    negations = set(re.findall(r'[不非无未没]|没有|not|no|never|none|neither', text, re.IGNORECASE))
    return numbers | negations


def _build_char_map(raw):
    """
    Build a mapping from normalized character positions to original indices in raw string.
    """
    norm_chars = []
    orig_indices = []
    i = 0
    n = len(raw)
    while i < n:
        # Check markdown link [text](url)
        link_m = re.match(r'\[([^\]]+)\]\([^)]+\)', raw[i:])
        if link_m:
            inner = link_m.group(1)
            for offset, ch in enumerate(inner):
                if ch not in '*`#_~' and not ch.isspace():
                    norm_ch = ch.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
                    norm_chars.append(norm_ch)
                    orig_indices.append(i + 1 + offset)
            i += link_m.end()
            continue
        
        ch = raw[i]
        if ch in '*`#_~' or ch.isspace():
            i += 1
            continue
        
        norm_ch = ch.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
        norm_chars.append(norm_ch)
        orig_indices.append(i)
        i += 1

    return "".join(norm_chars), orig_indices


def match_or_find_quote(quote, material_body):
    """
    Check if quote exists in material_body.
    Returns (True, exact_slice_from_body) or (False, None).
    Guarantees:
    - Never uses partial similarity or threshold-based slice fuzzy matching.
    - An altered number (e.g. 20 -> 200) or negation flip is strictly rejected.
    - When normalized matching succeeds, returns the actual slice from material_body.
    """
    if not isinstance(quote, str) or not isinstance(material_body, str):
        return False, None

    q_strip = quote.strip()
    if not q_strip or not material_body:
        return False, None

    # 1. Exact match in body
    if q_strip in material_body:
        return True, q_strip

    # 2. Match with normalized whitespace / markdown
    norm_mat, char_map = _build_char_map(material_body)
    norm_q = normalize_text(q_strip)

    if not norm_q or not norm_mat:
        return False, None

    # Substring search in normalized stream
    start_pos = norm_mat.find(norm_q)
    if start_pos == -1:
        return False, None

    # Check for ambiguity: if it matches multiple places, ensure they don't produce divergent slices
    second_pos = norm_mat.find(norm_q, start_pos + 1)
    if second_pos != -1:
        orig_start1 = char_map[start_pos]
        orig_end1 = char_map[start_pos + len(norm_q) - 1] + 1
        orig_start2 = char_map[second_pos]
        orig_end2 = char_map[second_pos + len(norm_q) - 1] + 1
        slice1 = material_body[orig_start1:orig_end1].strip()
        slice2 = material_body[orig_start2:orig_end2].strip()
        if slice1 != slice2:
            return False, None

    # Map back to exact span in original material_body
    orig_start = char_map[start_pos]
    orig_end = char_map[start_pos + len(norm_q) - 1] + 1
    exact_slice = material_body[orig_start:orig_end].strip()

    # Guard semantic fidelity: numbers, dates, negations must match exactly
    if _extract_tokens_of_interest(q_strip) != _extract_tokens_of_interest(exact_slice):
        return False, None

    # Ensure normalized text of the exact slice matches norm_q
    if normalize_text(exact_slice) != norm_q:
        return False, None

    # Ensure the returned quote is indeed an exact slice of material_body
    if exact_slice in material_body:
        return True, exact_slice

    return False, None
