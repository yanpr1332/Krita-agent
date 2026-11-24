# Krita Agent roadmap — authoritative current status (2026-11-10)

Status terms: **code authored** means committed source only; **offline passed** requires executed tests; **native accepted** requires real Krita behavioral evidence. These terms must not be used interchangeably.

**Branch isolation policy:** every new numbered development round and every cross-round roadmap/documentation milestone must be created on its own new branch *before* any GitHub write. Do not append future plans to the previous round's existing branch. See [AGENTS.md](../AGENTS.md) for mandatory workflow. This R7–R12 plan was authored on `docs/round7-12-generalist-roadmap`, separate from `feat/round6-brush-dynamics`.

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

An original visual benchmark, fixed scene contract and mandatory local-result evidence gate were added after discovering that earlier 1,200-stroke / rectangle tests verified technical capability only. See [ARTWORK-ACCEPTANCE.md](ARTWORK-ACCEPTANCE.md) and root [AGENTS.md](../AGENTS.md). No new whole-artwork drawing test has run as part of this policy change.

## Round 5 — autonomous creative workflow source implemented, real-art acceptance pending

Branch: `feat/round5-autonomous-creative-workflow`; Python package: `0.6.0.dev0`.

- [x] **R5-A / Engine:** Persistent creative run state, explicit plan/revision approval, stage artifacts, versioned native KRA/PNG archive and fail-closed unknown effects. Long-job continuation verifies the prior KRA and restores it to a fresh copy before any suffix.
- [x] **R5-B / Planner:** Opt-in HTTPS JSON model adapter and user-provided ScenePlan v3 candidate; validates object IDs, bounds, depth, parent cycles, real brush strokes, canvas and compiler commands. No arbitrary generated IPC commands.
- [x] **R5-C / Painting Strategist:** Object-aware brush category, pressure envelopes, sizes and optional manually reviewed build-specific preset selection, compiled through ScenePlan v2 and existing native Bridge.
- [x] **R5-D / Visual Critic:** Uses the real full PNG and up to three actual region crops as multimodal input, requires concrete findings for every object and returns bounded observations and ROIs; no claim of independent final artwork acceptance.
- [x] **R5-E / Reviser:** Critique-bound new-layer native stroke proposal, ROI containment, source PNG hash, explicit human approval and live baseline preflight before drawing. No silent overwrite of original layers.
- [x] **R5-F / Integration:** CLI `creative` lifecycle, versioned artwork collection, three run-scoped native stage snapshots, read-only HTML status dashboard, delivery artifacts, safety tests, Windows CI and bilingual docs.
- [ ] **Native acceptance:** Stable / Next Qt5 / Next Qt6 validation, real artwork re-open and independent VLM plus human review are still required.

Deferred: generative inpainting, arbitrary reverse compositing, unattended model loops, arbitrary-code plugins, high-bit-depth editing and a fully live native Dock workflow dashboard. Source-level CLI integration does not imply end-to-end real-image quality. See [ROUND5-API](ROUND5-API.md) and [ROUND5-ACCEPTANCE](ROUND5-ACCEPTANCE.md).

## Round 5 cloud offline validation

At code revision `689535a`, [GitHub Actions run 42468603707](https://github.com/yanpr1332/Krita-agent/actions/runs/42468603707) passed 129 offline pytest cases and source compilation on each of Windows Python 3.10 and 3.13. This is not native installed-Krita acceptance or independent finished-artwork review. A prior Python setup failure was caused by GitHub's Python artifact server returning HTTP 504; it did not run project tests.

## Round 6 — stroke-level brush flexibility (NATIVE FIXTURES VERIFIED; HUMAN ARTWORK ACCEPTANCE PENDING)

- [x] Per-stroke Krita brush preset, nominal size, foreground color and opacity; named palettes and safe baseline restoration.
- [x] Arc-length multiknot pressure curves with bounded deterministic modulation and optional speed sensitivity.
- [x] Per-stroke calibrated preset categories, larger semantic object stroke budgets and per-object detail minima.
- [x] Brush diversity/density diagnostics and flexible ROI revision strokes.
- [x] Three-build native pressure/brush calibration, adjacent switching, mask painting and strict KRA reopen checks **for the tested fixtures**; see dated reports.
- [x] Optimized native Needle Lake candidate and model visual review recorded; preserve the original five-pixel failed reopen and later corrected version.
- [ ] Independent **human** whole-artwork approval, formal audit, and root-cause fix of the rare Qt6 one-level reopen difference.

[Round 6 API](ROUND6-API.md) · [Round 6 acceptance](ROUND6-ACCEPTANCE.md) · [Round 6 native reacceptance](ROUND6-REACCEPTANCE.md)

## Round 7–12 — generalist human-like painting roadmap (partially implemented; R8–R12 proposed)

**Long-term product direction, not yet delivered artwork capability:** real and natural Krita painting, broad common-subject coverage, and reference-based repainting plus reusable technique learning. Round 7 source implementation introduces the staged foundation, **not** native or finished-art validation. The full six-round plan, technical architecture, per-round deliverables, AI evaluation schedule, safety boundaries, and held-out multi-subject art acceptance criteria are documented in **[ARTIST-ROADMAP-R7-R12](ARTIST-ROADMAP-R7-R12.md)**.

- **R7 (source implemented, Windows offline CI 189/189 passed on Python 3.10 and 3.13; native QA pending):** ScenePlan v4 free-form subject hierarchy/materials, sketch/block/detail StagePlan, deterministic gesture/coverage/accent intent lowering to ScenePlan v3, explicit per-stage approval and source-bound native preview archiving; old v3 retained. See [Round 7 API](ROUND7-API.md), [Round 7 acceptance](ROUND7-ACCEPTANCE.md), and [CI run #42771429702](https://github.com/yanpr1332/Krita-agent/actions/runs/42771429702).
- **R8:** Natural material-specific brushwork, lighting-aware texture, and anti-repetition.
- **R9:** People, animals, still life, architecture, mechanical subjects, and illustration generalization.
- **R10:** Authorized reference repainting and provenance-aware style/technique library.
- **R11:** Real opt-in multimodal API visual evaluation and bounded, auditable revision loop. Model assistance for planning/seeing references may be used earlier when configured; mandatory paid evaluator integration is intentionally deferred.
- **R12:** Whole-system performance, long-running reliability, cross-build testing, and held-out multi-genre artwork acceptance.

Each development round should use its own branch. Native/visual/human evidence remains distinct; no fixed benchmark-specific scripts, pasted reference image, stroke-count target, or model self-rating can substitute for real artwork acceptance.

## Cloud-first acceptance scheduling amendment (2026-11-19)

The user approved a consolidated local validation approach for R9–R12 to reduce costly repeated local agent sessions. Round-specific branches remain mandatory. Complete most source/contract/geometry/fault-injection tests in GitHub CI; attempt genuine cloud Krita smoke testing separately; perform **one staged local Windows acceptance campaign** after integrated cloud development, with minimal targeted native smoke exceptions if essential. Keep visual and human artwork judgements as independent final gates, and never claim mock/CI successes as native painting. Implementation and limitations: [Cloud Validation Strategy](CLOUD-VALIDATION-STRATEGY.md). This planning change lives on its own `infra/cloud-tiered-acceptance` branch and does not modify the existing Round 8 feature branch.


## Tier-2 cloud Krita native checkpoint (2026-11-19)

**Native cloud smoke verified for official Linux Krita 5.3.4.1**, with real authenticated Bridge, editable KRA, original/reopened PNGs and 0 strict pixel differences. [GitHub Actions #44482971863](https://github.com/yanpr1332/Krita-agent/actions/runs/44482971863) · [full evidence report](CLOUD-NATIVE-ACCEPTANCE.md). The infrastructure is isolated on `infra/cloud-tiered-acceptance`; Windows local build compatibility, advanced brush/artwork quality and final human acceptance remain pending. CI is not merged into `main`.

- **R7 (source implemented; 9 three-build native technical fixtures passed; complete-artwork visual acceptance FAILED):** ScenePlan v4 free-form subject hierarchy/materials, sketch/block/detail StagePlan, deterministic gesture/coverage/accent intent lowering to ScenePlan v3, explicit per-stage approval and source-bound native preview archiving; old v3 retained. See [Round 7 API](ROUND7-API.md), [Round 7 acceptance](ROUND7-ACCEPTANCE.md), [Round 7 failed artwork attempts](ROUND7-ARTWORK-ATTEMPTS.md), and [CI run #42771429702](https://github.com/yanpr1332/Krita-agent/actions/runs/42771429702).
- **R8 (source implemented; Windows 3.10/3.13 CI: 223 passed each; native/artwork acceptance pending):** Opt-in ten-technique material rendering, surface flow fields, layered per-mark brush/pressure/color, centerline clipping and edge stitching, deterministic staggered or blue-noise placement, actual-stage and per-subject-ROI PNG change diagnostics plus geometric repetition diagnostics. See [Round 8 API](ROUND8-API.md), [acceptance](ROUND8-ACCEPTANCE.md) and [development brief](ROUND8-DEVELOPMENT-PLAN.md). [Windows CI #42990495459](https://github.com/yanpr1332/Krita-agent/actions/runs/42990495459) is green; code-only tests are not whole-artwork evidence.

## Round 9 — structural generalist painting (cloud-first implementation)

Development branch: `feat/round9-multigenre-structure`; created from verified `main` that already includes cloud Tier-2, then imports outstanding Round 8 source **only into this branch**. R9 adds opt-in generic subject anchors/parts/chains and explicit part counts, depth/occlusion/relative-scale constraints, vanishing-point convergence, deterministic subject+material painting strategy hints and explicit hash-bound locked-geometry revision proposals. Real structural guide strokes are generated only when guide_mode=paint, through the existing safe native compiler. See [Round 9 API](ROUND9-API.md) and [R9 acceptance checklist](ROUND9-ACCEPTANCE.md). **Offline CI/native smoke do not prove convincing human/animal anatomy or multi-genre artwork quality.** Full visual/local acceptance is deferred to the consolidated R9–R12 campaign.

**Round 9 cloud engineering verification (2026-11-19):** [Windows Python 3.10 + 3.13 CI #44494279871](https://github.com/yanpr1332/Krita-agent/actions/runs/44494279871) passed **265 cases per environment**. [True Linux Krita 5.3.4.1 #44494279816](https://github.com/yanpr1332/Krita-agent/actions/runs/44494279816) passed 41 real native commands, bounded structural guides, 6 editable phase paint layers and strict zero-pixel KRA export/reopen. See [Round 9 cloud native report](ROUND9-CLOUD-ACCEPTANCE.md). Not a Windows installed-build test nor independent whole-artwork evaluation.

## Round 10 — reference-guided native painting and reusable techniques (cloud source implementation)

Development branch: `feat/round10-reference-technique` created from verified Round 9 merged `main`. Adds (1) provenance/permission-gated local image analysis, per-source and author-ROI color/value/edge metrics, (2) separately authorized VLM subject/geometry hypotheses, (3) multi-reference role bindings and SHA-bound palette/material/composition candidates for validated ScenePlan v4, (4) immutable versioned reusable native brush technique recipes with material/build limitations, (5) strict original KRA and PNG/reopened comparison. See [Round 10 API](ROUND10-API.md), [acceptance](ROUND10-ACCEPTANCE.md). **Offline/cloud native execution and artwork similarity are independent evidence levels; no local full-artwork evaluation was requested this round.**

**Round 10 cloud evidence (source revision `27887d17`, 2026-11-19):** [Windows CI #44517302459](https://github.com/yanpr1332/Krita-agent/actions/runs/44517302459) passed **285 tests each** on Python 3.10/3.13. [Real Krita 5.3.4.1 #44517302418](https://github.com/yanpr1332/Krita-agent/actions/runs/44517302418) passed 52 native commands for the licensed synthetic reference→color/technique hypothesis→editable StagePlan→fresh-KRA-reopen pipeline, with 0 strict reopened pixel differences. This confirms engineering workflow only; material technique extraction may explicitly return indeterminate direction, and observed reference/painting ROI color gaps remain large. [Evidence](ROUND10-CLOUD-ACCEPTANCE.md).


## Round 12 — integrated workflow observability and effort profiles (source milestone)

Development branch: `feat/round12-generalist-acceptance`, based on merged Round 11 main. This first R12 package adds bounded effort profiles, compiled-step enforcement, hash-chained phase timings, planned brush/pressure summaries, dashboard/CLI observability and per-channel reopen-drift localization. It improves operational control and evidence quality; it does not solve KRA color drift or establish artistic generalization. Offline CI passed on Python 3.10 and 3.13 (306 tests each); Tier-2 native timings, the three-build Windows/Krita campaign and the 24-task held-out artwork benchmark remain pending. See [Round 12 API](ROUND12-API.md), [acceptance checklist](ROUND12-ACCEPTANCE.md) and [REPORT-012](REPORT-012.md).


Round 12 follow-up: per-subject brush diversity floors now make the earlier request for multiple sizes, colors, opacity levels and pressure variation measurable. The default is advisory for backward compatibility; strict mode is opt-in and blocks plans that fail the selected profile floor. This is still a plan-level check, not proof of visible pressure or good artwork.

Round 12 follow-up: generalist diversity floors now aggregate strokes across the subject's complete staged lifecycle. Stage-local layers no longer cause false failures simply because a sketch or block-in phase is intentionally sparse.

Round 12 follow-up: the native brush calibration fixture now tests constant and changing pressure plus nominal size changes. Profiles remain build-specific and require manual inspection of real Krita exports before registration.
