# Round 8 development brief — natural brushwork and material rendering

> **Original kickoff plan.** Source implementation is now underway on the same branch, but native and whole-artwork acceptance are NOT established. See [R8 API](ROUND8-API.md) and [acceptance](ROUND8-ACCEPTANCE.md). Created on the new `feat/round8-natural-brushwork` branch based on `main` at `5eb948ba10f96771da32ea003261a32292c72a05` (2026-11-11). Round 7 is merged, but its **finished-artwork acceptance FAILED**. Preserve all failed local evidence and do not modify `main` as part of Round 8 development.

## 1. Why Round 8 is necessary

Round 7 successfully demonstrated an auditable **execution framework**: ScenePlan v4 with generic subjects, ordered phases, purpose-bearing intents, deterministic stroke compilation, stage-by-stage confirmation, editable Krita layers, KRA preservation and strict fresh-reopen consistency. This is architectural progress, **not yet an accomplished painter**.

Read the dated evidence before making claims:

- [Round 7 native QA](ROUND7-LOCAL-ACCEPTANCE.md): 9 staged technical fixtures across Stable 5.3.4.1 / Next Qt5 / Next Qt6. All completed and passed strict reopen with **zero RGBA difference** in those tests; the first independent artwork review rejected all 3 subject outputs. This does not resolve the older separate 5-pixel Qt6 issue.
- [Round 7 whole-art attempts](ROUND7-ARTWORK-ATTEMPTS.md) and [sanitized measurements](acceptance-evidence/round7-artwork-attempts.json): 2 × 3 candidates (landscape, teapot/pear still life, traveler character); all 6 **failed independent visual review** despite 10–13 visibly contributing layers and strict image consistency. A third attempt remained interrupted before stage two.
- In initial fixtures, the detail stage changed only **55–149 pixels**, a useful warning that phase names/intent counts do not guarantee meaningful fine detail. This observation does not characterize all later artwork attempts.
- Failure patterns: repeated mechanical cloud strokes, sparse trees/reflections, empty foreground; scalloped color-fill edges, flat ceramic shading and incomplete spout/handle; neck gap, underdeveloped body shape and barely resolved forms.
- The R7 compiler currently supports only `gesture` (given guide), rotated parallel `coverage` scanlines and `accents` (tangent mini-strokes). The **same geometric grammar** applies to almost every named material; human readable `purpose` text is not itself converted into more intelligent paint decisions. Round 6 changes to color, brush size and pressure are real but cannot fix a poor stroke geometry.
- The six rejected plans were locally authored/executor-confirmed; they **did not establish that the optional real model planner itself failed**. Separate the planner, compiler, execution and independent artwork-review variables in every next experiment.

**Diagnosis:** R7 met much of its generalist-stage infrastructure goal but not whole-artwork quality. Improving the natural, material-appropriate painter is a distinct and necessary Round 8 effort. Do not attempt to pass by multiplying uniform strokes, swapping a benchmark, or calling a technical fixture an illustration.

## 2. Round 8 product goal

Given the *same reviewed ScenePlan v4 composition* and comparable resource budget, the new painter should produce **visibly more continuous forms, better edges/volume, less mechanical repetition and material-specific strokes**, while retaining:
- genuinely native Krita brush marks and editable layers;
- deterministic, bounded, audited source-to-mark compilation;
- separately approved stages, no ambiguous automatic replay and immutable failure evidence;
- full strict Export Integrity + Reopen Stability and independent actual-image review;
- generalist transfer across landscape, still life and at least a simple character rather than one hardcoded mountain scene.

Round 8 focuses on *how material surfaces are painted*. Round 9 remains responsible for deep anatomy, articulated poses and generalizable perspective construction; R10 for rights-cleared reference interpretation/technique memory; R11 for opt-in real-model automated visual critique and bounded revisions.

## 3. Development packages

### R8-A: surface/brush intent IR and compatibility contract

- Add a safely validated **material recipe / directional-field** layer on top of R7 subject + stage + ROI and purpose, keeping the legacy `gesture/coverage/accents` compiler available byte-for-byte for existing plans.
- Distinguish **subject structure** (what/where), **material** (mark-making and optical treatment) and **style** (rendering conventions). Do not equate a subject label with one hardcoded procedural painting function.
- Represent purpose-specific `edge_role` (hard/soft/lost), `surface_flow` (tangent, radial, contour, perspective or user-provided guide), `value_groups`, `stroke_scale`, `density`, `direction_variation`, `layering_pass` and `seed` as bounded declarative fields. Every extension remains schema-validated; no arbitrary model IPC or Python code.
- Keep existing v4 plans valid with unchanged behavior. Use an explicit version/feature discriminator and source digests for new semantics. Avoid silently altering old rendered hashes.

### R8-B: real region coverage and boundary quality

- Replace naked parallel scanline-only filling with one or more **region-aware brush placement strategies** using Krita-native marks: contour-following interior strokes, adaptive overlap and short edge-correction marks. If a native selection/mask route is adopted, isolate its build-specific proof first.
- Detect underpainted slivers, exposed stroke endpoints, scalloped borders and unintended gaps using **actual raster snapshots**, not just polygon area estimates.
- Respect negative space, transparency, intended soft edges and layer ordering. Do not artificially flood-fill/paste an external reference bitmap and call it original painting.
- Backstop expensive proposals with stroke, pixel-region, layer and native-step budgets; keep reproducible seeds and visual step previews.

### R8-C: meaningful brush dynamics, color and layering

- Choose brush preset families from **verified installed-Krita profiles**, never assume a nominal 'watercolor' name means a particular native response. Preserve stroke-level size/color/opacity switching and pressure interpolation from R6.
- Compose broad value blocks → structural midtones → directional volume strokes → local highlights/texture → edge reconciliation. Use small tonal/hue palettes tied to light and surface, not uniform random RGB noise.
- Permit deterministic but *structured* variation in width, arc length, curve, mark orientation, paint opacity and endpoints. In-stroke color/preset changes are **not** claimed unless the Bridge truly supports them.
- Add a detail-budget floor based on **actual local contribution and visual intent**, not raw stroke count alone. If the detailed stage changes only a few isolated pixels on a target meant to be resolved, emit a review warning.

### R8-D: material recipe library, style separated

Implement a composable initial library, with user-editable parameters and an honest per-build capability matrix. At least:
1. sky/cloud — gradual value shape, soft/hard edge hierarchy, non-cloned organic formations;
2. lake/water — perspective-aligned reflection strokes, length/density variation and value continuity;
3. stone/snow — planar facet orientation, cracks/edges, controlled contrast;
4. foliage/grass — clumps and branch/growth direction, varied silhouette, no cloned 'tree stamps';
5. ceramic/metal — radial/elliptical volume shading, rim and specular control;
6. fabric/hair/skin — drape/growth/form-following marks at a simple illustration level.

Materials must be mixable independently of subject names: e.g., ceramic in a still life and a room; fabric on a character and in the interior. Avoid benchmark-specific output geometry or copied image fills.

### R8-E: anti-mechanical diagnostics and actual pixel QC

- Go beyond R6 coarse duplicate-path signatures: investigate repeated curve shapes, rounded endpoint prominence, parallel-line periodicity, unnatural uniform spacing, fill holes, local edge raggedness and insufficient contrast/detail.
- Record region- and material-conditioned diagnostics, with source ROI masks and native-rendered pixels. Deliberate graphic repetition may be valid; diagnostics must explain context rather than blindly introduce jitter.
- Add a human-readable **why this mark exists** trail from material recipe → stroke group → relevant stage/ROI, coupled with counts and duration for auditing.
- Add a finite manual revision proposal interface for obvious **missing coverage / incorrect edge** defects. Every proposed revision requires explicit approval and a *new* editable layer/version; no self-triggered endless loops.

### R8-F: integration, regression, performance and documentation

- CLI/SDK mode selection, visualization of material recipe per stage, safe deterministic JSON serialization, tested legacy v4/v3 path and bounded per-intent expansion.
- Unit tests (geometry clipping/continuity/determinism, hostile input/budget limits, profile fallback, stage approvals, source tamper, failed effects), mock Bridge regression, Windows 3.10/3.13 CI.
- Native smoke tests across Stable / Next Qt5 / Next Qt6: pressure, edge filling, preview pixel contribution, layer editing, strict KRA/PNG/export/reopen. Preserve source and hashed artifacts.
- Maintain one coherent changelog/acceptance report; do not scatter temporary scripts or commit raw `artwork-results` with private data.

## 4. Controlled experiments and artwork acceptance

Pre-register each test's input contract, budgets and review criteria **before** adjusting algorithms. Use both a fixed-source comparison and unseen prompts.

1. **Baseline A/B (diagnosis):** same R7 scene structure, subjects, palette, canvas, native build and approximately comparable budget; R7 old compiler vs R8 material compiler. Document native time, stroke count, actual pixel difference, KRA integrity and blinded region-level visual judgement. Do not attribute improvements solely to algorithm if plans differ.
2. **Material studies:** separate cropped local areas for water, rock, cloud, foliage, ceramic, cloth/hair. Show screenshots and full-stage previews from real Krita with convincing differences rather than a list of claimed recipes.
3. **Whole art:** **three distinct complete pieces** (landscape, still life, simple character), separate from fixture-only plans. Require real editable KRA/PNG, original plan, presets, stage snapshots, visible layer contribution and preservation of failed attempts.
4. **Out-of-sample check:** at least one alternate prompt/arrangement per subject group not individually hardcoded in recipes. Preserve all failures in the denominator.
5. **Safety gates:** explicit approval per phase, fail-closed unknown execution, no model-generated commands, no raster-paste substitute, exact Export Integrity and Reopen Stability, no silent repaired-file overwrite.
6. **Visual gate:** blinded independent review of recognizability, silhouette/edge quality, volume/light, material distinction, repetition, foreground/background completion and whole-picture coherence. A real human sign-off is separately required for 'accepted'. VLM self-judgement or GitHub green CI cannot replace it.

Suggested tracking table columns: candidate ID, review brief, recipe versions, source SHA, stage SHA, native build/preset, compiled strokes, real painted-area coverage, edge-gap findings, duplicate geometry diagnostics, stage pixel contribution, actual KRA/PNG/reopen hashes, independent model observations, human verdict and outstanding defects.

**No fixed numeric aesthetic threshold is claimed now.** Early runs should calibrate meaningful region-level thresholds from actual image evidence; later tighten them before held-out acceptance. Do not optimize only one flattering metric.

## 5. Sequencing and stop conditions

1. Freeze R7 failed attempts as baseline; do not alter or remove their original hashes, manifests or reports.
2. R8-A + R8-B first: prove controllable brush placement and non-mechanical region boundaries in isolated native fixtures.
3. R8-C + R8-D next: demonstrate differing material techniques on the *same* base geometry without a fresh hardcoded scene for each.
4. R8-E + R8-F: instrument actual rendered pixels, run controlled comparisons, CI, then real multi-build and whole-art checks.
5. On acceptance failures, preserve real artifacts, classify the missing mechanism, implement a bounded fix and rerun. Do not 'pass' by changing the benchmark or multiplying strokes alone.

This plan **does not** authorize a model API payment or immediate new native local drawing. Full independent multimodal API art-evaluator automation remains planned for R11. Test fixtures may use already explicitly configured providers only when authorized.

## 6. Branch and status policy

- **Active development branch:** `feat/round8-natural-brushwork`, created from the verified latest `main` SHA above before any Round 8 write.
- **Current status:** kickoff / plan only. This document is not an implementation claim. Round 8 development must be separately implemented, CI-tested, natively verified and visually assessed.
- Preserve `main`, Round 7 merged history and all old feature branches. Do not merge/push `main` without express authorization. No Windows/WSL workspace or RDC operations were performed for this GitHub preparation.
- Continue to obey [AGENTS.md](../AGENTS.md), [the generalist roadmap](ARTIST-ROADMAP-R7-R12.md), [Round 7 acceptance](ROUND7-ACCEPTANCE.md) and [full artwork standards](ARTWORK-ACCEPTANCE.md).


## 7. Implementation checkpoint (2026-11-11)

The initial R8 source batch implements an optional validated recipe/field layer for ten painting techniques and five flow types; layered per-mark style/pressure, seed-stable staggered or bounded blue-noise placement, polygon-clipped centerlines and optional fine edge stitching; legacy R7 opt-out compatibility; a read-only diagnostic command inspecting actual native stage PNGs and mark-shape repeats; and Windows offline regression tests. This is **not** evidence of actual perceptual improvement. Remaining work in this round includes native material/preset trials, region-level edge and fill review, controlled R7-vs-R8 visual comparison, finishing quality improvements based on failed art, and independent human full-art acceptance. No cloud deployment or local desktop/Krita test is performed by this commit.


### Source validation checkpoint

Windows GitHub Actions [run #42990495459](https://github.com/yanpr1332/Krita-agent/actions/runs/42990495459) passed **223 offline tests** on Python 3.10 and 3.13 for commit `a366a41f`. The tests cover the declarative material schema, deterministic bounded native brush compilation, opt-out R7 compatibility, blue-noise placement, light-dependent palettes, actual-PNG diagnostics, subject-ROI deltas, failure guards and CLI contracts. **No installed Krita was used in this CI run.** For real native/visual acceptance, follow [the local handoff](ROUND8-NATIVE-HANDOFF.md) and preserve failed results.
