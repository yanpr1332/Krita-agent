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


## Round 4 — local acceptance recorded

Development branch: feat/round4-layer-aware-painting, version 0.5.0.dev0.
See REPORT-011 for the scope of each tested capability.

- [x] R4-A: live DocumentGraph hierarchy, rebind candidates, node diff.
- [x] R4-B: conservative opaque-only tile revision into a new editable top layer; immutable originals.
- [x] R4-C: durable serial scheduler for up to 10K workflow steps and bounded 1-MiB sub-jobs; no uncertain retry.
- [x] R4-D: reproducible pressure calibration plans and manually reviewed, build-specific brush profiles.
- [x] R4-E: tile ROI planning/preview and pyramid metadata; 4096² acceptance target, no claimed high-bit-depth pixels.
- [x] R4-F: ScenePlan v2 semantic layer roles converted into validated Krita commands.
- [x] R4-G: alpha-aware finite feedback proposals with explicit approval for every revision.
- [x] R4-H: Dock step timing plus local creative-project artifact manifests.
- [x] R4-I: protocol v2 SDK DTOs, conservative evidence registry, plugin ZIP builder, bilingual docs and acceptance evidence.

See [REPORT-011](REPORT-011.md), [ROUND4-API](ROUND4-API.md) and [ROUND4-ACCEPTANCE](ROUND4-ACCEPTANCE.md).

## Deferred (NOT Round 3 claims)

Open-ended natural-language art planning, multimodal semantic critiques, generative inpainting, arbitrary multi-layer source-to-target compositing, automatic resume without a saved KRA, full high-bit-depth pixel edit implementations, general ICC correctness guarantee, scheduled monitoring and headless native painting on unsupported platforms.

## R4.5 artwork acceptance correction (policy, not a drawing acceptance)

An original visual benchmark, fixed scene contract and mandatory local-result evidence gate were added after discovering that earlier 1,200-stroke / rectangle tests verified technical capability only. See [ARTWORK-ACCEPTANCE.md](ARTWORK-ACCEPTANCE.md) and root [AGENTS.md](../AGENTS.md). No new whole-artwork drawing test has run as part of this policy change. ## Round 5 — source implementation on GitHub; acceptance pending

Development branch: feat/round5-autonomous-creative-workflow. Package version: 0.6.0.dev0.

- [x] R5-A: Explicit long-job continuation from a known safe batch boundary only; verifies workflow/batch digests and the latest KRA checkpoint SHA. Unknown or in-flight effects remain blocked.
- [x] R5-B: Offline ScenePlan v2 preflight with layer/role/stroke/shape/point metrics, empty-layer checks and off-canvas warnings.
- [x] R5-C: Artwork review schema v2 binds visual and human decisions to the exact PNG/KRA and visual inputs; requires object and relation evidence.
- [x] R5-D: Automatic Windows GitHub Actions CI for Python 3.10 and 3.13 on feature pushes and pull requests.
- [ ] R5-E: Native full-artwork benchmark on a real Krita session, with actual KRA/PNG, stages, contributing layers and independent reviews.
- [ ] R5-F: Generative image planning/inpainting, arbitrary multilayer compositing, high-bit-depth editing and general ICC correctness remain deferred pending separate design and native validation.

See ROUND5-API.md and ROUND5-ACCEPTANCE.md. Source implementation does not imply CI success or native/artwork acceptance.
