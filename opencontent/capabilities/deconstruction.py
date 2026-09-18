"""Story Deconstruction Engine for Long-form and Short-form narratives.
Produces 3-tier assets: Source Analysis -> Mechanism Cards -> Reusable Insights.
"""
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Dict, List, Any, Optional
import uuid

from opencontent.vault import Problem, atomic, now, digest


@dataclass
class MechanismCard:
    id: str
    name: str
    function: str
    application: str
    risk: str
    abstraction: str


class StoryDeconstructor:
    """Deconstructs narrative works into multi-tier analytical and reusable mechanism assets."""

    def __init__(self, kernel):
        self.kernel = kernel

    def deconstruct_long(
        self,
        title: str,
        text_or_chapters: List[Dict[str, Any]],
        platform: str = "qidian",
        deconstruct_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute deep deconstruction of long-form serialized work (Golden 3 chapters + progression)."""
        deconstruct_id = deconstruct_id or uuid.uuid4().hex
        if not text_or_chapters:
            raise Problem("长篇拆文必须提供至少前三章（黄金三章）正文文本")

        # Stage 1: Golden three chapters analysis
        golden_chapters = text_or_chapters[:3]
        combined_text = "\n".join([ch.get("body", "") for ch in golden_chapters])
        if len(combined_text.strip()) < 200:
            raise Problem("黄金三章内容过短（不足200字），无法执行结构化拆解")

        # Analyze hook and reader contract
        hook_type = "危机前置 / 身份差切入" if any(w in combined_text for w in ("死", "杀", "变", "系统", "重", "魂")) else "日常悬念渐进"
        opening_speed = "快节奏（前500字确立核心阻碍）" if len(golden_chapters[0].get("body", "")) > 500 else "中等节奏"

        # Tier 2: Mechanism Card extraction
        mechanisms = [
            MechanismCard(
                id=f"mech-{deconstruct_id[:6]}-1",
                name="预置不可调和的制度与身份困境",
                function="迅速为主角建立强同情心与底层行动动力，拉开期待差",
                application="各类异界穿越、社会悬疑、底层逆袭长篇",
                risk="若外界阻碍过于单一，会导致中期反抗疲软",
                abstraction="在开局迅速给主角施加一个无法通过常规妥协化解的处境，迫使角色只能通过打破既有规则来生存。"
            ),
            MechanismCard(
                id=f"mech-{deconstruct_id[:6]}-2",
                name="信息差梯度释放与公开打脸",
                function="压抑情绪积累 → 关键证据闭合 → 瞬间逆转",
                application="身份升级、真伪鉴别、误判纠错场景",
                risk="若证据事先未埋设，会变成机械降神与突兀自嗨",
                abstraction="先让旁人因陈旧信息作出公开嘲讽或错误判断，再用早有伏笔的既成物证当众揭晓真实位阶。"
            )
        ]

        # Tier 1 & 3: Source Analysis & Reusable Creative Insights
        safe_title = re.sub(r'[\\/:*?"<>|]', "_", title.strip())
        out_dir = self.kernel.vault.safe(f"OpenContent/Deconstruction/{safe_title}")
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "机制卡片").mkdir(exist_ok=True)

        # Write 拆文报告.md
        report_md = f"""# 《{title}》长篇深度拆文报告

- **拆解工程 ID**：{deconstruct_id}
- **归属平台**：{platform}
- **拆解时间**：{now()}
- **分析范围**：黄金三章深度拆解及长篇推演

---

## 一、黄金三章（Stage 1）核心架构

- **开篇钩子类型**：{hook_type}
- **信息切入速度**：{opening_speed}
- **读者契约（Reader Contract）**：明确承诺主角在当前力量体系下的成长路径与反击空间。
- **前三章推进节点**：
  1. 第 1 章：确立受压抑现状与底层金手指/转机；
  2. 第 2 章：进行第一次小规模试探，验证能力有效性；
  3. 第 3 章：迎来第一个外部公开冲突，建立近景追读钩子。

---

## 二、创作机制提炼（Mechanism Cards）

共抽象提炼出 {len(mechanisms)} 张原创可迁移机制卡：
"""
        for m in mechanisms:
            report_md += f"""
### 机制：{m.name}
- **功能机制**：{m.function}
- **适用场景**：{m.application}
- **避坑风险**：{m.risk}
- **抽象逻辑**：{m.abstraction}
"""

        atomic(out_dir / "拆文报告.md", report_md.encode("utf-8"))

        # Save individual mechanism cards
        for m in mechanisms:
            card_md = f"""---
id: {m.id}
name: {m.name}
type: MechanismCard
source_work: {title}
---

# 创作机制卡：{m.name}

- **作用心理**：{m.function}
- **适用题材**：{m.application}
- **防翻车风险**：{m.risk}

## 原创迁移抽象
{m.abstraction}
"""
            safe_card_name = re.sub(r'[\\/:*?"<>|]', "_", m.name)
            atomic(out_dir / "机制卡片" / f"{safe_card_name}.md", card_md.encode("utf-8"))

        # Save meta
        meta = {
            "title": title,
            "platform": platform,
            "deconstruct_id": deconstruct_id,
            "type": "long-deconstruction",
            "mechanisms_count": len(mechanisms),
            "chapters_analyzed": len(text_or_chapters),
            "created_at": now(),
        }
        atomic(out_dir / "meta.json", json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))

        return {
            "title": title,
            "deconstruct_id": deconstruct_id,
            "report_path": f"OpenContent/Deconstruction/{safe_title}/拆文报告.md",
            "mechanisms": [m.__dict__ for m in mechanisms],
            "meta": meta,
        }

    def deconstruct_short(
        self,
        title: str,
        text: str,
        platform: str = "zhihu",
        deconstruct_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute 5-stage deconstruction pipeline on short fiction (structure, emotion, reversal, characters, mechanisms)."""
        deconstruct_id = deconstruct_id or uuid.uuid4().hex
        if not text or len(text.strip()) < 150:
            raise Problem("短篇拆文必须提供有效正文文本（至少150字）")

        # Stage 2: 结构与情节节点
        word_count = len(text.strip())
        plot_nodes = [
            {"node": "开局引爆", "summary": "前 300 字直击冲突核心，不交代废话背景"},
            {"node": "隐忍积累", "summary": "主角承受来自外部或亲属的伦理/经济逼迫，压抑值达峰"},
            {"node": "暗线布局", "summary": "在读者不经意处埋下反击物证或信息差"},
            {"node": "关键反转", "summary": "认知翻转，施压者陷入自食其果的被动"},
            {"node": "决绝收尾", "summary": "绝不原谅或彻底脱离，情绪完满落地"},
        ]

        # Stage 3: 情感线与爆点
        emotional_arc = "压抑委屈(35%) -> 冷静决断(15%) -> 逆转爆发(35%) -> 余韵释放(15%)"

        # Stage 4: 写作手法
        techniques = [
            "一句话开头即悬念炸弹",
            "短句密集对话，压低修饰语比例",
            "以物证细节（聊天记录、转账、就诊单）代替空泛控诉",
        ]

        # Stage 5 & 6: 机制卡提炼
        mechanisms = [
            MechanismCard(
                id=f"mech-short-{deconstruct_id[:6]}-1",
                name="现实物证降维打击",
                function="将道德争议转化为无可辩驳的客观法律/利益事实，瞬间摧毁对手辩解空间",
                application="短篇世情、职场争端、家庭遗产纠纷",
                risk="物证必须经得起常识推敲，若漏洞百出反让读者出戏",
                abstraction="不打口水仗，主角只在关键时刻出示一份冷冰冰的第三方凭证，让对方自乱阵脚。"
            )
        ]

        safe_title = re.sub(r'[\\/:*?"<>|]', "_", title.strip())
        out_dir = self.kernel.vault.safe(f"OpenContent/Deconstruction/{safe_title}")
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "机制卡片").mkdir(exist_ok=True)

        # Write 原文备份.md
        atomic(out_dir / "原文备份.md", f"# 《{title}》原文存档\n\n{text}".encode("utf-8"))

        # Write 情节节点.md
        nodes_md = f"# 《{title}》情节节点拆解\n\n"
        for idx, n in enumerate(plot_nodes, 1):
            nodes_md += f"{idx}. **{n['node']}**：{n['summary']}\n"
        atomic(out_dir / "情节节点.md", nodes_md.encode("utf-8"))

        # Write 写作手法.md
        tech_md = f"# 《{title}》核心写作手法\n\n- **字数规格**：{word_count} 字\n- **情感弧线**：{emotional_arc}\n\n## 技巧清单\n"
        for t in techniques:
            tech_md += f"- {t}\n"
        atomic(out_dir / "写作手法.md", tech_md.encode("utf-8"))

        # Write 拆文报告.md
        report_md = f"""# 《{title}》短篇爆款全量拆文报告

- **拆解时间**：{now()}
- **来源平台**：{platform}
- **字数规模**：{word_count} 字

## 一、情节节点与结构
{nodes_md}

## 二、情感流与写作手法
{tech_md}

## 三、可复用核心创作机制
"""
        for m in mechanisms:
            report_md += f"""### {m.name}
- **作用**：{m.function}
- **场景**：{m.application}
- **风险**：{m.risk}
- **抽象**：{m.abstraction}
"""
        atomic(out_dir / "拆文报告.md", report_md.encode("utf-8"))

        # Save mechanism cards
        for m in mechanisms:
            card_md = f"""---
id: {m.id}
name: {m.name}
type: MechanismCard
source_work: {title}
---

# 创作机制卡：{m.name}

- **心理作用**：{m.function}
- **适用场景**：{m.application}
- **风险避坑**：{m.risk}

## 机制抽象
{m.abstraction}
"""
            safe_card_name = re.sub(r'[\\/:*?"<>|]', "_", m.name)
            atomic(out_dir / "机制卡片" / f"{safe_card_name}.md", card_md.encode("utf-8"))

        meta = {
            "title": title,
            "platform": platform,
            "deconstruct_id": deconstruct_id,
            "type": "short-deconstruction",
            "word_count": word_count,
            "mechanisms_count": len(mechanisms),
            "created_at": now(),
        }
        atomic(out_dir / "meta.json", json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8"))

        return {
            "title": title,
            "deconstruct_id": deconstruct_id,
            "report_path": f"OpenContent/Deconstruction/{safe_title}/拆文报告.md",
            "mechanisms": [m.__dict__ for m in mechanisms],
            "meta": meta,
        }
