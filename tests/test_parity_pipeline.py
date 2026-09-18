"""End-to-End Parity Tests for Narrative Pack v1:
Market Scan -> Deconstruction -> Mechanism Extraction -> Creation -> Cover Presentation.
"""
from pathlib import Path
import tempfile
import unittest

from opencontent.kernel import Kernel
from opencontent.capabilities import (
    PackRegistry,
    CapabilityRuntime,
    LongMarketAnalyzer,
    ShortMarketAnalyzer,
    StoryDeconstructor,
    CoverDirector,
    MediaGenerationAdapter,
)


class ParityPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.k = Kernel(self.tmp.name)
        self.p = self.k.create_project("科幻长篇：星渊遗孤", "创作硬科幻连载长篇", "科幻读者")["oc_id"]
        
        packs_root = Path(__file__).resolve().parent.parent / "packs"
        self.reg = PackRegistry()
        self.reg.discover([packs_root])
        self.rt = CapabilityRuntime(self.k, self.reg)

    def test_long_market_scan_parity(self):
        """Parity with Oh Story story-long-scan: multi-platform data, quality gate, opportunities."""
        raw_data = {
            "qidian": [
                {"rank": 1, "title": "宿命之环", "author": "爱潜水的乌贼", "genre": "玄幻", "words": 280, "recommendation": 500000, "intro": "诡秘世界第二部，蒸汽与神秘的再次交织。"},
                {"rank": 2, "title": "赤心巡天", "author": "情何以甚", "genre": "仙侠", "words": 420, "recommendation": 450000, "intro": "上古时代，妖族绝迹，少年拔剑起于微末。"},
                {"rank": 3, "title": "道诡异仙", "author": "狐尾的笔", "genre": "悬疑", "words": 190, "recommendation": 400000, "intro": "诡异修仙，心素迷茫，现实与幻觉交替。"},
            ],
            "fanqie": [
                {"rank": 1, "title": "十日终焉", "author": "杀虫队队员", "genre": "悬疑脑洞", "words": 210, "reads": 1200000, "intro": "齐夏在回家的路上被卷入终焉之地，必须通过层层智谋考验。"},
                {"rank": 2, "title": "我在精神病院学斩神", "author": "三九音域", "genre": "都市高武", "words": 410, "reads": 1500000, "intro": "大夏境内，神明禁行！林七夜双眼缠绕黑绸，斩杀入侵的旧日神明。"},
                {"rank": 3, "title": "我不是戏神", "author": "三九音域", "genre": "玄幻", "words": 160, "reads": 800000, "intro": "穿越大夏，以戏入道，台上演戏，台下戏神。"},
            ]
        }
        res = self.rt.execute_task({
            "schema": "opencontent.creative-task.v1",
            "project": self.p,
            "pack": "narrative",
            "profile": "serial-fiction",
            "task": "long-scan",
            "raw_data": raw_data,
        })
        self.assertEqual(res["receipt"]["status"], "SUCCEEDED")
        report = res["market_report"]
        self.assertEqual(report["total_samples"], 6)
        self.assertEqual(report["quality_reports"]["qidian"]["quality_status"], "PASS")
        self.assertEqual(len(report["opportunity_candidates"]), 3)
        # Vault asset created
        vault_md = list(self.k.vault.root.glob("OpenContent/Market/Long/*.md"))
        self.assertEqual(len(vault_md), 1)

    def test_short_market_scan_parity(self):
        """Parity with Oh Story story-short-scan: independent model, emotions, shelf-life."""
        raw_data = {
            "zhihu": [
                {"rank": 1, "title": "法医妻子的物证", "author": "冷月", "genre": "刑侦", "words": 1.2, "reads": 88000, "emotional_hook": "专业复仇 / 伦理反转", "reversal_type": "物证翻转", "intro": "作为首席法医，在解剖台前我认出了那块特殊的腕表。"},
                {"rank": 2, "title": "离婚当天我买下了他的公司", "author": "晚风", "genre": "言情", "words": 1.5, "reads": 92000, "emotional_hook": "决绝离开 / 全员打脸", "reversal_type": "身份反转", "intro": "签字离婚那天，我没有流一滴泪。"},
            ]
        }
        res = self.rt.execute_task({
            "schema": "opencontent.creative-task.v1",
            "project": self.p,
            "pack": "narrative",
            "profile": "narrative-nonfiction",
            "task": "short-scan",
            "raw_data": raw_data,
        })
        self.assertEqual(res["receipt"]["status"], "SUCCEEDED")
        report = res["market_report"]
        self.assertEqual(report["total_samples"], 2)
        self.assertIn("30天内", report["opportunity_candidates"][0]["rescan_recommended_before"])
        vault_md = list(self.k.vault.root.glob("OpenContent/Market/Short/*.md"))
        self.assertEqual(len(vault_md), 1)

    def test_long_and_short_deconstruction_parity(self):
        """Parity with Oh Story story-long-analyze & story-short-analyze: 3-tier assets."""
        # Long deconstruct
        chapters = [
            {"title": "第一章 醒来", "body": "苏晨从冷冻休眠舱中缓缓苏醒，刺耳的猩红警报声响彻整个第七科研层。全息环境扫描显示周围生命信号为零，人工重力系统即将崩溃，深空飞船正在向未知引力源坠落。"},
            {"title": "第二章 故障", "body": "主控室应急合金闸门已经彻底锁死，想要通往核心逃生舱，必须手动输入首席安全官的生物指纹与密钥。但在残留日志中，安全官早在三百年前的第一次接触战中牺牲。"},
            {"title": "第三章 绝壁", "body": "在布满尘埃的废弃通信终端深处，苏晨发现了留给幸存者的最后一段高度加密遗言：真正的灾难源头不在太阳系，而在深空折跃门背后，所有星图坐标已被篡改。"}
        ]
        res_long = self.rt.execute_task({
            "schema": "opencontent.creative-task.v1",
            "project": self.p,
            "pack": "narrative",
            "profile": "general-fiction",
            "task": "long-analyze",
            "title": "深空沉眠者",
            "chapters": chapters,
            "platform": "qidian"
        })
        self.assertEqual(res_long["receipt"]["status"], "SUCCEEDED")
        self.assertTrue(len(res_long["mechanisms"]) >= 2)
        # Vault asset created
        self.assertTrue((self.k.vault.root / "OpenContent/Deconstruction/深空沉眠者/拆文报告.md").is_file())
        self.assertTrue(len(list((self.k.vault.root / "OpenContent/Deconstruction/深空沉眠者/机制卡片").glob("*.md"))) >= 2)

        # Short deconstruct
        short_text = """我站在重症监护室门外，婆婆正带着全家族的亲戚尖叫着让我把婚前个人房产过户给小叔子抵还赌债。
她冷笑着威胁说如果不答应就让我身败名裂。然而她不知道的是，早在三个小时之前，我已经去公证处办妥了婚前个人财产公证，并调取了过去三年来全部银行转账流水记录与报警回执。
在后续的法庭调解现场，对方所有的伪善与谎言，在这一份份盖着红色印章的第三方客观存证面前，彻底溃不成军、不攻自破。"""
        res_short = self.rt.execute_task({
            "schema": "opencontent.creative-task.v1",
            "project": self.p,
            "pack": "narrative",
            "profile": "narrative-nonfiction",
            "task": "short-analyze",
            "title": "婚前物证",
            "text": short_text,
            "platform": "zhihu"
        })
        self.assertEqual(res_short["receipt"]["status"], "SUCCEEDED")
        self.assertTrue((self.k.vault.root / "OpenContent/Deconstruction/婚前物证/情节节点.md").is_file())
        self.assertTrue((self.k.vault.root / "OpenContent/Deconstruction/婚前物证/写作手法.md").is_file())
        self.assertTrue((self.k.vault.root / "OpenContent/Deconstruction/婚前物证/拆文报告.md").is_file())

    def test_cover_director_and_generation_parity(self):
        """Parity with Oh Story story-cover: genre semantics, platform sizing, multi-version."""
        res_cover = self.rt.execute_task({
            "schema": "opencontent.creative-task.v1",
            "project": self.p,
            "pack": "narrative",
            "profile": "serial-fiction",
            "task": "cover",
            "title": "星渊遗孤",
            "genre": "科幻",
            "platform": "fanqie",
        })
        self.assertEqual(res_cover["receipt"]["status"], "SUCCEEDED")
        spec = res_cover["spec"]
        self.assertEqual(spec["dimensions"]["ratio"], "3:4")
        self.assertIn("hard sci-fi", spec["image_generation_prompt"])
        candidates = res_cover["candidates"]
        self.assertEqual(len(candidates), 2)
        # Verify physical image existence
        for c in candidates:
            img_path = self.k.vault.root / c["path"]
            self.assertTrue(img_path.is_file())
            self.assertTrue(img_path.stat().st_size > 50)


if __name__ == "__main__":
    unittest.main()
