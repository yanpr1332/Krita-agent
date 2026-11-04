# Krita Agent roadmap — authoritative current status (2026-11-04)

Status terms: **code authored** means committed source only; **offline passed** requires executed tests; **native accepted** requires real Krita behavioral evidence. These terms must not be used interchangeably.

## Round 1 — NATIVE ACCEPTED

- [x] Authenticated localhost Bridge and CLI, Stable/Next Qt5/Next Qt6 connectivity.
- [x] Native paint layers, brush presets, pressure stroke and segmented fallback.
- [x] KRA roundtrip, PNG export, job control and security rejection.
- [x] 18 offline tests documented as passing. See [REPORT-004](REPORT-004.md).

## Round 2 — NATIVE ACCEPTED

- [x] Layer tree, grouping, duplication/reorder/transforms, document control.
- [x] Reference/image import, selection copy/paste, region previews and pixel edits.
- [x] Local feedback primitives, task journal/interruption markers, upstream evidence analysis.
- [x] Qt5/Qt6 Dock actual button click and pixel comparison across three installed builds.
- [x] 34 offline tests; 54 command/protection records and 8 pixel assertion groups per build.
- [x] See [REPORT-006](REPORT-006.md) and [REPORT-007](REPORT-007.md) for limits and real results.

## Round 3 — INSTALLED-BUILD ACCEPTANCE COMPLETED

Executed offline and installed-build results are recorded in REPORT-009; earlier source completion remains in REPORT-008.

- [x] **R3-A:** SHA-bound KRA snapshots, step-boundary journal, deliberate restore to fresh copy and explicit suffix resumption.
- [x] **R3-B:** non-destructive transparency/selection/filter masks and filter layers.
- [x] **R3-C:** separate reversible pixel edit journal, clipboard artifact, selection algebra and feathering.
- [x] **R3-D:** structured layer/stroke scene planning and additional brush metadata.
- [x] **R3-E:** image difference and constrained reference-guided local revision with preflight projection.
- [x] **R3-F:** color model/ICC introspection and backup-required explicit conversion.
- [x] **R3-G:** SHA API inventory, Python AST, heuristic C++ header changes, manual capability provenance.
- [x] **R3-H:** Dock history/error/preview and project documentation/acceptance suite.

See [REPORT-008](REPORT-008.md) for code completion and [ROUND3-ACCEPTANCE](ROUND3-ACCEPTANCE.md) for the executed checklist.


## Round 4 — SOURCE COMPLETED; NO ACCEPTANCE PERFORMED

Development branch: feat/round4-layer-aware-painting, version 0.5.0.dev0.
All items below are UNCHECKED until an independently recorded runtime acceptance.

- [ ] R4-A: live DocumentGraph hierarchy, rebind candidates, node diff.
- [ ] R4-B: conservative opaque-only tile revision into a new editable top layer; immutable originals.
- [ ] R4-C: durable serial scheduler for up to 10K workflow steps and bounded 1-MiB sub-jobs; no uncertain retry.
- [ ] R4-D: reproducible pressure calibration plans and manually reviewed, build-specific brush profiles.
- [ ] R4-E: tile ROI planning/preview and pyramid metadata; 4096² acceptance target, no claimed high-bit-depth pixels.
- [ ] R4-F: ScenePlan v2 semantic layer roles converted into validated Krita commands.
- [ ] R4-G: alpha-aware finite feedback proposals with explicit approval for every revision.
- [ ] R4-H: Dock step timing plus local creative-project artifact manifests.
- [ ] R4-I: protocol v2 SDK DTOs, conservative evidence registry, plugin ZIP builder, bilingual docs, pending test plan.

See REPORT-010.md, ROUND4-API.md and ROUND4-ACCEPTANCE.md.
New modules are NOT included in historical 57 offline tests that were recorded as passed.

## Deferred (NOT Round 3 claims)

Open-ended natural-language art planning, multimodal semantic critiques, generative inpainting, arbitrary multi-layer source-to-target compositing, automatic resume without a saved KRA, full high-bit-depth pixel edit implementations, general ICC correctness guarantee, scheduled monitoring and headless native painting on unsupported platforms.
