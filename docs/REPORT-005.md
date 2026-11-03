# Round 2 implementation report — 2026-11-03

## Scope and status

Second-round source code added to a dedicated branch `feat/round2-advanced-workflow`. **This is an implementation report, NOT a runtime acceptance report.** No unit tests, Krita GUI tests, plugin installation, GitHub Actions, or integration validation are being run during this round, as requested. Existing first-round acceptance evidence in REPORT-004 remains unchanged.

### Stage I: editable drawing

- Added command handlers for recursive layer tree and stable ID selection, rename, visibility, lock, opacity, blending mode, color label, grouping, duplication, reorder, delete with explicit confirmation, and position moves.
- Added multiple-document listing/activation, explicit close protection, crop, selection rectangle/clear/copy/cut/paste (API behavior pending validation).
- Added a bounded image import to RGBA U8 editable layers and file-linked reference layers. Import paths are confined to a configured local input directory.
- Added native brush resource listing and metadata inspection, plus explicit scale and rotation operations.
- Added offline Catmull–Rom sampling, smoothing, arc-length resampling and pressure/sensor interpolation, exposed through CLI and workflow compiler.

### Stage II: preview and resilient jobs

- Added bounded full-image, region and layer previews with PNG file outputs and hashes. Previews do not silently overwrite files.
- Added local optional Pillow pixel comparison and SHA256 digest module to enable deterministic feedback for later local revisions.
- Added explicit workflow steps for editing existing open documents without forcing a new canvas.
- Added an atomic per-job journal under the authorized output directory. A restarted Bridge marks unfinished jobs **interrupted**; it does not auto-replay potentially duplicated brush strokes.
- Added read-only recovery inspection and plan archiving, status panel, pause/resume/cancel buttons if the optional Docker is enabled.
- Added undo/redo wrappers that refuse to operate during an active job.

### Stage III: compatibility and maintenance

- Added upstream source change impact classification, source URLs, suggestions for later isolated tests, and saved runtime symbol evidence ingestion.
- Added separate native command handlers instead of extending the original monolithic Bridge dispatcher indefinitely. Existing first-round commands remain in place.
- Updated README in English/Chinese, roadmap, architecture, example workflow, optional manual CI configuration, and additional regression test source.

## Known limitations and risks

- **Unverified new commands:** Krita Python APIs differ between Stable/Next and Qt5/Qt6. In particular, document activation, node transforms, selections, file layers, native pixel data and DockWidget behavior need target-build inspection before calling them supported.
- **Preserved established behaviors:** the first-round Bridge path remains unchanged except for advanced command routing, job journal integration and optional Dock initialization.
- **Durability is not a transaction:** a last step may have taken effect before a crash. The journal records steps and progress; it does not save a KRA checkpoint for every stroke or guarantee automatic resume after restart.
- **Output sandbox:** output files are under the configured output root; reference imports require a configured input root. Destructive edits require explicit parameters and are not silently permitted by the workflow compiler.
- **Upstream source findings are not runtime tests.** Manual CI is not automatically triggered by pushes.

## Next action

Inspect the branch as source changes and review the PR when desired. Runtime tests and compatibility repairs are intentionally deferred and have not been scheduled.
