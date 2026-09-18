"""Market Intelligence Module for Long and Short Narrative Scans.
Implements distinct models for Long-form and Short-form market analyses.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Dict, List, Any, Optional
import uuid

from opencontent.vault import Problem, atomic, now, digest


# ----------------------------------------------------------------------
# Platform Cleaners & Normalizers
# ----------------------------------------------------------------------

def clean_intro(text: str, max_len: int = 200) -> str:
    """Clean book introduction: strip marketing noise, tags, excessive whitespace."""
    if not isinstance(text, str):
        return ""
    cleaned = re.sub(r"【.*?】|\[.*?\]|（.*?）", "", text)
    cleaned = re.sub(r"求收藏|求月票|求推荐|QQ群|官方群|加群|防盗|书友群", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:max_len]


def normalize_record(raw: Dict[str, Any], platform: str) -> Dict[str, Any]:
    """Normalize a raw book record from platform into standard market schema."""
    title = str(raw.get("title", "")).strip()
    if not title:
        raise Problem(f"Platform '{platform}' record missing title")
    
    author = str(raw.get("author", "未知作者")).strip()
    genre = str(raw.get("genre", "综合")).strip()
    rank = int(raw.get("rank", 999))
    status = str(raw.get("status", "连载")).strip()
    
    words = raw.get("words", 0)
    try:
        words = float(words)
    except (ValueError, TypeError):
        words = 0.0

    score_or_recom = raw.get("recommendation", raw.get("reads", raw.get("likes", 0)))
    try:
        score_or_recom = float(score_or_recom)
    except (ValueError, TypeError):
        score_or_recom = 0.0

    intro = clean_intro(raw.get("intro", ""))

    return {
        "platform": platform,
        "rank": rank,
        "title": title,
        "author": author,
        "genre": genre,
        "status": status,
        "words_ten_thousand": round(words, 2),
        "popularity_metric": score_or_recom,
        "intro": intro,
        "tags": [t.strip() for t in raw.get("tags", []) if isinstance(t, str) and t.strip()],
        "url": str(raw.get("url", "")).strip(),
    }


# ----------------------------------------------------------------------
# Long Market Analyzer (起点、番茄、七猫、晋江)
# ----------------------------------------------------------------------

class LongMarketAnalyzer:
    """Market analyzer for long serialized fiction (focusing on retention, progression, and paid/traffic patterns)."""

    def __init__(self, kernel):
        self.kernel = kernel

    def analyze(
        self,
        raw_platform_data: Dict[str, List[Dict[str, Any]]],
        scan_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        scan_id = scan_id or uuid.uuid4().hex
        captured_at = now()
        
        normalized_records = []
        quality_reports = {}
        total_valid = 0

        for platform, items in raw_platform_data.items():
            valid_items = []
            anomalies = []
            for item in items:
                try:
                    norm = normalize_record(item, platform)
                    valid_items.append(norm)
                except Exception as e:
                    anomalies.append({"item": item, "error": str(e)})

            # Quality gate: check sample size
            is_sufficient = len(valid_items) >= 3
            quality_reports[platform] = {
                "total_collected": len(items),
                "valid_samples": len(valid_items),
                "anomalies_count": len(anomalies),
                "quality_status": "PASS" if is_sufficient else "INSUFFICIENT_DATA",
            }
            if not is_sufficient:
                quality_reports[platform]["warning"] = "样本量不足3条，无法提炼稳健模式"

            normalized_records.extend(valid_items)
            total_valid += len(valid_items)

        if total_valid < 3:
            raise Problem(f"长篇扫榜有效样本总量不足（仅 {total_valid} 本），触发质量门禁阻断。")

        # Extract repeating tropes and genre distribution
        genre_counts = {}
        trope_frequency = {}
        for r in normalized_records:
            g = r["genre"]
            genre_counts[g] = genre_counts.get(g, 0) + 1
            for tag in r["tags"]:
                trope_frequency[tag] = trope_frequency.get(tag, 0) + 1

        top_genres = sorted(genre_counts.items(), key=lambda x: -x[1])
        top_tropes = sorted(trope_frequency.items(), key=lambda x: -x[1])[:8]

        # Formulate 3 opportunity candidates grounded in evidence
        candidates = []
        for i in range(min(3, len(top_genres))):
            primary_g = top_genres[i][0]
            matched_books = [b["title"] for b in normalized_records if b["genre"] == primary_g][:3]
            candidates.append({
                "direction_id": f"long-opp-{i+1}",
                "theme": f"{primary_g}方向创新切口",
                "core_appeal": f"针对 {primary_g} 读者群体，结合热门元素 {', '.join([t[0] for t in top_tropes[:2]])}",
                "evidence_sources": matched_books,
                "commercial_logic": "番茄侧完读率高 / 起点侧世界观扩展性强",
                "risk_assessment": "若无前三章紧凑因果线，容易在中期出现叙事疲劳",
            })

        report = {
            "schema": "opencontent.market-long.v1",
            "scan_id": scan_id,
            "captured_at": captured_at,
            "platforms": list(raw_platform_data.keys()),
            "total_samples": total_valid,
            "quality_reports": quality_reports,
            "top_genres": top_genres,
            "top_tropes": top_tropes,
            "opportunity_candidates": candidates,
        }

        # Persist as reviewable asset in Vault
        vault_path = self.kernel.vault.safe(f"OpenContent/Market/Long/{scan_id}.md")
        vault_path.parent.mkdir(parents=True, exist_ok=True)
        
        md_content = f"""---
scan_id: {scan_id}
type: MarketRunLong
captured_at: {captured_at}
total_samples: {total_valid}
---

# 长篇网文市场扫榜报告（{scan_id[:8]}）

- **采集时间**：{captured_at}
- **覆盖平台**：{', '.join(raw_platform_data.keys())}
- **有效样本总数**：{total_valid}

## 一、数据质量门禁报告

{json.dumps(quality_reports, ensure_ascii=False, indent=2)}

## 二、热门题材与核心元素分布

- **高频题材**：{', '.join([f'{g} ({c}本)' for g, c in top_genres])}
- **跨平台重复热词/标签**：{', '.join([f'{t} ({c}次)' for t, c in top_tropes])}

## 三、机会方向建议（基于真实样本）

"""
        for c in candidates:
            md_content += f"""### {c['theme']}
- **读者吸引力**：{c['core_appeal']}
- **榜单代表样本**：{', '.join(c['evidence_sources'])}
- **商业模型考量**：{c['commercial_logic']}
- **创作风险提示**：{c['risk_assessment']}

"""

        atomic(vault_path, md_content.encode("utf-8"))
        atomic(self.kernel.vault.safe(f".opencontent/runs/market-{scan_id}-records.json"),
               json.dumps(normalized_records, ensure_ascii=False, indent=2).encode("utf-8"))

        return report


# ----------------------------------------------------------------------
# Short Market Analyzer (知乎盐选、点众、黑岩、七猫短篇)
# ----------------------------------------------------------------------

class ShortMarketAnalyzer:
    """Market analyzer for short fiction (focusing on emotions, virality, completion rate, shelf-life)."""

    def __init__(self, kernel):
        self.kernel = kernel

    def analyze(
        self,
        raw_platform_data: Dict[str, List[Dict[str, Any]]],
        scan_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        scan_id = scan_id or uuid.uuid4().hex
        captured_at = now()

        normalized_records = []
        quality_reports = {}
        total_valid = 0

        for platform, items in raw_platform_data.items():
            valid_items = []
            anomalies = []
            for item in items:
                try:
                    norm = normalize_record(item, platform)
                    # Short specific: extract emotional tone
                    norm["emotional_hook"] = str(item.get("emotional_hook", "强烈情感反差")).strip()
                    norm["reversal_type"] = str(item.get("reversal_type", "信息差反转")).strip()
                    valid_items.append(norm)
                except Exception as e:
                    anomalies.append({"item": item, "error": str(e)})

            is_sufficient = len(valid_items) >= 2
            quality_reports[platform] = {
                "total_collected": len(items),
                "valid_samples": len(valid_items),
                "anomalies_count": len(anomalies),
                "quality_status": "PASS" if is_sufficient else "INSUFFICIENT_DATA",
            }
            normalized_records.extend(valid_items)
            total_valid += len(valid_items)

        if total_valid < 2:
            raise Problem(f"短篇扫榜有效样本量不足（仅 {total_valid} 本），触发门禁阻断。")

        # Emotional analysis & Viral drivers
        emotions_map = {}
        reversals_map = {}
        for r in normalized_records:
            emo = r.get("emotional_hook", "共鸣")
            rev = r.get("reversal_type", "反转")
            emotions_map[emo] = emotions_map.get(emo, 0) + 1
            reversals_map[rev] = reversals_map.get(rev, 0) + 1

        top_emotions = sorted(emotions_map.items(), key=lambda x: -x[1])
        top_reversals = sorted(reversals_map.items(), key=lambda x: -x[1])

        # Formulate short fiction opportunities with explicit shelf-life and saturation risk
        candidates = [
            {
                "direction_id": f"short-opp-1",
                "emotion_core": "不公压抑 → 决绝离开 → 全员悔恨",
                "opening_formula": "开局三句内亮出无法调和的伦理或利益背叛，主角果断切割",
                "saturation_risk": "高（市面同类追妻/世情模式偏多，必须在职业细节或物证逻辑上做差异化）",
                "shelf_life_days": 30,
                "rescan_recommended_before": "30天内",
                "representative_samples": [b["title"] for b in normalized_records[:2]],
            },
            {
                "direction_id": f"short-opp-2",
                "emotion_core": "专业身份反差 → 隐形暗算揭露 → 认知重构",
                "opening_formula": "利用严谨行业知识（法医/金融/刑侦）作为证据链，步步逼近真相",
                "saturation_risk": "中偏低（具备真实行业质感的作品稀缺，完读与转发率高）",
                "shelf_life_days": 60,
                "rescan_recommended_before": "60天内",
                "representative_samples": [b["title"] for b in normalized_records[1:3] if len(normalized_records) > 2] or [normalized_records[0]["title"]],
            }
        ]

        report = {
            "schema": "opencontent.market-short.v1",
            "scan_id": scan_id,
            "captured_at": captured_at,
            "platforms": list(raw_platform_data.keys()),
            "total_samples": total_valid,
            "quality_reports": quality_reports,
            "top_emotions": top_emotions,
            "top_reversals": top_reversals,
            "opportunity_candidates": candidates,
            "trend_shelf_life": "短篇趋势具有高时效性，建议每月复扫验证",
        }

        # Persist as reviewable asset in Vault
        vault_path = self.kernel.vault.safe(f"OpenContent/Market/Short/{scan_id}.md")
        vault_path.parent.mkdir(parents=True, exist_ok=True)

        md_content = f"""---
scan_id: {scan_id}
type: MarketRunShort
captured_at: {captured_at}
total_samples: {total_valid}
shelf_life: 30-60天
---

# 短篇网文市场扫榜报告（{scan_id[:8]}）

- **采集时间**：{captured_at}
- **短篇平台**：{', '.join(raw_platform_data.keys())}
- **有效样本**：{total_valid}
- **特别提示**：短篇为情绪交付驱动，本报告附带趋势时效与饱和度警告。

## 一、情绪图谱与反转手法统计

- **主流情绪触发点**：{', '.join([f'{e} ({c}篇)' for e, c in top_emotions])}
- **核心反转模式**：{', '.join([f'{r} ({c}篇)' for r, c in top_reversals])}

## 二、短篇选题与情绪切口建议

"""
        for c in candidates:
            md_content += f"""### 方向：{c['emotion_core']}
- **开头前置公式**：{c['opening_formula']}
- **市场饱和风险**：{c['saturation_risk']}
- **趋势有效周期**：{c['shelf_life_days']} 天（建议在 {c['rescan_recommended_before']} 重新复扫）
- **参考样本**：{', '.join(c['representative_samples'])}

"""

        atomic(vault_path, md_content.encode("utf-8"))
        return report
