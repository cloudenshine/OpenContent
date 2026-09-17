# Capability Pack Authoring Guide

This guide enables developers to create and package new creative capability packs (e.g. `evidence-essay`, `video-narrative`, `history-storytelling`) without modifying OpenContent Core.

---

## Pack Structure

Every capability pack resides in its own directory (e.g. `packs/<pack-id>/` or `<vault>/OpenContent-Packs/<pack-id>/`) with the following structure:

```text
packs/<pack-id>/
  pack.yaml                # Primary capability manifest
  profiles/
    <profile-id>.yaml      # Profile definitions (tone, guidance, constraints)
  workflows/
    <task-id>.yaml         # Workflow step definitions for supported tasks
  context/
    selector.py            # (Optional) Domain-specific context selection logic
  validators/
    <name>.py              # (Optional) Domain-specific continuity/quality validators
```

---

## 1. Defining `pack.yaml`

The manifest must adhere to schema `opencontent.capability-pack.v1`:

```yaml
schema: opencontent.capability-pack.v1

id: my-pack-id             # 2-32 lowercase alphanumeric with hyphens
name: My Creative Pack
version: 1.0.0             # Semver X.Y.Z

description: >
  Brief summary of capabilities provided by this pack.

profiles:
  - standard-profile
  - advanced-profile

tasks:
  - plan
  - write
  - continue
  - revise
  - critique

runtime:
  tools: required          # required | optional | disabled
  workspace_write: required
  session: optional
  web: optional

workflows:
  plan: workflows/plan.yaml
  write: workflows/write.yaml
  continue: workflows/continue.yaml
  revise: workflows/revise.yaml
  critique: workflows/critique.yaml

context:
  selector: context/selector.py

outputs:
  - artifact
  - proposal
  - state_delta
  - review
```

---

## 2. Defining Profiles (`profiles/*.yaml`)

Profiles define genre conventions, tone guidelines, invariants, and creative boundaries:

```yaml
id: standard-profile
name: Standard Profile
description: Profile summary.

tone: factual and engaging
voice: third-person
pacing: structured

guidance: >
  Editorial guidance provided to the Creator agent during task execution.

invariants:
  - "Rule 1 that must not be broken"
  - "Rule 2 that must be preserved"

forbidden:
  - "Anti-pattern 1"
  - "Anti-pattern 2"

creative_freedom:
  - "Allowed stylistic choices"
```

---

## 3. Defining Workflows (`workflows/*.yaml`)

Workflows specify the logical progression of steps for each supported task:

```yaml
id: write
name: Writing Workflow
description: Scene drafting procedure.

steps:
  - id: analyze_context
    description: Inspect prompt, constraints, and relevant sources.
  - id: draft_content
    description: Write prose according to profile invariants.
  - id: check_continuity
    description: Validate facts and temporal continuity.

outputs:
  - candidate: Candidate markdown draft.
  - state_delta: State updates.
```

---

## 4. Registering Your Pack

OpenContent automatically discovers packs located in:
1. `packs/` within the repository root.
2. `OpenContent-Packs/` in the user's Obsidian Vault.

To verify discovery programmatically:
```python
from pathlib import Path
from opencontent.capabilities import load_manifest, PackRegistry

registry = PackRegistry()
registry.discover([Path("packs"), Path("my-custom-packs")])
print(registry.list_capabilities())
```
