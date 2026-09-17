# Narrative Capability Pack v1

## Identity

- **ID**: `narrative`
- **Version**: `1.0.0`
- **Purpose**: Planning, scene drafting, multi-chapter continuation, surgical revision, and independent critique.

---

## Profiles

1. **`general-fiction`**:
   - Focus: Character motivation, causal conflict, organic pacing, sensory scene craft.
   - Tone: Immersive, character-driven storytelling without formulaic web-fiction tropes.
2. **`serial-fiction`**:
   - Focus: Chapter arc commitments, escalating stakes, expectation management, continuity across installments.
   - Tone: Engaging, forward-moving serialized rhythm.
3. **`narrative-nonfiction`**:
   - Focus: Rigorous factual fidelity, source attribution, chronological precision combined with dramatic exposition.
   - Tone: Fact-disciplined, vivid narrative reconstruction.

---

## Workflows & Tasks

- **`plan`**: Outlines dramatic arcs, turning points, character flaw/goal matrices, and initial narrative anchors.
- **`write`**: Drafts complete scenes or chapters from prioritized context, generating candidate prose and state deltas.
- **`continue`**: Resumes from the prior chapter's final state (locations, injuries, lingering hooks) without relying on chat session memory.
- **`revise`**: Surgical, minimal necessary revision addressing specific flaws without rewriting untouched prose.
- **`critique`**: Independent multi-dimensional audit evaluating character credibility, pacing, tension, and continuity.

---

## Output Contracts

- **Candidate Artifact**: Proposal for human review and diff inspection.
- **State Delta**: Structured tracking updates (`characters`, `timeline`, `world`, `open_threads`) marked with origin (`observed_from_output`, `explicit_user_instruction`, `agent_inference`).
- **Review**: Structured issues categorized by severity (`hard`, `major`, `minor`) with concrete locations and suggested remediations.
