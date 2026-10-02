"""Cover production boundaries. All image providers here are explicit test doubles."""
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

from opencontent.capabilities.media import (
    MAX_IMAGE_BYTES, MediaGenerationAdapter, validate_image_bytes,
)
from opencontent.kernel import Kernel
from opencontent.vault import Problem, digest


def fixture_image(size=(600, 900), variant=0, image_format="PNG"):
    image = Image.new("RGB", size, (10 + variant * 20, 20, 60))
    ImageDraw.Draw(image).rectangle((size[0] // 4, size[1] // 4,
                                    size[0] * 3 // 4, size[1] * 3 // 4),
                                   fill=(180, 90 + variant * 20, 130))
    output = io.BytesIO()
    image.save(output, image_format)
    return output.getvalue()


class ImageFixtureProvider:
    """Emulates CLI artifacts only; never evidence of live image generation."""
    def __init__(self, action=None, image_generation=True):
        self.action = action
        self.image_generation = image_generation
        self.calls = []

    def capabilities(self):
        return {"image_generation": self.image_generation, "fixture": True}

    def run(self, request, workspace, event):
        workspace = Path(workspace)
        self.calls.append((request, workspace, event))
        if self.action:
            return self.action(request, workspace, event)
        dimensions = request["spec"]["dimensions"]
        images = []
        for i in range(request["count"]):
            filename = f"image-{i}.png"
            (workspace / filename).write_bytes(fixture_image(
                (dimensions["upload_width"], dimensions["upload_height"]), i))
            images.append({"path": filename, "alt": f"Test cover {i}",
                           "generation": {"tool": "test-fixture", "model": "test-only"}})
        return {"images": images, "error": None}


class CoverGenerationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.kernel = Kernel(self.tmp.name)
        self.pid = self.kernel.create_project("Cover test", "Test scope", "Readers")["oc_id"]
        self.provider = ImageFixtureProvider()
        self.adapter = MediaGenerationAdapter(self.kernel, {"fixture": self.provider})
        self.cover_dir = self.kernel.vault.safe(f"Attachments/OpenContent/{self.pid}/covers")

    def generate(self, **kwargs):
        return self.adapter.generate_cover_candidates(self.pid, "Cover test", **kwargs)

    def output_action(self, images, files):
        def action(request, workspace, event):
            for filename, content in files.items():
                path = workspace / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            return {"images": images}
        return action

    @staticmethod
    def record(path="output.png", **extra):
        return {"path": path, "alt": "Cover art", "generation": {"tool": "test-only"}, **extra}

    def test_decoded_assets_record_evidence_and_use_provider_stage(self):
        result = self.generate(instruction="Leave title room", premise="A lunar station", run_id="verified-run")
        request, workspace, _ = self.provider.calls[0]
        self.assertEqual(request["stage"], "illustrate")
        self.assertEqual(request["instruction"], "Leave title room")
        self.assertEqual(request["spec"]["premise"], "A lunar station")
        self.assertEqual(result["image_status"], "FIXTURE_GENERATED")
        self.assertEqual(result["mode"], "fixture")
        self.assertTrue(result["evidence"]["test_only"])
        self.assertIn("TEST FIXTURE ONLY", result["evidence"]["generation_attestation"])
        self.assertEqual(result["provider"], "fixture")
        self.assertEqual(result["evidence"]["request_hash"], digest(request))
        self.assertEqual(result["evidence"]["response_hash"], digest((workspace / "provider-result.json").read_bytes()))
        self.assertEqual(result["evidence"]["author_review"], "PENDING")
        self.assertEqual(len(result["candidates"]), 2)
        for candidate in result["candidates"]:
            actual = (self.kernel.vault.root / candidate["path"]).read_bytes()
            self.assertEqual(candidate["file_hash"], digest(actual))
            self.assertEqual(candidate["image"]["width"], 600)
            self.assertEqual(candidate["image"]["height"], 900)
            self.assertTrue(candidate["image"]["decoded"])
            self.assertEqual(candidate["provenance"]["run_id"], "verified-run")
            self.assertEqual(candidate["provenance"]["generation"]["tool"], "test-fixture")
        self.assertEqual(json.loads((workspace / "receipt.json").read_text())["status"], "SUCCEEDED")
        self.assertEqual(json.loads((workspace / "receipt.json").read_text())["execution_mode"], "fixture")
        self.assertTrue((self.cover_dir / "cover-specs-verified-run.json").is_file())

    def test_no_provider_is_blocked_and_does_not_create_cover(self):
        self.adapter = MediaGenerationAdapter(self.kernel)
        with self.assertRaisesRegex(Problem, "No configured cover provider") as context:
            self.generate(run_id="no-provider")
        self.assertEqual(context.exception.status, 503)
        receipt = json.loads(self.kernel.vault.safe(".opencontent/runs/no-provider/media/receipt.json").read_text())
        self.assertEqual(receipt["status"], "BLOCKED")
        self.assertFalse(self.cover_dir.exists())

    def test_explicit_unknown_provider_never_falls_back(self):
        with self.assertRaisesRegex(Problem, "No configured cover provider"):
            self.generate(provider_name="nonexistent")
        self.assertFalse(self.provider.calls)

    def test_unsupported_provider_never_runs(self):
        for unsupported in (False, None, 1, "no", "fixture"):
            with self.subTest(unsupported=unsupported):
                self.provider.image_generation = unsupported
                with self.assertRaisesRegex(Problem, "does not support image generation"):
                    self.generate()
        self.assertFalse(self.provider.calls)

    def test_runtime_dependent_provider_attempts_real_generation(self):
        self.provider.image_generation = "runtime-dependent"
        self.assertEqual(self.generate(count=1)["image_status"], "FIXTURE_GENERATED")

    def test_configured_mapping_can_be_populated_after_adapter_initialization(self):
        providers = {}
        self.adapter = MediaGenerationAdapter(self.kernel, providers)
        providers["added"] = self.provider
        self.assertEqual(self.generate(count=1)["provider"], "added")

    def test_brief_only_empty_and_failed_responses_never_succeed(self):
        cases = [None, [], {}, {"images": []}, {"images": [], "illustrations": [{"prompt": "A book"}]},
                 {"images": [], "error": "Image tool unavailable"}]
        for output in cases:
            with self.subTest(output=output):
                self.provider.action = lambda request, workspace, event: output
                with self.assertRaises(Problem):
                    self.generate()
                self.assertFalse(self.cover_dir.exists())

    def test_invalid_second_output_does_not_persist_first_candidate(self):
        images = [self.record("good.png"), self.record("bad.png")]
        self.provider.action = self.output_action(images, {"good.png": fixture_image(), "bad.png": b"\x89PNG\r\n\x1a\ninvalid"})
        with self.assertRaisesRegex(Problem, "decoding"):
            self.generate()
        self.assertFalse(self.cover_dir.exists())

    def test_partial_candidate_set_fails_without_persistence(self):
        self.provider.action = self.output_action([self.record()], {"output.png": fixture_image()})
        with self.assertRaisesRegex(Problem, "exactly 2"):
            self.generate()
        self.assertFalse(self.cover_dir.exists())

    def test_tiny_wrong_ratio_corrupt_oversized_and_blank_images_fail(self):
        blank = io.BytesIO()
        Image.new("RGB", (600, 900), "white").save(blank, "PNG")
        transparent = io.BytesIO()
        Image.new("RGBA", (600, 900), (0, 0, 0, 0)).save(transparent, "PNG")
        cases = [(fixture_image((1, 1)), "dimensions"),
                 (fixture_image((60, 90)), "minimum dimensions"),
                 (fixture_image((900, 900)), "aspect ratio"),
                 (fixture_image()[:100], "decoding"),
                 (fixture_image((8193, 2)), "pixel limit"),
                 (blank.getvalue(), "placeholder"), (transparent.getvalue(), "transparent")]
        for image, reason in cases:
            with self.subTest(reason=reason):
                self.provider.action = self.output_action([self.record()], {"output.png": image})
                with self.assertRaisesRegex(Problem, reason):
                    self.generate(count=1)
                self.assertFalse(self.cover_dir.exists())

    def test_jpeg_is_decoded_and_saved_with_real_extension(self):
        self.provider.action = self.output_action([self.record("image.bin")], {"image.bin": fixture_image(image_format="JPEG")})
        candidate = self.generate(count=1)["candidates"][0]
        self.assertTrue(candidate["path"].endswith(".jpg"))
        self.assertEqual(candidate["image"]["format"], "JPEG")

    def test_gif_is_not_a_supported_cover_format(self):
        with self.assertRaisesRegex(Problem, "PNG or JPEG"):
            validate_image_bytes(fixture_image(image_format="GIF"))

    def test_duplicate_pixels_fail_even_with_different_png_compression(self):
        original = fixture_image()
        alternate = io.BytesIO()
        with Image.open(io.BytesIO(original)) as image:
            image.save(alternate, "PNG", compress_level=0)
        self.assertNotEqual(original, alternate.getvalue())
        self.provider.action = self.output_action([self.record("a.png"), self.record("b.png")],
                                                 {"a.png": original, "b.png": alternate.getvalue()})
        with self.assertRaisesRegex(Problem, "duplicate"):
            self.generate()
        self.assertFalse(self.cover_dir.exists())

    def test_invalid_count_and_identifiers_fail_before_provider_or_workspace(self):
        for count in (0, -1, 5, True, "2", 1.0):
            with self.subTest(count=count):
                with self.assertRaisesRegex(Problem, "count"):
                    self.generate(count=count)
        for kwargs in ({"run_id": "../escape"}, {"run_id": "/tmp/run"}, {"platform": "unknown"},
                       {"instruction": None}, {"provider_name": ""}):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(Problem):
                    self.generate(**kwargs)
        with self.assertRaisesRegex(Problem, "project ID"):
            self.adapter.generate_cover_candidates("../escape", "Cover")
        self.assertFalse(self.provider.calls)
        self.assertFalse(self.kernel.vault.safe(".opencontent/runs").exists())

    def test_image_paths_must_be_workspace_relative_on_both_operating_systems(self):
        for path in ("../image.png", "/tmp/image.png", "C:/image.png", "C:relative.png",
                     "C:\\image.png", "\\\\server\\share\\a.png", "dir\\..\\image.png", "a\x00.png"):
            with self.subTest(path=path):
                self.provider.action = lambda request, workspace, event: {"images": [self.record(path)]}
                with self.assertRaisesRegex(Problem, "path"):
                    self.generate(count=1)
        self.assertFalse(self.cover_dir.exists())

    @unittest.skipUnless(hasattr(os, "symlink"), "Symlinks unavailable")
    def test_linked_images_and_lexical_ancestor_links_fail(self):
        source = self.kernel.vault.safe("existing.png")
        source.write_bytes(fixture_image())
        def action(request, workspace, event):
            (workspace / "linked.png").symlink_to(source)
            return {"images": [self.record("linked.png")]}
        self.provider.action = action
        with self.assertRaisesRegex(Problem, "Linked"):
            self.generate(count=1)
        def action(request, workspace, event):
            (workspace / "real").mkdir()
            (workspace / "real/image.png").write_bytes(fixture_image())
            (workspace / "linked").symlink_to(workspace / "real", target_is_directory=True)
            return {"images": [self.record("linked/image.png")]}
        self.provider.action = action
        with self.assertRaisesRegex(Problem, "Linked"):
            self.generate(count=1)
        self.assertFalse(self.cover_dir.exists())

    @unittest.skipUnless(hasattr(os, "link"), "Hardlinks unavailable")
    def test_existing_hardlinked_vault_image_is_not_accepted(self):
        source = self.kernel.vault.safe("existing.png")
        source.write_bytes(fixture_image())
        def action(request, workspace, event):
            os.link(source, workspace / "linked.png")
            return {"images": [self.record("linked.png")]}
        self.provider.action = action
        with self.assertRaisesRegex(Problem, "linked"):
            self.generate(count=1)
        self.assertFalse(self.cover_dir.exists())

    def test_oversized_file_rejected_without_reading_it(self):
        def action(request, workspace, event):
            with (workspace / "huge.png").open("wb") as handle:
                handle.truncate(MAX_IMAGE_BYTES + 1)
            return {"images": [self.record("huge.png")]}
        self.provider.action = action
        with self.assertRaisesRegex(Problem, "20 MB"):
            self.generate(count=1)
        self.assertFalse(self.cover_dir.exists())

    def test_missing_image_or_generation_evidence_fails(self):
        for record in (self.record("missing.png"), self.record(generation={}),
                       self.record(generation={"tool": "test", "model": 5}), self.record(alt="")):
            with self.subTest(record=record):
                self.provider.action = self.output_action([record], {"output.png": fixture_image()})
                with self.assertRaises(Problem):
                    self.generate(count=1)
        self.assertFalse(self.cover_dir.exists())

    def test_nonexistent_output_directory_and_run_reuse_fail(self):
        self.generate(count=1, run_id="same-run")
        self.assertEqual(len(self.provider.calls), 1)
        with self.assertRaisesRegex(Problem, "already exists"):
            self.generate(count=1, run_id="same-run")
        self.assertEqual(len(self.provider.calls), 1)

    def test_version_gaps_and_jpeg_versions_are_not_overwritten(self):
        self.cover_dir.mkdir(parents=True)
        (self.cover_dir / "cover-v2.png").write_bytes(b"old png")
        (self.cover_dir / "cover-v9.jpg").write_bytes(b"old jpg")
        first = self.generate(run_id="first")
        second = self.generate(count=1, run_id="second")
        self.assertEqual([c["version"] for c in first["candidates"]], [10, 11])
        self.assertEqual(second["candidates"][0]["version"], 12)
        self.assertEqual((self.cover_dir / "cover-v2.png").read_bytes(), b"old png")
        self.assertEqual((self.cover_dir / "cover-v9.jpg").read_bytes(), b"old jpg")
        self.assertEqual(json.loads((self.cover_dir / "cover-specs-first.json").read_text())["run_id"], "first")
        self.assertEqual(json.loads((self.cover_dir / "cover-specs.json").read_text())["run_id"], "second")

    def test_provider_failure_records_failed_receipt(self):
        self.provider.action = lambda request, workspace, event: (_ for _ in ()).throw(RuntimeError("CLI stopped"))
        with self.assertRaisesRegex(Problem, "CLI stopped"):
            self.generate(run_id="failed-cli")
        receipt = json.loads(self.kernel.vault.safe(".opencontent/runs/failed-cli/media/receipt.json").read_text())
        self.assertEqual(receipt["status"], "FAILED")
        self.assertFalse(self.cover_dir.exists())

    def test_cancel_before_or_after_provider_never_persists_cover(self):
        event = threading.Event()
        event.set()
        with self.assertRaisesRegex(Problem, "cancelled"):
            self.generate(cancel_event=event)
        self.assertFalse(self.provider.calls)
        event.clear()
        def action(request, workspace, event):
            event.set()
            return {"images": []}
        self.provider.action = action
        with self.assertRaisesRegex(Problem, "cancelled"):
            self.generate(cancel_event=event)
        self.assertFalse(self.cover_dir.exists())

    def test_missing_decoder_is_actionable(self):
        raw = fixture_image()
        with patch.dict("sys.modules", {"PIL": None}):
            with self.assertRaisesRegex(Problem, "install requirements.txt") as context:
                validate_image_bytes(raw)
        self.assertEqual(context.exception.status, 503)


if __name__ == "__main__":
    unittest.main()
