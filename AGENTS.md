# Local agent instructions: Krita Agent and its acceptance process

These rules apply to coding/testing agents and the local human-run acceptance workflow. Follow them before claiming a feature or end-to-end painting workflow is accepted.

## Mandatory GitHub branch isolation — before every write

**A new development round or a new cross-round roadmap/documentation effort MUST start on a NEW GitHub branch before writing any file.** Do not add Round N+1 source, tests, roadmap, acceptance policy or future-work plans to the existing Round N feature branch merely because it is the latest branch. This requirement applies to documentation-only work, too.

1. **Identify the work type:** new numbered round → `feat/roundN-topic`; future-round or cross-round planning → a separate `docs/topic` branch; current-round bugfix only → its existing Round N branch. The user may explicitly choose another branch; honor that instruction.
2. **Create first, write second:** inspect the intended base commit and existing branch/PR, create the new branch, verify its ref points to the expected base, **then** make commits. Never write first and decide the target branch later.
3. **Keep review boundaries clean:** a Round N PR should contain only Round N work and relevant fixes. Plans for future rounds must not be mixed into it. No default branch merge or push to `main` without explicit authorization.
4. **Resolve ambiguity before mutations:** when the correct target branch cannot be determined safely, ask the user. Do not infer “same branch as last turn” for a new round.
5. **Recover safely if misfiled:** verify and preserve the exact new work on the proper new branch before repairing the old branch. Recheck remote refs and open PRs; never discard unrelated commits or rewrite another person's changes. History-altering ref moves require exact-target, no-intervening-commit checks and an explicit request/authority.

## Distinguish acceptance types

- TECHNICAL acceptance checks Krita API behavior, native strokes, KRA/pixel operations, performance and safety. Simple boxes and repeated lines are allowed for only these tests.
- FULL-ARTWORK acceptance checks whether the actual Krita Agent has generated an entire coherent, recognizable, editable illustration. A grid of 1,200 strokes, eight empty/named layers, or several rectangles is never a passing artwork.
- A milestone described as "can paint a finished illustration" requires BOTH technical and full-artwork acceptance. Do not backfill earlier technical reports as artwork validation.

## Mandatory full-artwork inputs

Read docs/ARTWORK-ACCEPTANCE.md, docs/ARTWORK-VLM-REVIEW.md and the immutable scene contract in benchmarks/artwork/contracts/sunset_alpine_lake.v1.json. **Open the pixels** of benchmarks/artwork/reference/sunset_alpine_lake.jpg and show them to the visual evaluator. Do not let a VLM infer visual complexity from captions, filenames, labels or logs only.

The illustration reference is a complexity target, not an image to paste into Krita as the final artifact. The benchmark must be locked before running. Do not edit it to make an inferior output pass.

## Mandatory local run outputs

Create a unique directory under artwork-results/<run-id>/ **inside this repository**. Preserve final artwork.kra, artwork.png, actual Krita screenshot, scene plan, native execution history, layer graph, evidence of 8 or more genuinely contributing paint layers, three full-scene stage previews, and two independent reviews. Keep failure runs, too. Do not delete, overwrite or mislabel them after inspection.

Never claim the finished artwork exists unless the PNG is visibly shown and the KRA can be reopened with editable painted content. Counts of tools, steps or layers prove nothing about picture coherence.

## Separation of duties and fail-closed rules

- The executor must not generate a fake "finished picture" via the evaluator/test script or paste the benchmark JPEG as a flattened outcome.
- The VLM must receive the actual benchmark AND the actual finished exported artwork as images, check every object and spatial relation, and reject abstract tests masquerading as a landscape.
- The person running the executor may generate machine-readable logs, but must not impersonate an independent human reviewer or fill human approval as if it already happened.
- Missing human review, VLM review, final PNG, real KRA or meaningful layer evidence means NOT ACCEPTED. Report what is pending instead.
- Technical safety remains mandatory: do not reuse uncertain native strokes, overwrite personal art, kill unrelated Krita PIDs or publish sensitive files.

## Publishing

Raw acceptance runs stay under artwork-results and are ignored by Git to prevent accidental leaks and massive commits; they are STILL present locally. Only after real visual and human acceptance, run scripts/prepare_artwork_publish.py to stage a small curated preview and public metadata. That script never performs git push. Review privacy/licenses, then explicitly commit curated files if authorized. Full KRA needs separate LFS/Release approval.


## Round 5 autonomous creative workflow

The `creative` CLI is an orchestrator, not a substitute for the real Krita-native painting acceptance. Inspect and approve a full ScenePlan v3 before `creative paint`. Natural-language planning and visual critique require explicit user-configured model credentials; no silent cloud calls. The visual critic's internal `decision=pass` is NOT independent artwork approval. A final artwork still requires both independent reviewer files, KRA reopen evidence, all stage images, object recognizability and real contributing paint layers.

Do not use model responses as arbitrary commands. Revised strokes must stay inside approved ROIs on newly created layers. If a native step, export, checkpoint restore or revision has unknown effects, never retry automatically. Do not commit raw artwork, local credentials, or run-state files into GitHub. Store output versions under the requested local run directory and keep older versions intact.


Round 5's optional stage snapshots must come from actual Krita `preview.canvas` commands, not from offline generated substitutes. The local static dashboard is a status/evidence browser, not proof of a completed painting or a substitute for real review.

## Mandatory integrity and reopen evidence

For every native creative export, archive the original KRA and initial PNG **before** judging integrity, including failed files. Report Export Integrity (KRA embedded mergedimage versus initial PNG) and Reopen Stability (freshly reopened KRA versus initial PNG) as separate hash-bound metrics. Require strict RGBA/ICC equality for delivery; explicitly bounded minor RGB differences are informational and never silently accepted. A repair must be a new immutable version, retaining the failed original and evidence. A lost/ambiguous native reopen or export response must remain unknown and never be replayed automatically. Do not claim this feature natively accepted until it is exercised with real Krita builds.

## Round 6 per-stroke painting acceptance

Native painting plans may now switch brush size, color, opacity and preset on each separate stroke, and may supply per-sample pressure dynamics. This source implementation does not prove that any installed brush reacts to pressure. When accepting a drawing, inspect the actual KRA, real exported pixels, selected brush presets, layer contributions and pressure differences in all requested Krita builds. Do not substitute brush-count, palette-size or diagnostic score for visual artwork quality. Preserve failing runs, hashes and stage snapshots. Do not silently split a continuous stroke or auto-replay an uncertain Krita effect. ScenePlan v3 still requires explicit user approval before native execution.


## Round 7–12 generalist artist charter (future work, not accepted features)

Before starting any Round 7+ development, read [docs/ARTIST-ROADMAP-R7-R12.md](docs/ARTIST-ROADMAP-R7-R12.md). The user-approved long-term direction has three non-negotiable goals: **purposeful, natural human-like painting**, **common-subject generalization beyond landscapes**, and **authorized reference repainting plus provenance-aware reusable technique learning**. Avoid replacing these goals with brush/stroke-count milestones.

- Preserve the existing real editable Krita/KRA, whitelisted Bridge, user approval, hash, rollback/reopen, failed-version retention, and independent human evaluation contracts.
- Do not hardcode final artwork for a particular benchmark, re-label pasted references as brush-painted output, or infer generic drawing skill from one alpine sunset.
- Treat proposed Round 7–12 capabilities as **not implemented** until real code and appropriate native/artwork acceptance evidence exist. Each development round belongs on its own branch and must record unresolved limitations.
- Full real-API multimodal **evaluation** is planned for Round 11; earlier optional model-based planning or reference understanding is allowed with explicit user-provided credentials, but paid model access must not silently become a requirement or be auto-invoked without authorization.
- A human or visual model may guide bounded revisions, but no model response may impersonate an independent human reviewer. “Learning” recipes and style records do not constitute a change in foundation-model weights.


## Round 7 stage-planning and new branch safety

This round lives on the dedicated `feat/round7-generalist-scene` branch, based on the separate planning branch. Every subsequent numbered development round or cross-round roadmap effort MUST create and verify its **new** GitHub branch before the first write; do not append new rounds to R7. Do not silently merge a feature branch into main.

ScenePlan v4 is a high-level **proposal** with generic subjects, material descriptors, stages, and `gesture`/`coverage`/`accents` intents. Validate all candidate JSON; forbid generated code or unreviewed IPC commands. Only the bounded compiler may emit native brush operations. The artist must review the full scene and **explicitly approve each stage individually**; observe real Krita canvas previews and layer contributions between phases. If a stage effect is uncertain, preserve the ledger and require manual inspection without automatic retry or fabricated success.

The R7 source implementation, offline unit tests, real Krita native verification, and independent complete-artwork quality acceptance are separate claims. Keep the original KRA and all failed evidence; enforce strict export/reopen pixel gates, and archive repairs as new versions. R8–R12 goals remain prospective; do not claim R7 provides sophisticated human-like strokes, universal subjects, or learned reference styles without whole-artwork acceptance.


## Round 8 material renderer and true-artwork acceptance

Round 8 lives only on `feat/round8-natural-brushwork`, created from verified merged Round 7 `main`. It adds **opt-in** material-aware native mark algorithms and read-only diagnostics. Never write any Round 8 work onto `main` or the Round 7 branch without specific authority, and create a fresh branch before future Round 9 or cross-round milestones.

Material recipes, seeded irregularity, ten named techniques and plan/repetition metrics are **not** evidence of convincing painterly skill. The source compiler constrains stroke centerlines; installed Krita brush tips may extend outside the region. Verify real stage PNGs, endcap/edge gaps, concrete material differentiation, actual brush presets and editable layer contributions on supported builds. Preserve exact KRA/PNG/reopen hashes and retain every failure version. Independent human review is mandatory for whole-artwork acceptance. Do not silently change the benchmark, multiply strokes to game scores, auto-replay uncertain effects, or pass an artificial PNG as Krita-native artwork. Full multimodal model evaluation is still a separate authorized later task.
