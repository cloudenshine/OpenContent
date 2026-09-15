# Notices

OpenContent 0.4 source is licensed under the repository MIT LICENSE.

The application imports PyYAML 6.0.3 (MIT) and Mistune 3.2.0 (BSD-3-Clause) as Python dependencies; their source packages are not bundled. The Obsidian plugin calls the host's public API; Obsidian itself is not bundled. The optional Codex adapter invokes a separately installed and authenticated CLI; no Agent runtime is bundled.

The previous implementation and its Apache-2.0 OpenDesign audit samples are preserved only in `archive/pre-charter-v0.1/`, together with their original notices. They are excluded from the new release and are not runtime dependencies.

Additional research-only Open Design samples under `docs/ux-research/opendesign/` are from nexu-io/open-design commit `00c12c6451d9248c11a5c5122714e4d0b9f5709c`, under Apache-2.0. Their LICENSE and a source URL/SHA-256 manifest are retained. They are excluded from runtime archives and are not covered by OpenContent's MIT license. The interaction changes are independently implemented.

The research-only files under `docs/market-evidence/ailu-audit/` come from mcncarl/ailu, commit 8a232fe082163c5898038cca7bcf26cb1956b9a2, under that project's GNU AGPL-3.0 license. The original LICENSE and source URL/hash manifest are retained alongside this research. These samples are not covered by OpenContent's MIT license, are not imported by the application, and are explicitly excluded from release archives. OpenContent's Markdown handoff is independently implemented and does not invoke Ailu or its platform uploaders.
