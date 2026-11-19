# Round 9 — acceptance and next-stage handoff

Development branch: `feat/round9-multigenre-structure` (created from verified cloud-infrastructure `main`, then Round 8 source merged **into this new branch only**). Main remains protected and unchanged by R9 work.

## Tier 1 — deterministic source, protocol and safety

- [x] Windows Python 3.10 / 3.13 CI both 265 passed on [#44494279871](https://github.com/yanpr1332/Krita-agent/actions/runs/44494279871).
- [x] Existing Round 8 render recipes keep backward-compatible output and still satisfy material boundedness.
- [x] Six generalist semantic categories compile using the **same** structure/constraint contract, without category-specific emitted image scripts.
- [x] Consistent named anchors, parts, explicit part-count expectations, cross-subject relations and one-point perspective pass validation.
- [x] Invalid figures/perspective/depth, missing references, cycles, locked edits, tampered revisions or stale source hashes fail closed.
- [x] Only explicit `guide_mode:paint` adds native sketch gestures; default audit-only contributes no extra native paint.
- [x] All native commands pass the same R7/R8 v4→v3→v2 allowlist, stage digest and no-unknown-retry policy.

## Tier 2 — real Krita Linux AppImage

- [x] Native CI 5.3.4.1 creates actual scene, paints the extra structural sketch guides and color blocks, generates per-phase Krita PNGs, and confirms distinct stage pixel contributions.
- [x] Valid editable KRA has phase/subject paint layers and zero strict exported/reopened RGBA and color-profile differences (or honestly reports failure and exact differences).
- [x] Source binding and structural diagnostics are retained as test evidence; no Python-generated substitute image is accepted.
- [ ] CI artifacts contain hashes, native build version and failing logs. All these are **engineering tests**, not anatomical pixel correctness assessments.

## Tier 3 — deferred consolidated local artwork validation

- [ ] User-authorized Windows Stable/Next Qt5/Next Qt6 genuine KRA/PNG run.
- [ ] Pre-registered unseen benchmark (minimum six genres × three held-out prompts); meaningful recognizable subjects, anatomy and perspective reviewed independently. Failed pictures retained. No changing prompts to game the outcome.
- [ ] Visual and manual evidence distinguish real artwork quality from planning constraints or increased stroke count; human and VLM findings remain separate.
- [ ] Only after integrated R9–R12 cloud development, carry out single cost-aware local campaign; small native smoke exceptions require explicit approval.

## Failure/recovery contract

ScenePlan errors stop **before** any Krita effect. Geometry inconsistency is actionable with a named subject, relation/part/anchor ID and stage. Structure revision proposals modify only a copy, require explicit confirmation and validate the entire source. Existing artwork/KRA/PNG remain immutable, and every model-issued native change would require separate real-image evaluation in Round 11.

## Honest scope

R9 improves the ability to **express and enforce** composition/part/perspective plans and to route structural sketch guides to the native engine. It cannot prove that those constraints describe a visually correct pose or that Krita's final paint looks like a human artwork. This remains an explicit unresolved goal, not a passing result simply because CI is green.

**Executed Tier-2 evidence:** [#44494279816](https://github.com/yanpr1332/Krita-agent/actions/runs/44494279816), 41 actual Bridge native commands, two extra Round 9 construction strokes, six phase/subject paint layers, three stages, original/reopened PNG SHA-256 equality and strict zero RGBA pixel drift. The separately downloadable trace and hashes are in [ROUND9-CLOUD-ACCEPTANCE.md](ROUND9-CLOUD-ACCEPTANCE.md). The original user-artwork/aesthetic milestones in Tier 3 remain unchecked.
