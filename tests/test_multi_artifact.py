"""Tests for Multi-Artifact support and independent critique/approval states."""
import copy
import tempfile
import unittest

from opencontent.kernel import Kernel
from opencontent.vault import Problem
from opencontent.domain import AXES
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_kernel import KernelTests, response, STATEMENT


class MultiArtifactTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.k = Kernel(self.tmp.name)
        self.p = self.k.create_project("多章节小说项目", "创作连载叙事作品", "大众读者")["oc_id"]
        # Seed basic material and knowledge
        self.m = self.k.add(self.p, "Material", "世界设定", STATEMENT, {"source": "vault:lore.md"}, self.k.vault.token())
        req_d = self.k.request(self.p, "distill", [])
        self.k.apply_result(self.p, "distill", response(req_d), req_d["token"], "fixture", "distill_run")
        req_r = self.k.request(self.p, "research", [])
        self.k.apply_result(self.p, "research", response(req_r), req_r["token"], "fixture", "research_run")

    def test_multi_artifact_creation_and_targeted_critique(self):
        token = self.k.vault.token()
        cid = [o["oc_id"] for o in self.k.read()[0].values() if o["type"] == "Claim"][0]
        
        # Create Chapter 1
        body1 = f"# 第一章 启程\n\n{STATEMENT} [[{cid}]]\n\n飞船脱离轨道，朝着未知的星系进发。第一章内容在此展开。"
        art1 = self.k.add(self.p, "Artifact", "第一章", body1, {"derived_from": [cid], "author": "fixture:writer"}, token)
        aid1 = art1["oc_id"]

        # Create Chapter 2
        token = self.k.vault.token()
        body2 = f"# 第二章 迷航\n\n{STATEMENT} [[{cid}]]\n\n引擎在穿越小行星带时出现故障。第二章内容在此展开。"
        art2 = self.k.add(self.p, "Artifact", "第二章", body2, {"derived_from": [cid], "author": "fixture:writer"}, token)
        aid2 = art2["oc_id"]

        # Calling critique without specifying target artifact raises informative Problem
        req_critique = self.k.request(self.p, "critique", [])
        r = response(req_critique)
        with self.assertRaises(Problem) as ctx:
            self.k.apply_result(self.p, "critique", r, req_critique["token"], "fixture", "critique_unspecified")
        self.assertIn("MVP automated critic requires one artifact per project", str(ctx.exception))

        # Target Chapter 1 explicitly
        r1 = copy.deepcopy(r)
        r1["artifact_id"] = aid1
        self.k.apply_result(self.p, "critique", r1, req_critique["token"], "fixture", "critique_art1")
        g1 = self.k.inspect(aid1)["gate"]
        self.assertEqual(g1["status"], "PASS")

        # Approve Chapter 1
        token = self.k.vault.token()
        self.k.decide(aid1, "accept", "主编", "第一章节奏紧凑，准予定稿", token)
        self.assertTrue(self.k.inspect(aid1)["gate"]["approved"])

        # Chapter 2 must remain NOT approved
        self.assertFalse(self.k.inspect(aid2)["gate"]["approved"])

        # Target Chapter 2 explicitly
        token = self.k.vault.token()
        r2 = copy.deepcopy(r)
        r2["artifact_id"] = aid2
        self.k.apply_result(self.p, "critique", r2, token, "fixture", "critique_art2")
        self.assertEqual(self.k.inspect(aid2)["gate"]["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
