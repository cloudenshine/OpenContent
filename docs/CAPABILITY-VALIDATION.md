# Capability Validation & Acceptance Criteria

## Automated Test Matrix

The Capability Pack architecture is validated across four tiers:

---

## 1. Unit Tests (`tests/test_capabilities.py`)

- **Manifest Validation**: Schema version compliance, ID formatting, semver checks, path traversal rejection, missing profile/workflow errors.
- **Pack Registry**: Multi-root discovery, duplicate ID detection, capability enumeration, profile retrieval.
- **Task Router**: Deterministic routing (`task -> pack -> profile -> workflow`), invalid task rejection.
- **Context Assembler**: Task-specific selection, P0/P1/P2 budget enforcement, provenance tracking, exclusion of irrelevant characters.
- **State Delta Validator**: Origin tagging (`observed_from_output`, `explicit_user_instruction`, `agent_inference`), schema compliance.
- **Security & Path Traversal**: `validate_workspace_path` rejection of `..` traversals, absolute paths, and symlinks.

---

## 2. Multi-Artifact Integration Tests (`tests/test_multi_artifact.py`)

- Creation of multiple Artifacts within a single Project.
- Independent version tracking, diff generation, and context hash computation.
- Explicit `artifact_id` targeting during critique and decision stages.
- Verification that approving Chapter 1 does not automatically approve Chapter 2.

---

## 3. Real Local CLI & Host Tests

- **Codex CLI**: Verifies execution of `LocalCodexProvider` with task requests.
- **Workspace Receipts**: Validates structure and fields of `receipt.json`.
- **Obsidian Compatibility**: Verifies that plugin loads cleanly, renders capability options, and handles candidate diffs.
