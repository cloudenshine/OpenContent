"""Unit and contract tests for Capability Pack architecture."""
from pathlib import Path
import tempfile
import unittest
import yaml

from opencontent.vault import Problem
from opencontent.capabilities import (
    PACK_SCHEMA_V1,
    TASK_SCHEMA_V1,
    STATE_DELTA_SCHEMA_V1,
    PackManifest,
    validate_manifest,
    load_manifest,
    PackRegistry,
    TaskRouter,
    ContextAssembler,
    validate_workspace_path,
    validate_state_delta,
    validate_candidate_output,
)
from packs.narrative.validators.continuity import check_continuity


class CapabilityPackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_narrative_pack_manifest_validates_cleanly(self):
        narrative_dir = Path(__file__).resolve().parent.parent / "packs" / "narrative"
        manifest = load_manifest(narrative_dir)
        self.assertEqual(manifest.id, "narrative")
        self.assertEqual(manifest.version, "1.0.0")
        self.assertIn("general-fiction", manifest.profiles)
        self.assertIn("serial-fiction", manifest.profiles)
        self.assertIn("narrative-nonfiction", manifest.profiles)
        self.assertEqual(set(manifest.tasks), {"long-scan", "short-scan", "long-analyze", "short-analyze", "plan", "write", "continue", "revise", "critique", "cover"})
        self.assertEqual(manifest.runtime["workspace_write"], "required")

    def test_manifest_validation_rejects_invalid_schema_or_escaping_paths(self):
        bad_dir = self.root / "bad_pack"
        bad_dir.mkdir()
        (bad_dir / "pack.yaml").write_text(yaml.dump({
            "schema": "wrong.schema",
            "id": "bad",
            "version": "1.0.0",
            "name": "Bad",
            "profiles": ["p1"],
            "tasks": ["write"],
            "runtime": {"workspace_write": "required"},
            "workflows": {"write": "../../escape.yaml"},
            "outputs": ["artifact"]
        }), encoding="utf-8")

        with self.assertRaises(Problem) as ctx:
            load_manifest(bad_dir)
        self.assertIn("Unsupported capability pack schema", str(ctx.exception))

    def test_registry_discovery_and_duplicate_rejection(self):
        packs_root = Path(__file__).resolve().parent.parent / "packs"
        reg = PackRegistry()
        reg.discover([packs_root])
        self.assertIn("narrative", [c["id"] for c in reg.list_capabilities()])

        # Duplicate registration raises Problem
        manifest = reg.get_pack("narrative")
        with self.assertRaises(Problem) as ctx:
            reg.register(manifest)
        self.assertIn("Duplicate capability pack id", str(ctx.exception))

    def test_task_router_resolves_pack_profile_and_workflow(self):
        packs_root = Path(__file__).resolve().parent.parent / "packs"
        reg = PackRegistry()
        reg.discover([packs_root])
        router = TaskRouter()

        routed = router.route({
            "schema": TASK_SCHEMA_V1,
            "project": "proj_1",
            "pack": "narrative",
            "profile": "serial-fiction",
            "task": "continue",
            "instruction": "Continue chapter 2",
        }, reg)

        self.assertEqual(routed["task"], "continue")
        self.assertEqual(routed["pack"].id, "narrative")
        self.assertEqual(routed["profile_id"], "serial-fiction")
        self.assertEqual(routed["workflow"]["id"], "continue")

    def test_context_assembler_prioritizes_p0_and_filters_characters(self):
        assembler = ContextAssembler()
        project = {
            "oc_id": "p_test",
            "goal": "Write a sci-fi serial",
            "audience": "Sci-fi readers",
            "thesis": "Technology reshapes memory",
        }
        artifact = {
            "oc_id": "art_1",
            "title": "Chapter 1",
            "body": "Captain Miller stared at the nebula.",
        }
        state_data = {
            "characters": [
                {"id": "c1", "name": "Miller", "status": "alive", "active": True},
                {"id": "c2", "name": "IrrelevantPerson", "status": "alive", "active": False},
            ],
            "timeline": [{"event": "Launch", "timestamp": "Day 1"}],
            "open_threads": [{"id": "t1", "description": "Nebula mystery", "urgent": True}],
        }

        pkg = assembler.assemble(
            task="continue",
            instruction="Miller prepares to land on the asteroid.",
            project=project,
            artifact=artifact,
            state_data=state_data,
        )

        self.assertEqual(pkg["task"], "continue")
        self.assertEqual(pkg["intent"]["goal"], "Write a sci-fi serial")
        # Miller is included because mentioned in prompt & artifact
        char_names = [c["name"] for c in pkg["relevant_state"]["characters"]]
        self.assertIn("Miller", char_names)
        self.assertNotIn("IrrelevantPerson", char_names)
        # Provenance records exist
        self.assertTrue(any(p["target"] == "intent" and p["priority"] == "P0" for p in pkg["provenance"]))

    def test_workspace_security_rejects_path_traversal(self):
        ws = self.root / "workspace"
        ws.mkdir()
        # Safe relative path works
        valid = validate_workspace_path("candidate/output.md", ws)
        self.assertEqual(valid, (ws / "candidate/output.md").resolve())

        # Traversal escapes are rejected
        with self.assertRaises(Problem) as ctx:
            validate_workspace_path("../outside.txt", ws)
        self.assertIn("Path escapes task workspace", str(ctx.exception))

        # Absolute paths escaping workspace are rejected
        with self.assertRaises(Problem) as ctx:
            validate_workspace_path("C:/Windows/system.ini", ws)
        self.assertIn("Path escapes task workspace", str(ctx.exception))

    def test_state_delta_and_continuity_validators(self):
        # Valid delta
        valid_delta = {
            "schema": STATE_DELTA_SCHEMA_V1,
            "characters": [{"name": "Miller", "status": "injured", "origin": "observed_from_output"}],
            "timeline": [{"event": "Crash landing", "origin": "observed_from_output"}],
            "open_threads": [{"description": "Repair engine", "origin": "agent_inference"}],
            "relationships": [],
            "world": [],
            "resolved_threads": [],
            "new_proposals": [],
        }
        self.assertEqual(validate_state_delta(valid_delta), valid_delta)

        # Invalid origin rejected
        bad_delta = {
            "schema": STATE_DELTA_SCHEMA_V1,
            "characters": [{"name": "Miller", "origin": "hallucination"}],
            "timeline": [], "open_threads": [], "relationships": [], "world": [],
            "resolved_threads": [], "new_proposals": []
        }
        with self.assertRaises(Problem):
            validate_state_delta(bad_delta)

        # Continuity validator flags deceased character in active scene
        issues = check_continuity(
            draft_body="Completely silent, the station sat empty. Suddenly Captain Davis walked into the room and fired his weapon.",
            established_state={"characters": [{"name": "Davis", "status": "deceased"}]},
            profile_rules={},
        )
        self.assertTrue(any("Deceased character 'Davis' appears" in i for i in issues))


if __name__ == "__main__":
    unittest.main()
