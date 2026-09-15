# 2026-09-13 runtime acceptance

## Verified scope

Installed payload in `F:\Obsidian_vault`; settings preservation and kernel hashes checked on deployment. Offline environment checks passed. The deployed payload was also installed into `.ux-validation/vault` and loaded in an isolated Obsidian 1.13.7 instance.

- Full automated suite previously passed: Node tests, syntax/compile checks, 107 Python tests.
- Additional live-safe installation regression passed (6 installation tests total): separate runtime, old runtime preserved, BOM settings accepted, user selection retained.
- 11 native renderer checks passed: navigation, current note, CLI availability, retained inputs, one article per click, one captured note, fresh token, generation failure recovery, shared composer, narrow panel overflow.
- Fixed test synchronization: wait for asynchronous composer creation before asserting its presence. No acceptance assertion removed.
- Real Codex production job `481b96c80e63424d9d459d0e7a3c0e9d` completed all four stages, with a passing review.
- Real revision job `82e93f875bb34a62b868caeb76df09be` produced a preview. UI adoption saved the example and removed reader-facing internal terminology.
- Adoption invalidated the old review (BLOCKED observed), then automatically started review job `e7b24ba527bb4fd38f7076d7645aab9c`, which succeeded with all five axes PASS.
- Cancellation job `598d69268b324c2ab5a35218d2da8f3f` reached CANCELLED; article preserved.
- Disable/enable plugin reload preserved the revised body and PASS review. Approval remains false, as expected.

## Evidence objects

Project: `1f8b0b96b05c489f92ba99e956edaa60`.
Artifact: `008bc3cc7b084da9980dff1f0f4297a7`.
Latest review: `c3393dd2e5ad46dd9925586f61b20ad6`.
Files remain under `.ux-validation/vault/OpenContent` for inspection.

## Limits

This verifies local writing, revision, review, recovery and persistence in the isolated host with the same payload. It does not claim live user-vault UI acceptance or external publishing acceptance. No article was externally published or approved on the user's behalf. The model's PASS is supplemented by inspection of the generated example and preserved source boundaries; it is not a guarantee of general writing quality.
