"""Editorial rules. No Obsidian, provider, database, or network dependencies."""
import re
from datetime import datetime
from urllib.parse import urlsplit
from .vault import Problem, digest

STATES = ("CAPTURED", "DISTILLED", "IDEA", "RESEARCHING", "ARGUMENT_READY", "DRAFTING", "REVIEWING", "APPROVED", "PUBLISHED", "LEARNING")
AXES = ("Evidence", "Logic", "Originality", "Voice", "Utility")
REF_TYPES = {"Knowledge": "Material", "Claim": "Knowledge", "Idea": "Knowledge", "Artifact": "Claim"}


def linked(objects, project, kind):
    return [o for o in objects.values() if o.get("project") == project and o["type"] == kind]


def require_object(objects, uid, kind=None):
    obj = objects.get(uid)
    if not obj or (kind and obj["type"] != kind):
        raise Problem(f"Missing {kind or 'object'}: {uid}")
    return obj


def validate(obj, objects):
    kind = obj["type"]
    if kind != "Project":
        require_object(objects, obj.get("project"), "Project")
    if kind in ("Project", "Artifact") and obj.get("state") not in STATES:
        raise Problem("Project/Artifact needs an explicit production state")
    if kind == "Project" and not all(isinstance(obj.get(k), str) and obj[k].strip() for k in ("goal", "audience")):
        raise Problem("Project requires goal and audience")
    if kind == "Material" and (not isinstance(obj.get("source"), str) or not obj["source"].strip() or not obj["body"].strip()):
        raise Problem("Material requires a source string and nonempty original text")
    if kind in ("Knowledge", "Idea") and not obj["body"].strip():
        raise Problem(f"{kind} requires nonempty content")
    if kind in REF_TYPES:
        refs = obj.get("derived_from", [])
        if not refs:
            raise Problem(f"{kind} requires provenance to {REF_TYPES[kind]}")
        for uid in refs:
            parent = require_object(objects, uid, REF_TYPES[kind])
            if parent.get("project") != obj.get("project"):
                raise Problem("Cross-project provenance is not supported in MVP; explicitly capture a source")
    if kind == "Claim":
        if obj.get("confidence") not in ("low", "medium", "high"):
            raise Problem("Claim confidence must be low/medium/high")
        if not obj["body"].strip():
            raise Problem("Claim needs a statement")
    if kind == "Evidence":
        claim = require_object(objects, obj.get("claim"), "Claim")
        material = require_object(objects, obj.get("material"), "Material")
        validate(material, objects)
        if claim["project"] != obj["project"] or material["project"] != obj["project"]:
            raise Problem("Evidence belongs to another project")
        if obj.get("relation") not in ("supports", "opposes"):
            raise Problem("Evidence needs supports/opposes")
        from .quote_matcher import match_or_find_quote
        quote_str = str(obj.get("quote", "")).strip()
        matched, real_quote = match_or_find_quote(quote_str, material.get("body", ""))
        if not matched:
            raise Problem("Evidence quote does not occur in Material")
        if real_quote:
            obj["quote"] = real_quote
    if kind == "Review":
        artifact = require_object(objects, obj.get("artifact"), "Artifact")
        if artifact["project"] != obj["project"]:
            raise Problem("Review belongs to another project")
        if obj.get("mode") == "critique":
            scores = obj.get("axes", {})
            if set(scores) != set(AXES):
                raise Problem("Review needs exactly five axes")
            for name, value in scores.items():
                if not isinstance(value, dict) or value.get("status") not in ("PASS", "WARN", "FAIL") or not isinstance(value.get("reason"), str) or len(value["reason"].strip()) < 8:
                    raise Problem(f"{name} needs PASS/WARN/FAIL and a substantive reason")
            if not isinstance(obj.get("claims_complete"), bool):
                raise Problem("Reviewer must explicitly assess claim completeness")
        elif obj.get("mode") == "decision":
            if obj.get("decision") not in ("accept", "reject") or obj.get("origin") != "human":
                raise Problem("Final decision must be human accept/reject")
        else:
            raise Problem("Unknown review mode")
        if not obj.get("reviewer") or not obj.get("context_hash"):
            raise Problem("Review must identify reviewer and dependency hash")
    if kind == "Publication":
        artifact = require_object(objects, obj.get("artifact"), "Artifact")
        if artifact["project"] != obj["project"]:
            raise Problem("Publication belongs to another project")
        status=obj.get('delivery_status','MANUAL')
        if status not in ('MANUAL','PREPARED','SENDING','UNKNOWN','SUBMITTED','REMOTE_DRAFT','PUBLISHED','FAILED','CONFLICT','CANCELLED','WITHDRAWN'):
            raise Problem('Unknown publication delivery status')
        if not obj.get('context_hash'):
            raise Problem('Publication requires an approved version hash')
        if status not in ('MANUAL','PUBLISHED'):
            if not obj.get('channel') or not isinstance(obj.get('payload'),dict):
                raise Problem('Publication outbox requires channel and payload')
            return
        url = obj.get("url")
        if not isinstance(url, str) or urlsplit(url).scheme not in ("http", "https") or not urlsplit(url).hostname:
            raise Problem("Publication requires a valid HTTP(S) URL")
        try:
            datetime.fromisoformat(obj.get("published_at", ""))
        except (ValueError, TypeError):
            raise Problem("Publication requires an ISO publication date")
        if not obj.get("context_hash"):
            raise Problem("Publication requires an approved version hash")


def context_hash(objects, artifact, policies):
    # Review/Publication and declared state do not recursively invalidate the review.
    pid = artifact["project"]
    content = {}
    for uid, obj in objects.items():
        if (obj.get("project") == pid or uid == pid) and obj["type"] not in ("Review", "Publication"):
            if obj["type"] == "Artifact" and uid != artifact["oc_id"]:
                continue
            content[uid] = {k: v for k, v in obj.items() if k not in ("hash", "path", "state", "history", "planning")}
    return digest({"content": content, "constitution": policies})


def evidence_graph(objects, artifact):
    rows = []
    for cid in artifact.get("derived_from", []):
        claim = objects.get(cid, {})
        evidence = [e for e in objects.values() if e["type"] == "Evidence" and e.get("claim") == cid]
        rows.append({"claim": claim, "supports": [e for e in evidence if e.get("relation") == "supports"],
                     "opposes": [e for e in evidence if e.get("relation") == "opposes"],
                     "knowledge": [objects.get(k, {"oc_id": k, "missing": True}) for k in claim.get("derived_from", [])],
                     "materials": [objects.get(m, {"oc_id": m, "missing": True}) for k in claim.get("derived_from", [])
                                   for m in objects.get(k, {}).get("derived_from", [])],
                     "used_by": [o["oc_id"] for o in objects.values() if o["type"] == "Artifact" and cid in o.get("derived_from", [])]})
    return rows


def argument_issues(objects, pid):
    issues = []
    claims = linked(objects, pid, "Claim")
    if not claims:
        issues.append("No registered Claims")
    for claim in claims:
        try:
            validate(claim, objects)
            for kid in claim.get("derived_from", []):
                knowledge = objects.get(kid)
                if not knowledge or knowledge.get("type") != "Knowledge":
                    # Self-heal or warn gracefully instead of hard-crashing the whole production pipeline
                    issues.append(f"Claim references unmaterialized knowledge: {kid}")
                    continue
                validate(knowledge, objects)
                for mid in knowledge.get("derived_from", []):
                    mat = objects.get(mid)
                    if mat and mat.get("type") == "Material":
                        validate(mat, objects)
            evidence = [e for e in linked(objects, pid, "Evidence") if e.get("claim") == claim["oc_id"]]
            if not any(e.get("relation") == "supports" for e in evidence):
                issues.append(f"Unsupported Claim: {claim['title']}")
            for e in evidence:
                validate(e, objects)
        except Problem as e:
            issues.append(str(e))
    return issues


def gate(objects, artifact, policies, errors=()):
    issues = list(errors)
    pid = artifact["project"]
    try:
        project = require_object(objects, pid, "Project")
        validate(project, objects)
        if not project.get("thesis", "").strip():
            issues.append("Project thesis is missing")
    except Problem as e:
        issues.append(str(e))
    issues.extend(argument_issues(objects, pid))
    try:
        validate(artifact, objects)
    except Problem as e:
        issues.append(str(e))
    if len(artifact.get("body", "").strip()) < 80:
        issues.append("Draft is shorter than 80 characters")
    markers = set(re.findall(r"\[\[([0-9a-f]{32})(?:\|[^\]]+)?\]\]", artifact["body"]))
    if markers != set(artifact.get("derived_from", [])):
        issues.append("Draft Claim links must match its registered Claims")
    is_v2 = artifact.get("protocol") == "opencontent.artifact.v2" and "claim_bindings" in artifact
    bindings = artifact.get("claim_bindings", {})
    if isinstance(bindings, list):
        bindings = {b.get("claim"): b for b in bindings if isinstance(b, dict)}
    elif not isinstance(bindings, dict):
        bindings = {}

    from .quote_matcher import _extract_tokens_of_interest

    for cid in artifact.get("derived_from", []):
        claim = objects.get(cid)
        if not claim:
            continue
        if is_v2:
            b = bindings.get(cid)
            if not b or not isinstance(b.get("text_excerpt"), str) or not b["text_excerpt"].strip():
                issues.append(f"Missing claim binding for: {claim['title']}")
            elif b["text_excerpt"].strip() not in artifact["body"]:
                issues.append(f"Claim binding excerpt is absent from draft: {claim['title']}")
            else:
                claim_tokens = _extract_tokens_of_interest(claim["body"])
                excerpt_tokens = _extract_tokens_of_interest(b["text_excerpt"])
                if not claim_tokens.issubset(excerpt_tokens):
                    issues.append(f"Claim binding altered critical tokens for: {claim['title']}")
        else:
            if claim["body"].strip() not in artifact["body"]:
                issues.append(f"Claim statement is absent from draft: {claim['title']}")
    for text in policies.values():
        headings = ("Audience", "Voice", "Editorial Principles", "Evidence Policy", "Citation Policy", "Originality Standard", "Forbidden Patterns", "Quality Gates")
        if any("## " + h not in text for h in headings):
            issues.append("CONTENT.md is missing required sections")
        section = re.search(r"## Forbidden Patterns\s*\n(.*?)(?=\n## |\Z)", text, re.S)
        for word in re.findall(r"^-\s+(.+)$", section[1] if section else "", re.M):
            if word.strip() and word.strip() in artifact["body"]:
                issues.append("Forbidden pattern: " + word.strip())
    fingerprint = context_hash(objects, artifact, policies)
    reviews = sorted([r for r in linked(objects, pid, "Review") if r.get("artifact") == artifact["oc_id"] and r.get("mode") == "critique"], key=lambda r: r["created"])
    review = reviews[-1] if reviews else None
    axes = {axis: {"status": "WARN", "reason": "No current review"} for axis in AXES}
    if not review or review.get("context_hash") != fingerprint:
        issues.append("Missing or stale Critic Review")
    else:
        try:
            validate(review, objects)
            if review.get("reviewer") == artifact.get("author"):
                raise Problem("Creator cannot review their own draft")
            axes = review["axes"]
            if not review.get("claims_complete"):
                issues.append("Important facts are missing from the Claim registry")
            if is_v2:
                claim_reviews = review.get("claim_reviews")
                if not isinstance(claim_reviews, dict):
                    issues.append("Critic Review must evaluate claim semantic fidelity for v2 artifact")
                else:
                    for cid in artifact.get("derived_from", []):
                        cr = claim_reviews.get(cid)
                        if not isinstance(cr, dict) or not cr.get("faithful"):
                            issues.append(f"Claim semantic fidelity not confirmed by Critic for: {objects.get(cid, {}).get('title', cid)}")
            for axis, value in axes.items():
                if value["status"] != "PASS":
                    issues.append(axis + ": " + value["status"])
            contested = [r for r in evidence_graph(objects, artifact) if r["opposes"]]
            if contested and not review.get("conflict_resolution", "").strip():
                issues.append("Opposing Evidence requires a review resolution")
        except Problem as e:
            issues.append(str(e))
    decisions = sorted([r for r in linked(objects, pid, "Review") if r.get("mode") == "decision" and r.get("artifact") == artifact["oc_id"]], key=lambda r: r["created"])
    decision = decisions[-1] if decisions else None
    approved = bool(not issues and decision and decision.get("context_hash") == fingerprint and
                    decision.get("decision") == "accept" and decision.get("origin") == "human" and decision.get("review") == (review or {}).get("oc_id"))
    return {"status": "PASS" if not issues else "BLOCKED", "issues": issues, "axes": axes,
            "context_hash": fingerprint, "review": review, "approved": approved,
            "needs_judgment": not approved, "decision": decision}


def transition(objects, project, target, policies, errors=()):
    current = project.get("state")
    if current not in STATES or target not in STATES or STATES.index(target) != STATES.index(current) + 1:
        raise Problem(f"Illegal transition {current} → {target}")
    pid = project["oc_id"]
    if errors:
        raise Problem("Vault diagnostics block transition: " + "; ".join(errors))
    requirements = {
        "DISTILLED": ("Material", "Knowledge"), "IDEA": ("Idea",), "RESEARCHING": ("Idea",),
        "ARGUMENT_READY": ("Claim", "Evidence"), "DRAFTING": ("Claim", "Evidence"), "REVIEWING": ("Artifact", "Review"),
        "APPROVED": ("Artifact", "Review"), "PUBLISHED": ("Publication",), "LEARNING": ("Publication",)}
    for kind in requirements.get(target, ()):
        candidates = linked(objects, pid, kind)
        if not candidates:
            raise Problem("Transition requires " + kind)
        for obj in candidates:
            validate(obj, objects)
    if target in ("IDEA", "RESEARCHING", "ARGUMENT_READY", "DRAFTING", "REVIEWING", "APPROVED") and not project.get("thesis", "").strip():
        raise Problem("A thesis is required")
    if target in ("ARGUMENT_READY", "DRAFTING", "REVIEWING", "APPROVED"):
        issues = argument_issues(objects, pid)
        if issues:
            raise Problem("; ".join(issues))
    if target == "APPROVED":
        artifacts = linked(objects, pid, "Artifact")
        if not artifacts or not all(gate(objects, a, policies, errors)["approved"] for a in artifacts):
            raise Problem("Approval requires current passing gate and explicit human decision for every artifact")
    if target == "PUBLISHED":
        for a in linked(objects,pid,'Artifact'):
            matches=[p for p in linked(objects,pid,'Publication') if p.get('artifact')==a['oc_id'] and
                p.get('delivery_status','MANUAL') in ('PUBLISHED','MANUAL') and p.get('url') and p.get('published_at') and
                p.get('context_hash')==context_hash(objects,a,policies)]
            if not matches:
                raise Problem('Every artifact requires a current published receipt')
            if not gate(objects, a, policies, errors)["approved"]:
                raise Problem("Publication requires approved artifact")
    if target == "LEARNING" and not any(p.get("body", "").strip() for p in linked(objects, pid, "Publication")):
        raise Problem("Learning tracking needs an explicit observation; automatic feedback learning is out of scope")
    return target
