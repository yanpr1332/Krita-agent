# Round 4 acceptance checklist

Local results and build-specific limits are recorded in [REPORT-011](REPORT-011.md). The run used disposable documents and installed Stable, Next Qt5 and Next Qt6 builds.

## 0. Safety and baseline

[Baseline and scope](REPORT-011.md) · [Offline results](acceptance-evidence/round4-offline.xml) · [Install and rollback](acceptance-evidence/round4-install-rollback.json)

- [x] Record tested SHA, exact Krita Stable 5.3.4.1, Next Qt5 5.4 prealpha, Next Qt6 6.1 prealpha, Python/Qt and environment.
- [x] Back up shared user pykrita resources. Use disposable KRA/input/output roots and independent sessions. Do not affect personal artwork or unrelated PIDs.
- [x] Run all prior and new offline tests and source compilation; record actual totals and defects, not estimates.
- [x] Review Git diff and branch; confirm main unchanged and no credentials/caches/artwork committed.

## 1. R4-A Document graph

[Native graph](acceptance-evidence/round4-native-stable.json) · [Rebind and layer payloads](acceptance-evidence/round4-supplement-stable.json) · [Graph budget](acceptance-evidence/round4-final-guards-stable.json)

- [x] Capture a graph of groups, paint layers, masks, filters and file layers with distinct blending, opacity and visibility.
- [x] Assert node IDs, paths, parents, sibling order, effective visibility, color model and bounds; verify graph JSON size guard.
- [x] Rename/reorder/modify one layer; verify diff accuracy. Save/reopen KRA; rebind only exact matches, never guess ambiguous identity.

## 2. R4-B Multi-layer safe revision — critical gate

[Stable](acceptance-evidence/round4-native-stable.json) · [Qt5](acceptance-evidence/round4-native-qt5.json) · [Qt6](acceptance-evidence/round4-native-qt6.json) · [129 changed tiles](acceptance-evidence/round4-changed-tile-cap.json) · [Existing output](acceptance-evidence/round4-overwrite-preflight.json)

- [x] Prepare 8+ editable layers including masks and filters, and capture BEFORE and GOAL PNG plus graph.
- [x] Plan opaque-only changed tiles and inspect SHA256 of source/target, graph, ROI and each preflight tile.
- [x] Mutate reference, layer order, node metadata, live tile and plan JSON independently; every stale input must be rejected before mutation.
- [x] Apply only with explicit confirmation. Verify immutable KRA checkpoint; a new topmost paint overlay is created, all original nodes remain byte- and hierarchy-unchanged.
- [x] Compare every changed tile pixel-by-pixel to target, including alpha; verify unchanged tiles remain unchanged. Reopen resulting KRA and original KRA.
- [x] Explicitly reject translucent goals, >500K-pixel region, too many tiles, image/graph mismatch, unauthorized reference path, unsafe UUID, overwrite, non-RGBA-U8 and lack of confirmation.
- [x] Kill only owned test Krita at controlled points; verify recovery from last confirmed checkpoint without blind replay.
- [x] Test native overlay on Stable Qt5, Next Qt5 and Next Qt6; record unsupported APIs separately.

## 3. R4-C Long work and performance

[KRA pixel and checkpoint checks](acceptance-evidence/round4-milestone-pixels.json) · [Fault injection](acceptance-evidence/round4-faults-stable.json) · [Stroke timing and Undo](acceptance-evidence/round4-supplement-qt6.json)

- [x] Compile and execute 1200+ steps in sequential bounded jobs (max 120 steps/batch), each with a real KRA checkpoint and durable ledger.
- [x] Inspect job IDs, batch hashes, timing, saved KRA checkpoints and progress; verify no lost/duplicate strokes.
- [x] Simulate response lost after a potentially accepted job: ledger becomes unknown_needs_review and there is exactly zero automatic retry.
- [x] Test pause/resume/cancel, wrong-port/reconnect, limited disk space and partial journal failure; do not kill unrelated processes.
- [x] Compare a continuous 2048-point stroke and explicitly segmented long trajectory for timing, visible seam and Undo granularity.
- [x] Test explicit long-stroke splitting of >2048 samples, endpoint overlap, global nondecreasing timestamps, seams and multiple Undo steps; unapproved splitting must fail.

## 4. R4-D Brush calibration

[Stable](acceptance-evidence/round4-native-stable.json) · [Qt5](acceptance-evidence/round4-native-qt5.json) · [Qt6](acceptance-evidence/round4-native-qt6.json)

- [x] Generate calibration workflows for three installed presets per build; inspect actual pressure/size and opacity effects.
- [x] Record evidence SHA, build ID, category and confidence for each profile; verify selection refuses mismatched/low-confidence evidence.
- [x] Never label untested presets pressure-calibrated based on file name alone.

## 5. R4-E Tile and large canvas

[Pyramid and ICC](acceptance-evidence/round4-pyramid-color-budget.json) · [Native limits](acceptance-evidence/round4-final-guards-stable.json) · [Alpha feedback](acceptance-evidence/round4-feedback.json)

- [x] Run 4096x4096 fixture using 512x512 previews and compare every tile origin, dimensions and pixel hash.
- [x] Check tile edges, offline Pillow pyramid PNG artifacts/ICC metadata, memory/disk budgets, 32MP input cap and IPC size restrictions.
- [x] Test alpha-only changes and fully transparent output, which must not silently pass an opaque-overlay revision.
- [x] Confirm profile/bit-depth probes, unsupported RGBA-U16 pixel write rejection and no unapproved color conversion.

## 6. R4-F/G ScenePlan and feedback

[Scene execution](acceptance-evidence/round4-supplement-qt6.json) · [Candidate validation](acceptance-evidence/round4-scene-validation.json) · [Feedback](acceptance-evidence/round4-feedback.json)

- [x] Compile ScenePlan v2 with 8+ layer roles, strokes/shapes, brush data and preview markers; verify deterministic plan SHA and no hidden actions.
- [x] Reject invalid/untrusted AI candidate JSON, unsupported role/command, oversized steps and unsafe paths.
- [x] Submit only after explicit action, inspect editable KRA and compare actual pixels.
- [x] Review a goal/current PNG with alpha-aware difference and limited iterations; verify no automatic repair execution, infinite loop or cloud call.
- [x] Apply two separately approved revisions on test artwork; test goal vs after-preview and rollback boundaries.

## 7. R4-H/I Project/GUI/compatibility

[Stable Dock](acceptance-evidence/round4-dock-stable.json) · [Qt5 Dock](acceptance-evidence/round4-dock-qt5.json) · [Qt6 Dock](acceptance-evidence/round4-dock-qt6.json) · [Project audits](acceptance-evidence/round4-projects-provenance.json) · [Capability matrix](acceptance-evidence/round4-capability-matrix.json)

- [x] Test Dock recent job list, latency metrics, preview, error states and Pause/Resume/Cancel on all three builds/DPI configurations.
- [x] Create project, record KRA/references/scene/job ledger, audit file SHA and tamper detection; ensure no tokens are stored.
- [x] Verify additive v2 SDK DTOs do not change existing v1 IPC protocol or break legacy clients.
- [x] Verify manual capability matrix never promotes source_seen to tested_working without true runtime evidence.
- [x] Exercise explicit plugin install and rollback in a disposable resource directory.
- [ ] Remote workflow dispatch is conditional on separate authorization and was outside this local run.
- [x] Reconcile README EN/ZH, ROADMAP, ARCHITECTURE and reports with measured results.

## 8. Final integrated milestone

[Milestone evidence and measured limits](REPORT-011.md#results-and-evidence)

- [x] Real 4096x4096 canvas, at least 8 editable layers, three calibrated presets and >1000 native steps.
- [x] Two approved revisions, deliberate owned-process crash/recovery, unchanged original nodes, KRA reopen and exact ROI pixel comparison.
- [x] Record time, memory, GUI responsiveness, task throughput, storage; deliver sanitized REPORT-011 and evidence.
- [x] Repair all failures before marking Round 4 native accepted.
