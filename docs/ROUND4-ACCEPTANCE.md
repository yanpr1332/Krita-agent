# Round 4 acceptance checklist — NOT EXECUTED

Status: all items below are pending. This is a plan, not test evidence.
Previously passing Round 3 tests do not imply any Round 4 feature passes.

## 0. Safety and baseline
- [ ] Record tested SHA, exact Krita Stable 5.3.4.1, Next Qt5 5.4 prealpha, Next Qt6 6.1 prealpha, Python/Qt and environment.
- [ ] Back up shared user pykrita resources. Use disposable KRA/input/output roots and independent sessions. Do not affect personal artwork or unrelated PIDs.
- [ ] Run all prior and new offline tests and source compilation; record actual totals and defects, not estimates.
- [ ] Review Git diff and branch; confirm main unchanged and no credentials/caches/artwork committed.

## 1. R4-A Document graph
- [ ] Capture a graph of groups, paint layers, masks, filters and file layers with distinct blending, opacity and visibility.
- [ ] Assert node IDs, paths, parents, sibling order, effective visibility, color model and bounds; verify graph JSON size guard.
- [ ] Rename/reorder/modify one layer; verify diff accuracy. Save/reopen KRA; rebind only exact matches, never guess ambiguous identity.

## 2. R4-B Multi-layer safe revision — critical gate
- [ ] Prepare 8+ editable layers including masks and filters, and capture BEFORE and GOAL PNG plus graph.
- [ ] Plan opaque-only changed tiles and inspect SHA256 of source/target, graph, ROI and each preflight tile.
- [ ] Mutate reference, layer order, node metadata, live tile and plan JSON independently; every stale input must be rejected before mutation.
- [ ] Apply only with explicit confirmation. Verify immutable KRA checkpoint; a new topmost paint overlay is created, all original nodes remain byte- and hierarchy-unchanged.
- [ ] Compare every changed tile pixel-by-pixel to target, including alpha; verify unchanged tiles remain unchanged. Reopen resulting KRA and original KRA.
- [ ] Explicitly reject translucent goals, >500K-pixel region, too many tiles, image/graph mismatch, unauthorized reference path, unsafe UUID, overwrite, non-RGBA-U8 and lack of confirmation.
- [ ] Kill only owned test Krita at controlled points; verify recovery from last confirmed checkpoint without blind replay.
- [ ] Test native overlay on Stable Qt5, Next Qt5 and Next Qt6; record unsupported APIs separately.

## 3. R4-C Long work and performance
- [ ] Compile and execute 1200+ steps in sequential bounded jobs (max 120 steps/batch), each with a real KRA checkpoint and durable ledger.
- [ ] Inspect job IDs, batch hashes, timing, saved KRA checkpoints and progress; verify no lost/duplicate strokes.
- [ ] Simulate response lost after a potentially accepted job: ledger becomes unknown_needs_review and there is exactly zero automatic retry.
- [ ] Test pause/resume/cancel, wrong-port/reconnect, limited disk space and partial journal failure; do not kill unrelated processes.
- [ ] Compare a continuous 2048-point stroke and explicitly segmented long trajectory for timing, visible seam and Undo granularity.

## 4. R4-D Brush calibration
- [ ] Generate calibration workflows for three installed presets per build; inspect actual pressure/size and opacity effects.
- [ ] Record evidence SHA, build ID, category and confidence for each profile; verify selection refuses mismatched/low-confidence evidence.
- [ ] Never label untested presets pressure-calibrated based on file name alone.

## 5. R4-E Tile and large canvas
- [ ] Run 4096x4096 fixture using 512x512 previews and compare every tile origin, dimensions and pixel hash.
- [ ] Check tile edges, pyramid metadata, memory/disk budgets, 32MP input cap and IPC size restrictions.
- [ ] Test alpha-only changes and fully transparent output, which must not silently pass an opaque-overlay revision.
- [ ] Confirm profile/bit-depth probes, unsupported RGBA-U16 pixel write rejection and no unapproved color conversion.

## 6. R4-F/G ScenePlan and feedback
- [ ] Compile ScenePlan v2 with 8+ layer roles, strokes/shapes, brush data and preview markers; verify deterministic plan SHA and no hidden actions.
- [ ] Reject invalid/untrusted AI candidate JSON, unsupported role/command, oversized steps and unsafe paths.
- [ ] Submit only after explicit action, inspect editable KRA and compare actual pixels.
- [ ] Review a goal/current PNG with alpha-aware difference and limited iterations; verify no automatic repair execution, infinite loop or cloud call.
- [ ] Apply two separately approved revisions on test artwork; test goal vs after-preview and rollback boundaries.

## 7. R4-H/I Project/GUI/compatibility
- [ ] Test Dock recent job list, latency metrics, preview, error states and Pause/Resume/Cancel on all three builds/DPI configurations.
- [ ] Create project, record KRA/references/scene/job ledger, audit file SHA and tamper detection; ensure no tokens are stored.
- [ ] Verify additive v2 SDK DTOs do not change existing v1 IPC protocol or break legacy clients.
- [ ] Verify manual capability matrix never promotes source_seen to tested_working without true runtime evidence.
- [ ] Exercise explicit plugin install/rollback in disposable profile and manually invoke offline CI only with user authorization.
- [ ] Reconcile README EN/ZH, ROADMAP, ARCHITECTURE and reports with measured results.

## 8. Final integrated milestone
- [ ] Real 4096x4096 canvas, at least 8 editable layers, three calibrated presets and >1000 native steps.
- [ ] Two approved revisions, deliberate owned-process crash/recovery, unchanged original nodes, KRA reopen and exact ROI pixel comparison.
- [ ] Record time, memory, GUI responsiveness, task throughput, storage; deliver sanitized REPORT-011 and evidence.
- [ ] Repair all failures before marking Round 4 native accepted.

No Round 4 tests, GUI checks or CI runs were performed when this checklist was authored.
