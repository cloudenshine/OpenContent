# Capability Pack Security & Workspace Isolation

## Threat Model & Boundaries

Capability Packs execute arbitrary creative workflows via local Agent CLIs. To protect user vaults from accidental corruption or adversarial tampering, OpenContent enforces strict isolation boundaries:

---

## 1. Filesystem Isolation

- **Isolated Run Directory**: Every capability task executes within a unique `.opencontent/runs/<run-id>/` folder.
- **Write Restriction**: Agents are confined to writing within `candidate/`, `review/`, and task logs inside their run directory.
- **Path Escape Prevention**: All paths emitted by agents or pack manifests are verified via `validate_workspace_path()`. Attempted `..` directory traversals, absolute paths, or symlink creations are rejected with hard failures.
- **Formal Vault Read-Only Snapshot**: Formal Vault files are exposed as read-only references or contextual JSON packages. Agents cannot modify live Vault notes or Markdown canon directly.

---

## 2. Formal Authority Separation

- **Candidates vs. Canon**: Agent output is strictly classified as `Candidate Artifact` or `State Delta proposal`. It cannot self-promote to authoritative status or bypass human approval.
- **Human Accept Required**: Adopting a candidate artifact creates a formal version and invalidates existing approvals, triggering the standard five-axis gate check and requiring explicit human signing.

---

## 3. Adversarial Invariant Checks

The test suite systematically probes:
1. Attempted path escapes using `../` in manifests or outputs.
2. Symlink creation within run workspaces.
3. Malformed state deltas attempting to inject unauthorized entity origins.
4. Tampered context packages with modified dependency hashes.
5. Concurrent native edits invalidating in-flight generation.
