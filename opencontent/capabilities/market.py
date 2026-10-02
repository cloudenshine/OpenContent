"""Evidence-bounded market summaries of explicit, provenance-bearing snapshots.

These are descriptive sample counts, not causal commercial or trend predictions.
Unknown fields remain unknown. Invalid records never become plausible defaults.
"""
from collections import Counter
from datetime import datetime, timedelta, timezone
import ipaddress
import json
import math
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import uuid

from opencontent.vault import Problem, atomic, digest, now
from .market_sources import MAX_INPUT_BYTES, validate_scan_id


def clean_intro(text, max_len=200):
    if not isinstance(text, str):
        return ""
    cleaned = re.sub(r"【.*?】|\[.*?\]|（.*?）", "", text)
    cleaned = re.sub(r"求收藏|求月票|求推荐|QQ群|官方群|加群|防盗|书友群", "", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()[:max_len]


def _text(value, field, *, required=False, max_len=500):
    if value is None and not required:
        return None
    if not isinstance(value, str) or (required and not value.strip()) or len(value) > max_len:
        raise Problem(f"Market record {field} must be {'a nonempty' if required else 'a'} bounded string")
    # Font-obfuscated, replacement or control text is not silently decoded or guessed.
    if any((ord(c) < 32 and c not in '\n\r\t') or 0xE000 <= ord(c) <= 0xF8FF or c == '\ufffd' for c in value):
        raise Problem(f"Market record {field} contains unreadable or control characters")
    return value.strip() or None


def _number(value, field):
    if value is None:
        return None
    try:
        valid = not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0
    except (OverflowError, ValueError):
        valid = False
    if not valid:
        raise Problem(f"Market record {field} must be a finite nonnegative JSON number")
    return value


def _url(value, field="url"):
    value = _text(value, field, required=True, max_len=2000)
    try:
        parts = urlsplit(value)
        if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password or parts.port not in (None, 80, 443):
            raise ValueError()
        host = parts.hostname.lower()
        if any(c.isspace() for c in value) or "\\" in value or host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            raise ValueError()
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            if "." not in host or not re.fullmatch(r"[a-z0-9.-]+", host):
                raise ValueError()
        else:
            if not address.is_global:
                raise ValueError()
        query = urlencode(sorted((k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                                 if not k.lower().startswith("utm_") and k.lower() not in ("fbclid", "gclid")))
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/") or "/", query, ""))
    except ValueError as exc:
        raise Problem(f"Market record {field} must be a public HTTP(S) URL without credentials") from exc


def _observed_at(value):
    value = _text(value, "observed_at", required=True, max_len=80)
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            raise ValueError()
        stamp = stamp.astimezone(timezone.utc)
        if stamp > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError()
    except ValueError as exc:
        raise Problem("Market record observed_at must be an ISO-8601 observation timestamp with timezone, not a future analysis time") from exc
    return stamp.isoformat()


def normalize_record(raw, platform):
    if not isinstance(raw, dict):
        raise Problem(f"Platform '{platform}' record must be an object")
    title = _text(raw.get("title"), "title", required=True, max_len=300)
    rank = raw.get("rank")
    if isinstance(rank, bool) or not isinstance(rank, int) or not 1 <= rank <= 1_000_000:
        raise Problem("Market record rank must be a positive integer")
    tags = raw.get("tags", [])
    if not isinstance(tags, list) or len(tags) > 32:
        raise Problem("Market record tags must be a bounded array of strings")
    tags = list(dict.fromkeys(_text(t, "tag", required=True, max_len=100) for t in tags))
    metric = raw.get("metric")
    legacy_metrics = [key for key in ("recommendation", "reads", "likes") if key in raw and raw[key] is not None]
    for key in legacy_metrics:
        _number(raw[key], key)
    if metric is not None:
        if not isinstance(metric, dict):
            raise Problem("Market record metric must be an object")
        value = _number(metric.get("value"), "metric.value")
        if value is None:
            raise Problem("Market record metric.value is required")
        metric = {"name": _text(metric.get("name"), "metric.name", required=True, max_len=100), "value": value,
                  "unit": _text(metric.get("unit"), "metric.unit", max_len=100),
                  "source_label": _text(metric.get("source_label"), "metric.source_label", max_len=100)}
    elif legacy_metrics:
        key = legacy_metrics[0]
        metric = {"name": key, "value": raw[key], "unit": "source_defined", "source_label": key}
    intro = _text(raw.get("intro"), "intro", max_len=10000)
    record = {
        "platform": platform, "rank": rank, "title": title,
        "author": _text(raw.get("author"), "author", max_len=200),
        "genre": _text(raw.get("genre"), "genre", max_len=100),
        "status": _text(raw.get("status"), "status", max_len=100),
        "words_ten_thousand": _number(raw.get("words"), "words (万字)"),
        "popularity_metric": metric["value"] if metric else None,
        "metric": metric, "intro": clean_intro(intro) if intro else None, "intro_raw": intro,
        "tags": tags, "url": _url(raw.get("url")),
        "observed_at": _observed_at(raw.get("observed_at")),
        "source_id": _text(raw.get("source_id"), "source_id", max_len=100),
        "source_url": _url(raw["source_url"], "source_url") if raw.get("source_url") is not None else None,
        "emotional_hook": _text(raw.get("emotional_hook"), "emotional_hook", max_len=300),
        "reversal_type": _text(raw.get("reversal_type"), "reversal_type", max_len=300),
    }
    return record


def _validate_records(raw_data, minimum):
    try:
        encoded = json.dumps(raw_data, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise Problem("Market data must contain finite JSON values") from exc
    if len(encoded) > MAX_INPUT_BYTES or not isinstance(raw_data, dict) or not 1 <= len(raw_data) <= 8:
        raise Problem("Market data must be a nonempty bounded platform-to-records object (up to 8 platforms, 2 MB)")
    records, quality, seen_urls, seen_titles, seen_ranks = [], {}, set(), set(), set()
    for platform, items in raw_data.items():
        _text(platform, "platform", required=True, max_len=100)
        if not isinstance(items, list) or not minimum <= len(items) <= 200:
            raise Problem(f"Platform '{platform}' needs {minimum}-200 distinct valid records; insufficient/invalid input")
        normalized = []
        for i, item in enumerate(items):
            try:
                record = normalize_record(item, platform)
            except Problem as exc:
                raise Problem(f"Platform '{platform}', record {i + 1}: {exc}") from exc
            url_key = record["url"].split("://", 1)[1]
            title_key = (platform, record["title"].casefold(), (record["author"] or "").casefold())
            rank_key = (platform, record["source_id"], record["rank"])
            if url_key in seen_urls or title_key in seen_titles or rank_key in seen_ranks:
                raise Problem(f"Platform '{platform}', record {i + 1}: duplicate book URL/title or rank would inflate the quality gate")
            seen_urls.add(url_key)
            seen_titles.add(title_key)
            seen_ranks.add(rank_key)
            normalized.append(record)
        quality[platform] = {"total_collected": len(items), "valid_samples": len(normalized),
                             "anomalies_count": 0, "duplicates_count": 0, "quality_status": "PASS",
                             "scope": "input_snapshot_only"}
        records.extend(normalized)
    if len(records) > 1000:
        raise Problem("Market data exceeds the total sample limit")
    return records, quality, encoded


def _counts(records, field, list_field=False):
    counts = Counter()
    for r in records:
        for value in (r[field] if list_field else [r[field]]):
            if value:
                counts[value] += 1
    return sorted(counts.items(), key=lambda x: (-x[1], x[0]))


def _evidence(records):
    return [{k: r[k] for k in ("platform", "title", "url", "observed_at", "rank", "source_id")} for r in records[:5]]


class _MarketAnalyzer:
    kind = "long"
    minimum = 3

    def __init__(self, kernel):
        self.kernel = kernel

    def analyze(self, raw_platform_data, scan_id=None, source_metadata=None):
        scan_id = uuid.uuid4().hex if scan_id is None else scan_id
        validate_scan_id(scan_id)
        records, quality, raw_bytes = _validate_records(raw_platform_data, self.minimum)
        analyzed_at = now()
        source_metadata = dict(source_metadata or {
            "mode": "imported", "verification": "user_supplied_unverified", "sources": [],
            "warning": "用户提供的记录、网址和观测时间未联网核验。",
        })
        # Inputs and results are reviewable for both analyzers, with separate clocks.
        records_path = f".opencontent/runs/market-{scan_id}-records.json"
        input_path = f".opencontent/runs/market-{scan_id}-input.json"
        report_json_path = f".opencontent/runs/market-{scan_id}-report.json"
        report_path = f"OpenContent/Market/{self.kind.title()}/{scan_id}.md"
        source_metadata.update({"input_path": input_path, "input_sha256": digest(raw_bytes)})
        observations = [r["observed_at"] for r in records]
        report = {
            "schema": f"opencontent.market-{self.kind}.v2", "scan_id": scan_id,
            "analyzed_at": analyzed_at, "observed_at_range": {"earliest": min(observations), "latest": max(observations)},
            "platforms": list(raw_platform_data), "total_samples": len(records), "quality_reports": quality,
            "source_metadata": source_metadata, "records": records, "records_path": records_path,
            "report_path": report_path, "report_json_path": report_json_path,
            "limitations": [
                "仅为输入快照的描述性统计，样本量门禁不等于统计代表性或事实核验。",
                "平台指标口径不同，未跨平台比较或合并热度、阅读量与推荐数。",
                "单次榜单快照不能证明完读率、转发率、营收、市场饱和度或趋势寿命。",
                "机会方向是待作者验证的创作假设，不是商业表现保证；缺失字段保持未知。",
            ],
        }
        if self.kind == "long":
            self._long_analysis(report, records)
        else:
            self._short_analysis(report, records)
        # Resolve all destinations before the first write, including direct analyzer calls.
        destinations = [self.kernel.vault.safe(p) for p in (input_path, records_path, report_json_path, report_path)]
        atomic(destinations[0], raw_bytes)
        atomic(destinations[1], json.dumps(records, ensure_ascii=False, indent=2).encode("utf-8"))
        atomic(destinations[2], json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"))
        atomic(destinations[3], self._markdown(report).encode("utf-8"))
        return report

    @staticmethod
    def _long_analysis(report, records):
        genres, tropes = _counts(records, "genre"), _counts(records, "tags", True)
        report.update({"top_genres": genres, "top_tropes": tropes[:8], "opportunity_candidates": [],
                       "field_coverage": {"genre": sum(bool(r["genre"]) for r in records),
                                          "tags": sum(bool(r["tags"]) for r in records)}})
        for i, (genre, count) in enumerate(genres[:3], 1):
            matched = [r for r in records if r["genre"] == genre]
            report["opportunity_candidates"].append({
                "direction_id": f"long-opp-{i}", "classification": "creative_hypothesis",
                "theme": f"{genre}：可进一步研究的创作方向",
                "core_appeal": f"本次样本中有 {count} 本标为「{genre}」；可先比较这些作品的开篇与差异点。",
                "evidence_sources": [r["title"] for r in matched[:5]], "evidence": _evidence(matched),
                "commercial_logic": "未知；现有快照不支持商业因果判断。",
                "risk_assessment": "样本选择偏差与同质化风险需另行验证。",
            })

    @staticmethod
    def _short_analysis(report, records):
        emotions, reversals = _counts(records, "emotional_hook"), _counts(records, "reversal_type")
        report.update({"top_emotions": emotions, "top_reversals": reversals, "opportunity_candidates": [],
                       "trend_shelf_life": "未知；需要跨期观测，不能从单次快照推出30/60天有效期。",
                       "field_coverage": {"emotional_hook": sum(bool(r["emotional_hook"]) for r in records),
                                          "reversal_type": sum(bool(r["reversal_type"]) for r in records)}})
        for i, (emotion, count) in enumerate(emotions[:3], 1):
            matched = [r for r in records if r["emotional_hook"] == emotion]
            report["opportunity_candidates"].append({
                "direction_id": f"short-opp-{i}", "classification": "creative_hypothesis",
                "emotion_core": emotion, "sample_count": count,
                "opening_formula": "尚未分析原文开篇；需阅读并核验对应作品后形成写作方案。",
                "saturation_risk": "未知；当前样本不足以估计全市场饱和程度。",
                "shelf_life_days": None, "rescan_recommended_before": None,
                "representative_samples": [r["title"] for r in matched[:5]], "evidence": _evidence(matched),
            })

    @staticmethod
    def _markdown(report):
        label = "长篇" if "market-long" in report["schema"] else "短篇"
        meta = report["source_metadata"]
        lines = [f"# {label}市场样本报告（{report['scan_id']}）", "",
                 f"- 分析时间：{report['analyzed_at']}",
                 f"- 来源观测时间：{report['observed_at_range']['earliest']} 至 {report['observed_at_range']['latest']}",
                 f"- 输入方式：{meta['mode']} / {meta['verification']}",
                 f"- 有效样本：{report['total_samples']}（{', '.join(report['platforms'])}）",
                 f"- {meta.get('warning', '')}", "", "## 事实边界", ""]
        lines.extend(f"- {item}" for item in report["limitations"])
        lines.extend(["", "## 来源与采集凭据", ""])
        for source in meta.get("sources", []):
            lines.append(f"- {source['label']}：{source['url']}；观测 {source['observed_at']}；SHA-256 {source['sha256']}；快照 {source['snapshot_path']}")
        if not meta.get("sources"):
            lines.append("- 导入数据未联网核验，逐条来源网址与用户提供的观测时间见下。")
        lines.extend(["", "## 逐条样本与观测时间", ""])
        for r in report["records"]:
            title = r["title"].replace("[", "\\[").replace("]", "\\]")
            lines.append(f"- {r['platform']} #{r['rank']} [{title}]({r['url']})；观测 {r['observed_at']}；题材 {r['genre'] or '未知'}")
        summary = {k: v for k, v in report.items() if k in ("quality_reports", "top_genres", "top_tropes", "top_emotions", "top_reversals", "field_coverage", "opportunity_candidates", "trend_shelf_life")}
        lines.extend(["", "## 描述性统计与待验证创作假设", "", "```json", json.dumps(summary, ensure_ascii=False, indent=2), "```", "",
                      f"完整标准化记录：{report['records_path']}", f"机器可读报告：{report['report_json_path']}", ""])
        return "\n".join(lines)


class LongMarketAnalyzer(_MarketAnalyzer):
    """Long-fiction snapshot counts; requires three unique valid books per platform."""


class ShortMarketAnalyzer(_MarketAnalyzer):
    """Short-fiction snapshot counts; missing annotations remain unknown."""
    kind = "short"
    minimum = 2
