"""Approved Markdown for an editor/publisher of the user's choice. No external execution."""
import json
import os
import re
from urllib.parse import urlsplit
from .domain import gate, require_object
from .vault import Problem, digest


def write_once(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    except FileExistsError:
        if path.read_bytes() != raw:
            raise Problem("An existing handoff was edited or is incomplete; it will not be overwritten", 409)


def public_source(material):
    candidate = material.get("source_url") or material.get("source", "")
    try:
        parsed = urlsplit(candidate)
        if parsed.scheme in ("http", "https") and parsed.hostname and not parsed.username and not parsed.password:
            # Avoid transferring token-like query strings from captured source URLs.
            return parsed._replace(query="", fragment="").geturl()
    except ValueError:
        pass
    return "本地材料（未附公开链接）"


def reader_body(artifact):
    """Strip registered internal Claim markers; preserve authored prose and citations."""
    claims = set(artifact['derived_from'])
    return re.sub(r"\[\[([0-9a-f]{32})(?:\|[^\]]+)?\]\]",
                  lambda match: '' if match[1] in claims else match[0], artifact['body'])


def export_approved(kernel, aid, expected):
    vault = kernel.vault
    with vault.lock():
        if vault.token() != expected:
            raise Problem("Content changed before handoff; refresh and review", 409)
        objects, errors = kernel.read()
        artifact = require_object(objects, aid, "Artifact")
        result = gate(objects, artifact, vault.constitution(artifact["project"]), [*errors,*kernel.source_issues(objects,artifact['project'])])
        if not result["approved"]:
            raise Problem("Only a currently approved artifact can be handed off")
        # Provenance remains in the Vault; reader-facing exports contain authored text only.
        article = f"# {artifact['title']}\n\n{reader_body(artifact)}\n"
        # Version the export path so existing v1 handoffs and user edits remain intact.
        rel = f"OpenContent-Exports/{aid}-{result['context_hash'][:16]}-reader-v2.md"
        raw = article.encode("utf-8")
        target = vault.safe(rel)
        if vault.token() != expected:
            raise Problem("Content changed while preparing handoff; refresh and review", 409)
        write_once(target, raw)
        receipt_path = vault.safe(f".opencontent/handoffs/{aid}-{result['context_hash'][:16]}-reader-v2.json")
        receipt = {"protocol": "opencontent.approved-markdown.v2", "artifact": aid,
                   "context_hash": result["context_hash"], "file_hash": digest(raw), "path": rel,
                   "review": result["review"]["oc_id"], "decision": result["decision"]["oc_id"],
                   "status": "LOCAL_HANDOFF_ONLY"}
        write_once(receipt_path, json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8"))
        return {**receipt, "article": article}
