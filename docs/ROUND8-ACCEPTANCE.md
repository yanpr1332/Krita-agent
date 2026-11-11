# Round 8 acceptance — natural brushwork and material-aware rendering

> **Current state:** Round 8 source work and offline tests are being developed on `feat/round8-natural-brushwork`. No real Krita painting, independent visual acceptance or human approval has been performed in this cloud development phase. Preserve R7's known failed artworks as the locked baseline.

## A. Source and safety gates

- [x] Opt-in versioned `render` recipe in ScenePlan v4, without changing old plans that omit this field.
- [x] Separate ten material-oriented stroke geometries and five directional fields; vary length, curvature, spacing, color, pressure, opacity and passes through safe native brush strokes.
- [x] Bounded scene/intent expansion, strict unknown-field validation, on-polygon centerline clipping and brush-tip correction as an opt-in edge strategy.
- [x] User-approved R7 staged execution, hash-binding, editable layer output, unknown-result fail-closed policy and no-paste boundaries remain intact.
- [x] Informational plan repetition diagnostics, hash-validated full-canvas and per-subject-ROI pixel changes for archived actual Krita stage PNGs, and read-only CLI `creative diagnose`.
- [x] Cross-subject, cross-material sample study, negative/security tests and legacy compile regressions.
- [ ] Execute full Windows 3.10/3.13 GitHub CI for the final code SHA; link evidence here.
- [ ] Native tests of `wash/wisps/ripples/facets/growth/contour/folds/strands/planes/specular` on installed Krita builds, including brush preset behavior, actual stage pixels and CPU/time.
- [ ] Strict Export Integrity and fresh-copy Reopen Stability for new R8 creations, recording RGBA+ICC and retaining every failure.

## B. Controlled native comparisons

Before evaluating real artwork, lock a stable Round 7 scene plan and compare:

| Experiment | Hold fixed | Record |
| --- | --- | --- |
| R7 baseline vs R8 painter | Canvas, subject bounds, visible layers, approximate stroke/time budget, Krita build | Native PNG crop, gap/edge defects, repeated pattern evidence, rendering time |
| Surface type A/B | Subject geometry and style | Distinct real water/stone/cloud/leaf/ceramic/fabric/hair appearance |
| Parametric variants | Same painting task, only change material recipe parameters | Determinism, pressure response, color layering, edge quality |
| Cross-genre transfer | Recipe unchanged, new subject arrangement | Material transfer without benchmark-specific hardcoded coordinates |
| Integrity/recovery | Same native workflow and isolated run | Version hashes, stage cursor, lost-response behavior, strict reopened pixels |

At least three complete works (landscape, still life, simple character) plus at least one previously unseen prompt/arrangement per group. Failed candidates are retained and counted, not removed from the sample. No reference bitmap paste as painting.

## C. Finished-artwork review — independent gates

- [ ] Actual real KRA/PNG, three authentic full-stage previews, visible contributing editable paint layers, native screenshot and execution ledger.
- [ ] Independent visual judgement on **visible pixels**, not subject names or log step counts: composition, recognizability, completeness, edge continuity, volume/light, natural material marks, repetitiveness and scene-specific shortcomings.
- [ ] Real human review separately signed. Neither an agent-generated synthetic preview nor a model `pass` substitutes for that.
- [ ] Document A/B failures and actual affected regions, not just success examples.
- [ ] Preserve raw/failed versions and output hashes. Repair as a new KRA version, never overwrite a rejected one.

**Pass criteria:** Source and CI checks can establish `source_implemented` and `offline_passed`; actual Krita tests may establish `native_verified`; only real pixel/whole-art reviews can establish `artwork_accepted`. All statuses must remain separately reported.

## D. Known limits and deferred features

1. Different code-level mark silhouettes and seeded jitter do not, on their own, prove human-like artistry. The current clipping constrains **brush centerlines**, not the full native brush footprint; scalloped edges may remain.
2. The diagnostics emit risk indicators (low stage contribution, repeated trajectories, uniform orientation) rather than an automatic aesthetic score. A small intentional highlight is not a failure simply because it changes few pixels.
3. R8 deliberately does not implement general anatomical reasoning, artistic reference learning or an unbounded model self-correction loop. Those remain R9, R10 and R11 milestones.
4. The prior rare Qt6 five-pixel fresh-reopen root cause is still a separate investigation and must remain a strict gate if encountered.
5. A model planning prompt is included, but no paid API execution or independent remote visual critic was carried out for this branch.

## E. Handoff to the local native acceptance agent

Run `creative diagnose` against preserved real artwork after the native-stage archive; report original and reopened pixels and actual stage preview deltas. In each build, inspect at least three different materials at full-resolution crops. For the complete works, include the old-vs-new plan hashes and equivalent-run budget. Retain screenshots and failed results in isolated ignored `artwork-results/<run-id>` paths, and write a concise source-backed acceptance report to GitHub on this Round 8 branch only. Do not merge `main` without user authorization.

See [R8 API](ROUND8-API.md), [planned work packages](ROUND8-DEVELOPMENT-PLAN.md), [R7 failed baseline](ROUND7-ARTWORK-ATTEMPTS.md) and [project acceptance rules](../AGENTS.md).
