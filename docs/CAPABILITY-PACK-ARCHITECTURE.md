# Creative Capability Pack Architecture

## Overview

The Creative Capability Pack architecture extends OpenContent with pluggable, domain-specific creative methods without altering the core editorial invariants of OpenContent.

```text
Obsidian Desktop Plugin
          ↓
  OpenContent Core (Kernel / Vault / Jobs)
          ↓
  Capability Runtime (Router / Assembler / Workspace)
          ↓
   Capability Pack (Narrative, Evidence Essay, etc.)
          ↓
  Local Agent CLI (Codex / Claude)
```

---

## Core Invariants

1. **OpenContent Core Remains Method-Agnostic**: Core handles Projects, Artifacts, Reviews, Approvals, and Jobs. It does not hardcode genre rules, narrative conventions, or medium constraints.
2. **Pack ≠ Skill**: A Pack is a cohesive bundle of manifest, profiles, workflows, context selectors, validators, and references. It is not merely an array of prompt snippets.
3. **Single Source of Truth**: Markdown and YAML in the Obsidian Vault remain the sole authoritative canon. State deltas and candidate outputs are proposals that must be accepted before becoming canon.
4. **Task-Specific Context Assembly**: The Context Assembler loads only information whose absence would materially cause the current task to fail, organized into P0 (essential), P1 (relevant), and P2 (optional) budget tiers.
5. **Multi-Artifact Support**: A single Project can maintain multiple Artifacts (e.g. chapters, companion essays, video scripts), each possessing independent version hashes, reviews, and approval states.

---

## Pack Lifecycle

1. **Discovery**: `PackRegistry.discover(roots)` scans trusted directories for `pack.yaml`.
2. **Routing**: `TaskRouter.route(task_request)` maps task, pack, and profile to the designated workflow.
3. **Context Assembly**: `ContextAssembler.assemble()` builds a bounded, prioritized `ContextPackage`.
4. **Workspace Isolation**: Execution occurs within `.opencontent/runs/<run-id>/`, preventing unauthorized filesystem modifications.
5. **Validation & Receipt**: Validators audit continuity, state deltas, and output formats, recording a deterministic `receipt.json`.
