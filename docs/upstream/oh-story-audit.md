# Upstream Reference Audit: Oh Story (oh-story-claudecode)

## 1. Upstream Metadata

- **Repository**: `https://github.com/zenstory-ai/oh-story-claudecode`
- **Purpose**: Reference for serialized fiction workflows, tracking state mechanisms, and chapter continuation.
- **License**: MIT / Apache-2.0 compatible open source documentation and prompt workflows.
- **Audit Date**: 2026-09-16
- **Architecture Role**: Upstream conceptual reference and method library. **Not** a runtime dependency; **no** third-party code directly bundled or installed into global user environments.

---

## 2. Examined Concepts & Implementation Patterns

| Component / Workflow | Status | Architectural Treatment in OpenContent | Rationale |
|---|---|---|---|
| **Context Slicing & Prioritization** | **Adapted** | Integrated into `opencontent/capabilities/context.py` (P0/P1/P2 budget model) | Loading only relevant characters and open threads prevents prompt bloat and maintains bounded focus. |
| **Tracking State (Characters, Timeline, Open Threads)** | **Adapted** | Formulated as `opencontent.state-delta.v1` in `opencontent/capabilities/contracts.py` | State changes are emitted as candidate deltas from task execution and reviewed/applied to Project state; never directly overwriting formal Canon. |
| **Single Chapter & Continuation Loop** | **Adapted** | Defined as `write.yaml` and `continue.yaml` workflows in Narrative Pack | Provides distinct arcs for scene drafting and multi-chapter continuation while relying on explicit Project/Artifact snapshots rather than fragile session chat history. |
| **Targeted Revision (Minimal Change)** | **Adapted** | Defined as `revise.yaml` with explicit problem location, rationale, and diff boundaries | Replaces full-text rewriting with surgical edits preserving surrounding prose, established facts, and voice. |
| **Continuity Inspection** | **Adapted** | Implemented in `packs/narrative/validators/continuity.py` | Audits deceased/inactive character appearances and world rule violations before candidate artifact adoption. |
| **Oh Story JSON Database / State Files as Canon** | **REJECTED** | Preserved OpenContent Markdown/YAML as the single source of truth | Prevents a divergent second state database from competing with Vault Markdown. |
| **Global CLI Installation Scripts** | **REJECTED** | Scoped strictly to OpenContent's local workspace runner | Does not pollute user global environment or assume specific cloud platform setups. |
| **Web Novel Mechanical Formulae & Cliché Rules** | **REJECTED** | Kept flexible via 3 profiles (`general-fiction`, `serial-fiction`, `narrative-nonfiction`) | Avoids locking the creator into a single genre's formula or arbitrary word quotas. |
| **Heuristic "De-AI Flavor" Word Scoring** | **REJECTED** | Replaced with semantic five-axis review and structured critique | Quality comes from concrete scene craft and logic, not arbitrary keyword blacklists. |
| **Automated Cover & Platform Web Crawlers** | **REJECTED** | Out of scope for v1 local editorial plane | Keeps the focus on core writing craft and local vault ownership. |

---

## 3. Compliance & Architectural Invariants

1. **OpenContent Core Remains Decoupled**: OpenContent Core knows nothing about fiction tropes, story beats, or novel chapters. It only knows `CapabilityPack`, `Task`, `ContextPackage`, `Artifact`, `Review`, and `Jobs`.
2. **Attribution & Non-Pollution**: No external packages were injected into user environments. All adapted methods were implemented natively in Python/YAML conforming to OpenContent's type safety and verification standards.
