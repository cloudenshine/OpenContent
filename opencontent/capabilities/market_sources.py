"""Explicit, bounded market inputs. No model-generated or demonstration fallback.

Live sources are reviewed public HTML pages, not guessed/private APIs. Import
provenance records what the caller supplied, never a claim of online verification.
"""
from dataclasses import dataclass, field
from html.parser import HTMLParser
import ipaddress
import json
import os
import stat
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener, getproxies, proxy_bypass
from urllib.robotparser import RobotFileParser

from opencontent.vault import Problem, atomic, digest, now

MAX_INPUT_BYTES = 2_000_000
HTTP_TIMEOUT = 10
USER_AGENT = "OpenContent-Market/1.0 (+https://github.com/cloudenshine/OpenContent)"
SOURCES = {
    "qimao-boy-hot-daily": {
        "platform": "qimao", "task": "long-scan", "label": "七猫男生大热日榜（首页）",
        "url": "https://www.qimao.com/paihang/boy/hot/date/",
    },
    "qimao-girl-hot-daily": {
        "platform": "qimao", "task": "long-scan", "label": "七猫女生大热日榜（首页）",
        "url": "https://www.qimao.com/paihang/girl/hot/date/",
    },
}


def validate_scan_id(scan_id):
    import re
    if not isinstance(scan_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", scan_id):
        raise Problem("Market scan_id must contain 1-80 safe letters, digits, underscores or hyphens")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Problem("Market source redirected; automatic redirects and login/verification workarounds are disabled", 502)


def _fetch_public_page(url, max_bytes=MAX_INPUT_BYTES, content_type="text/html"):
    """Exact reviewed HTTPS URLs only; reject redirects/private DNS preflight.

    The configured system proxy/CA policy is honored. The DNS check is a
    preflight, not IP pinning; this is not a general caller-controlled URL fetcher.
    """
    allowed = {s["url"] for s in SOURCES.values()} | {"https://www.qimao.com/robots.txt"}
    if url not in allowed:
        raise Problem("Unsupported market source URL")
    parsed = urlsplit(url)
    try:
        # A configured HTTPS proxy resolves its own destination. Do not bypass
        # that route or require local DNS where the environment intentionally has
        # none. Direct transport gets a public-address preflight, not IP pinning.
        proxied = bool(getproxies().get("https")) and not proxy_bypass(parsed.hostname)
        if not proxied:
            addresses = socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
            if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
                raise Problem("Market source resolved to a non-public address; fetch blocked", 502)
        request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": content_type,
                                        "Accept-Encoding": "identity"})
        started = time.monotonic()
        with build_opener(_NoRedirect()).open(request, timeout=HTTP_TIMEOUT) as response:
            if response.status != 200 or response.geturl() != url:
                raise Problem("Market source returned an unexpected status or URL", 502)
            mime = response.headers.get_content_type()
            if mime != content_type:
                raise Problem(f"Market source returned {mime}; expected {content_type}", 502)
            if response.headers.get("Content-Encoding", "identity").lower() not in ("", "identity"):
                raise Problem("Compressed market responses are not supported", 502)
            length = response.headers.get("Content-Length")
            if length is not None and (not length.isdecimal() or int(length) > max_bytes):
                raise Problem("Market source response exceeds the size limit", 502)
            parts, size = [], 0
            while True:
                if time.monotonic() - started > HTTP_TIMEOUT * 2:
                    raise Problem("Market source response exceeded its time limit", 504)
                # read1 returns after one buffered/socket read, so slow trickle
                # bodies cannot hide forever inside read(n) between deadline checks.
                part = response.read1(min(64_000, max_bytes + 1 - size))
                if not part:
                    break
                parts.append(part)
                size += len(part)
                if size > max_bytes:
                    raise Problem("Market source response exceeds the size limit", 502)
            body = b"".join(parts)
            if not body:
                raise Problem("Market source returned an empty response", 502)
            try:
                body.decode("utf-8", errors="strict")
            except UnicodeError as exc:
                raise Problem("Market source is not valid UTF-8", 502) from exc
            return body
    except Problem:
        raise
    except (HTTPError, URLError, OSError, ValueError) as exc:
        raise Problem(f"Market source unavailable ({url}): {type(exc).__name__}. No substitute data was used.", 502) from exc


@dataclass
class _Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    def find(self, *, cls=None, tag=None):
        result, stack = [], list(reversed(self.children))
        while stack:
            node = stack.pop()
            if not isinstance(node, _Node):
                continue
            if (cls is None or cls in node.attrs.get("class", "").split()) and (tag is None or tag == node.tag):
                result.append(node)
            stack.extend(reversed(node.children))
        return result

    def text(self):
        parts, stack = [], list(reversed(self.children))
        while stack:
            node = stack.pop()
            if isinstance(node, str):
                parts.append(node)
            elif node.tag not in ("script", "style"):
                stack.extend(reversed(node.children))
        return " ".join(" ".join(parts).split())


class _HTMLTree(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node("root")
        self.stack = [self.root]
        self.nodes = 0

    def handle_starttag(self, tag, attrs):
        self.nodes += 1
        if self.nodes > 40_000 or len(self.stack) > 100:
            raise Problem("Market source HTML exceeds parser limits", 502)
        node = _Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _one(node, cls):
    matches = node.find(cls=cls)
    if len(matches) != 1:
        raise Problem(f"Market source layout changed: expected one {cls}", 502)
    return matches[0]


def parse_qimao_ranking(body, source_id, observed_at):
    """Parse the visible official rank-list, never execute scripts or fetch chapters."""
    import re
    source = SOURCES[source_id]
    if not isinstance(body, bytes) or not 0 < len(body) <= MAX_INPUT_BYTES:
        raise Problem("Market source HTML must be nonempty and bounded", 502)
    try:
        html = body.decode("utf-8", errors="strict")
        tree = _HTMLTree()
        tree.feed(html)
        tree.close()
    except (UnicodeError, RecursionError) as exc:
        raise Problem("Market source HTML could not be parsed", 502) from exc
    lists = tree.root.find(cls="rank-list")
    if len(lists) != 1 or "基于昨日书籍热度排行" not in tree.root.text():
        raise Problem("Market source ranking missing, blocked or changed; no sample data substituted", 502)
    items = lists[0].find(cls="rank-list-item")
    if not 3 <= len(items) <= 100:
        raise Problem("Market source ranking has insufficient or unexpected sample count", 502)
    records = []
    for item in items:
        title = _one(item, "s-book-title")
        url = urljoin(source["url"], title.attrs.get("href", ""))
        if not re.fullmatch(r"https://www\.qimao\.com/shuku/[0-9]+/", url):
            raise Problem("Market source returned an unexpected book URL", 502)
        info = _one(item, "s-book-info")
        links = info.find(tag="a")
        if len(links) != 3:
            raise Problem("Market source author/genre layout changed", 502)
        rank = _one(item, "rank-number").text()
        word_match = re.search(r"(?:^|\s)(\d+(?:\.\d+)?)万字(?:$|\s)", info.text())
        if not rank.isdecimal() or not word_match:
            raise Problem("Market source has malformed rank or word count", 502)
        heat = _one(item, "rank-num").text()
        unit = _one(item, "rank-unit").text()
        if not re.fullmatch(r"\d+(?:\.\d+)?", heat) or unit not in ("", "万", "亿"):
            raise Problem("Market source has an unsupported popularity metric", 502)
        records.append({
            "title": title.text(), "rank": int(rank), "author": links[0].text(),
            "genre": links[2].text(), "tags": [], "words": float(word_match[1]),
            "status": next((n.text() for n in info.find(tag="em") if n.text() in ("连载中", "已完结")), None),
            "intro": _one(item, "s-book-intro").text(),
            "metric": {"name": "qimao_heat", "value": float(heat) * {"": 1, "万": 10000, "亿": 100000000}[unit],
                       "unit": "platform_heat", "source_label": "热度"},
            "url": url, "source_url": source["url"], "source_id": source_id,
            "observed_at": observed_at,
        })
    if sorted(r["rank"] for r in records) != list(range(1, len(records) + 1)):
        raise Problem("Market source ranks are duplicate, missing or not a first-page ranking", 502)
    return records


def resolve_market_input(task_request, task_name, kernel, run_id):
    """Return (raw_platform_data, source_metadata) for the runtime/analyzer boundary."""
    validate_scan_id(run_id)
    if task_name not in ("long-scan", "short-scan"):
        raise Problem("Unsupported market task")
    choices = [k for k in ("raw_data", "market_input_path", "source_ids", "market_source") if k in task_request]
    if len(choices) != 1:
        raise Problem("请选择一个真实扫榜输入：source_ids 公共榜单或 raw_data 导入 JSON（每条需 title、rank、url、observed_at）；不使用示例数据。")
    mode = choices[0]
    if mode in ("raw_data", "market_input_path"):
        if mode == "market_input_path":
            path_value = task_request[mode]
            if not isinstance(path_value, str) or not path_value.endswith(".json"):
                raise Problem("market_input_path must be a Vault-relative JSON path")
            path = kernel.vault.safe(path_value)
            try:
                info = path.lstat()
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_INPUT_BYTES:
                    raise Problem("Market import must be a regular, unlinked JSON file up to 2 MB")
                flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
                with os.fdopen(os.open(path, flags), "rb") as stream:
                    opened = os.fstat(stream.fileno())
                    if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                            or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)):
                        raise Problem("Market import changed or is not a regular single-link file")
                    payload = stream.read(MAX_INPUT_BYTES + 1)
                if len(payload) > MAX_INPUT_BYTES:
                    raise Problem("Market import exceeds the 2 MB limit")
                data = json.loads(payload.decode("utf-8-sig"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                raise Problem("Market import must be a readable UTF-8 JSON file") from exc
        else:
            data = task_request[mode]
        try:
            payload = json.dumps(data, ensure_ascii=False, allow_nan=False).encode("utf-8")
        except (TypeError, ValueError, RecursionError) as exc:
            raise Problem("Market import must contain finite JSON values") from exc
        if len(payload) > MAX_INPUT_BYTES:
            raise Problem("Market import exceeds the 2 MB limit")
        if not isinstance(data, dict) or not data:
            raise Problem("Market import must be a nonempty platform-to-records JSON object")
        return data, {
            "mode": "imported", "verification": "user_supplied_unverified", "input_sha256": digest(payload),
            "received_at": now(), "sources": [],
            "warning": "导入记录及其网址、观测时间均由用户提供，未联网核验；分析时间不代表采集时间。",
        }
    source_ids = task_request[mode]
    if mode == "market_source":
        source_ids = [source_ids]
    if not isinstance(source_ids, list) or not 1 <= len(source_ids) <= 2 or any(not isinstance(s, str) for s in source_ids):
        raise Problem("source_ids must contain one or two supported public ranking source IDs")
    if len(set(source_ids)) != len(source_ids):
        raise Problem("Duplicate market source IDs are not allowed")
    for source_id in source_ids:
        if source_id not in SOURCES or SOURCES[source_id]["task"] != task_name:
            raise Problem(f"Unsupported {task_name} public source: {source_id}. 短篇暂无已验证的公开采集源，请导入带 URL 与 observed_at 的真实记录。")
    # One robots request per scan; deny/timeout/error are visible, never bypassed.
    robots_body = _fetch_public_page("https://www.qimao.com/robots.txt", max_bytes=64_000, content_type="text/plain")
    robots = RobotFileParser()
    robots.parse(robots_body.decode("utf-8").splitlines())
    raw_data, sources, snapshots = {}, [], []
    for source_id in source_ids:
        source = SOURCES[source_id]
        if not robots.can_fetch(USER_AGENT, source["url"]):
            raise Problem("Market source robots policy disallows collection; please import an authorized snapshot", 502)
        body = _fetch_public_page(source["url"])
        observed_at = now()
        records = parse_qimao_ranking(body, source_id, observed_at)
        raw_data.setdefault(source["platform"], []).extend(records)
        path = f".opencontent/runs/market-{run_id}-{source_id}.html"
        sources.append({"source_id": source_id, "platform": source["platform"], "label": source["label"],
                        "url": source["url"], "observed_at": observed_at, "ranking_period": "昨日（来源页面标注，未提供精确发布时刻）",
                        "sha256": digest(body), "snapshot_path": path, "total_collected": len(records),
                        "robots_sha256": digest(robots_body)})
        snapshots.append((path, body))
    for path, body in snapshots:
        atomic(kernel.vault.safe(path), body)
    return raw_data, {
        "mode": "live", "verification": "retrieved_public_page", "sources": sources,
        "warning": "仅统计指定公开榜单首页快照；未核验平台指标计算方式，不代表全平台或跨期趋势。",
    }
