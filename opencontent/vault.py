"""Markdown is authoritative. SQLite only serializes writers and tracks jobs."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import threading
import uuid
from datetime import datetime, timezone

import yaml

TYPES = {"Material", "Knowledge", "Claim", "Evidence", "Idea", "Project", "Artifact", "Review", "Publication"}


class Problem(ValueError):
    def __init__(self, message, status=422):
        super().__init__(message)
        self.status = status


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    if not isinstance(value, bytes):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise Problem("Frontmatter keys must be unique strings")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def encode(obj):
    meta = {k: v for k, v in obj.items() if k not in ("body", "path", "hash")}
    return ("---\n" + yaml.safe_dump(meta, allow_unicode=True, sort_keys=False) + "---\n\n" + obj.get("body", "") + "\n").encode("utf-8")


def parse(raw, path):
    try:
        text = raw.decode("utf-8-sig").replace("\r\n", "\n")
        if not text.startswith("---\n"):
            raise Problem("Missing YAML frontmatter")
        header, body = text[4:].split("\n---\n", 1)
        # Aliases are unnecessary for our small schema; disallow expansion bombs.
        if any(isinstance(t, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken)) for t in yaml.scan(header)):
            raise Problem("YAML anchors/aliases are not supported")
        meta = yaml.load(header, Loader=UniqueLoader)
        if not isinstance(meta, dict) or meta.get("type") not in TYPES:
            raise Problem("Invalid object type")
        if not isinstance(meta.get("oc_id"), str) or len(meta["oc_id"]) != 32 or any(c not in "0123456789abcdef" for c in meta["oc_id"]):
            raise Problem("Invalid stable oc_id")
        if not isinstance(meta.get("title"), str) or not meta["title"].strip():
            raise Problem("Object needs a title")
        if not isinstance(meta.get("derived_from", []), list) or not all(isinstance(x, str) for x in meta.get("derived_from", [])):
            raise Problem("derived_from must be an ID list")
        return {**meta, "body": body.strip(), "path": path, "hash": digest(raw)}
    except (UnicodeError, yaml.YAMLError, ValueError, TypeError) as e:
        raise Problem(f"{path}: {e}") from e


class Vault:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.runtime = self.safe(".opencontent")
        self.runtime.mkdir(exist_ok=True)
        self.content = self.safe("OpenContent")
        self.content.mkdir(exist_ok=True)
        self.mutex = threading.RLock()
        self._parse_cache = {}
        self.db = self.runtime / "runtime.sqlite3"
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, project TEXT, status TEXT, detail TEXT, created TEXT, updated TEXT)")
        with self.lock():
            self.recover()

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.db, timeout=15)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def lock(self):
        with self.mutex, self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            yield

    def safe(self, relative):
        path = self.root / relative
        if not path.resolve().is_relative_to(self.root) or path.is_symlink():
            raise Problem("Path escapes Vault")
        # Reject junctions/symlink ancestors even if currently pointing inside.
        for part in (path, *path.parents):
            if part == self.root:
                break
            if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
                raise Problem("Linked directories are not supported")
        return path

    def initialize(self):
        target = self.safe("CONTENT.md")
        if not target.exists():
            template = Path(__file__).resolve().parent.parent / "templates" / "CONTENT.md"
            atomic(target, template.read_bytes())

    def scan(self):
        objects, errors = {}, []
        seen = set()
        for path in sorted(self.content.rglob("*.md")):
            rel = path.relative_to(self.root).as_posix()
            try:
                path = self.safe(rel)
                if path.name == "CONTENT.md":
                    continue
                if path.stat().st_size > 1_000_000:
                    raise Problem("Object exceeds 1 MB")
                raw = path.read_bytes()
                fingerprint = digest(raw)
                cached = self._parse_cache.get(rel)
                if cached is None or cached[0] != fingerprint:
                    cached = (fingerprint, parse(raw, rel))
                    self._parse_cache[rel] = cached
                seen.add(rel)
                obj = deepcopy(cached[1])
                if obj["oc_id"] in objects:
                    raise Problem("Duplicate oc_id")
                objects[obj["oc_id"]] = obj
            except (Problem, OSError) as e:
                errors.append(f"{rel}: {e}")
        self._parse_cache = {p: value for p, value in self._parse_cache.items() if p in seen}
        return objects, errors

    def constitution(self, project=None):
        paths = ["CONTENT.md"]
        if project:
            paths.append(f"OpenContent/Project/{project}/CONTENT.md")
        found = {}
        for rel in paths:
            path = self.safe(rel)
            if path.exists():
                if path.stat().st_size > 100_000:
                    raise Problem("CONTENT.md exceeds 100 KB")
                found[rel] = path.read_text(encoding="utf-8")
        if "CONTENT.md" not in found:
            raise Problem("Vault CONTENT.md is missing")
        return found

    def token(self):
        objects, errors = self.scan()
        return digest({"files": {k: v["hash"] for k, v in objects.items()}, "errors": errors,
                       "policies": {p.relative_to(self.root).as_posix(): digest(self.safe(p.relative_to(self.root)).read_bytes())
                                    for p in [self.root / "CONTENT.md", *self.content.rglob("CONTENT.md")] if p.exists()}})

    def new(self, kind, title, body, project=None, **meta):
        if kind not in TYPES or not isinstance(body, str) or not isinstance(title, str) or not title.strip():
            raise Problem("Invalid object")
        uid = uuid.uuid4().hex
        obj = {"oc_id": uid, "type": kind, "title": title, "created": now(), "derived_from": [],
               "project": project, **meta, "body": body}
        obj["path"] = f"OpenContent/{kind}/{uid}.md"
        return obj

    def commit(self, objects, expected):
        # Caller holds lock. Journal is temporary runtime state, never the content source of truth.
        if self.token() != expected:
            raise Problem("Vault changed while work was running; review changes and retry", 409)
        entries = []
        seen = set()
        for obj in objects:
            path = self.safe(obj["path"])
            if obj["path"] in seen:
                raise Problem("Duplicate transaction path")
            seen.add(obj["path"])
            before = path.read_bytes() if path.exists() else None
            if before is not None and obj.get("hash") != digest(before):
                raise Problem("Concurrent file edit; refusing overwrite", 409)
            after = encode(obj)
            parse(after, obj["path"])
            entries.append({"path": obj["path"], "before": before.decode("utf-8") if before is not None else None,
                            "after": after.decode("utf-8")})
        journal = self.runtime / "transaction.json"
        atomic(journal, json.dumps(entries, ensure_ascii=False).encode("utf-8"))
        try:
            for entry in entries:
                path = self.safe(entry["path"])
                current = path.read_bytes().decode("utf-8") if path.exists() else None
                if current != entry["before"]:
                    raise Problem("External editor changed a file during commit", 409)
                atomic(path, entry["after"].encode("utf-8"))
            journal.unlink()
        except BaseException:
            self.recover()
            raise

    def recover(self):
        journal = self.runtime / "transaction.json"
        if not journal.exists():
            return
        entries = json.loads(journal.read_text(encoding="utf-8"))
        conflicts = []
        for entry in reversed(entries):
            path = self.safe(entry["path"])
            current = path.read_bytes().decode("utf-8") if path.exists() else None
            if current == entry["after"]:
                if entry["before"] is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic(path, entry["before"].encode("utf-8"))
            elif current != entry["before"]:
                conflicts.append(entry["path"])
        if conflicts:
            raise Problem("Recovery needs inspection; external edits preserved: " + ", ".join(conflicts), 409)
        journal.unlink()
