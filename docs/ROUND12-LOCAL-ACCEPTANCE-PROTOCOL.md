# Round 12 — consolidated Windows / Krita local acceptance protocol

**Status: normative test plan; no local acceptance has been executed by adding this document.**  
**Scope:** the integrated R7–R12 painting workflow as delivered by Round 12. This protocol does not change the implementation and does not turn offline CI into native or artwork acceptance.

Use this document together with [Round 12 acceptance checklist](ROUND12-ACCEPTANCE.md), [native brush calibration](ROUND12-BRUSH-CALIBRATION.md), [full-artwork acceptance standard](ARTWORK-ACCEPTANCE.md), [visual-review instructions](ARTWORK-VLM-REVIEW.md), and the root [AGENTS.md](../AGENTS.md). Where requirements differ, follow the stricter project-wide `AGENTS.md` / `ARTWORK-ACCEPTANCE.md` rules.

## 1. Verdicts and acceptance levels

Every gate and every build/task must use one of these states:

- `PASS`: the specified action was executed and every stated criterion was met with retained evidence.
- `FAIL`: the action was executed and at least one criterion was not met.
- `BLOCKED`: execution could not safely proceed (missing build, device, permission, provider, or required input).
- `NOT_RUN`: no attempt was made.

Never convert `BLOCKED`, `NOT_RUN`, missing evidence, or an unknown native result into `PASS`. Preserve failures and retries as separate immutable attempts.

Report these levels independently:

1. `offline_passed`: source/tests/CI only.
2. `cloud_native_verified`: genuine Krita native execution on the isolated cloud runner.
3. `local_native_verified`: genuine Krita execution on the named Windows build.
4. `artwork_human_accepted`: the exact artwork passed the separate human review.
5. `campaign_passed`: the aggregate 24-task thresholds in Section 8 were met.

A green CI run does not promote any later level. A task with a failed technical gate cannot count as an accepted artwork.

## 2. Campaign design — fixed 24-task matrix

Run the full artwork campaign on one designated primary build (default: installed Krita Stable). The matrix contains **18 held-out text tasks plus 6 reference tasks = 24 tasks**:

| Genre | Text task 1 | Text task 2 | Text task 3 | Reference task |
| --- | --- | --- | --- | --- |
| Landscape | `LND-T1` simple | `LND-T2` intermediate | `LND-T3` complex | `LND-REF` |
| Still life | `STL-T1` simple | `STL-T2` intermediate | `STL-T3` complex | `STL-REF` |
| Architecture / interior | `ARC-T1` simple | `ARC-T2` intermediate | `ARC-T3` complex | `ARC-REF` |
| Human | `HUM-T1` simple | `HUM-T2` intermediate | `HUM-T3` complex | `HUM-REF` |
| Animal | `ANI-T1` simple | `ANI-T2` intermediate | `ANI-T3` complex | `ANI-REF` |
| Illustration / comic | `ILL-T1` simple | `ILL-T2` intermediate | `ILL-T3` complex | `ILL-REF` |

Task-design requirements:

- Each text genre gets one simple single-subject task, one intermediate task with several objects or explicit spatial relations, and one complex task involving a difficult pose, perspective, interaction, lighting condition, or multi-part composition. Keep the prompts natural-language; do not prescribe coordinates, stroke paths, layer names, or a task-specific script.
- `LND-REF` is the repository's locked [sunset-alpine-lake benchmark](../benchmarks/artwork/contracts/sunset_alpine_lake.v1.json). It counts as the landscape reference task and is the canonical run for the existing `scripts/artwork_acceptance_audit.py`.
- The other five reference tasks must use user-owned or explicitly licensed images, one each for still life, architecture/interior, human, animal, and illustration/comic. Record source, rights/permission declaration, SHA-256, intended use, and whether external upload is permitted. Do not scrape or substitute unlicensed images.
- Before the first task, freeze all 24 prompts, task contracts, required objects/relations, complexity labels, reference hashes, canvas settings, model identifiers, and shared generation settings in a local `campaign-manifest.json`. Do not rewrite a prompt, remove a difficult task, or change a task contract after seeing its output.
- Use the same configured generalist planning model and shared settings across all 24 tasks. Record the actual model identifier and non-secret settings. Do not hand-author a special scene plan for a failed task and then count it as a model-generated success. A manually supplied plan may be used for a separate technical diagnostic, not as a replacement benchmark result.
- Use a consistent 1600 × 900, 16:9 canvas for the campaign. If a task genuinely requires another canvas, declare it in the manifest before execution and apply the same dimensions to all A/B variants of that task.
- All attempts count. A crash, invalid plan, incomplete image, or failed review remains in the denominator. A repaired attempt is a new version with the failed original retained.

## 3. Preflight and environment isolation

Before running any native task:

1. Confirm the PR has been merged or check out the exact reviewed feature commit in a separate worktree. Record the full source commit SHA. Do not mix uncommitted source edits into the campaign.
2. Record Windows version, Krita version/build, Qt version, Python/Bridge version, plugin version, active display profile, input device and driver (if available), and the exact executable path for each installed build.
3. Test Stable, Next Qt5, and Next Qt6 as separate targets. Keep their executable/resource/plugin paths and Bridge sessions distinct. Never point two running instances at the same session or output directory.
4. Use a disposable Krita profile or a clearly isolated test document. Do not open, modify, overwrite, or clean up the user's existing artwork. Do not silently install/update Krita, plugins, brush packs, or drivers.
5. Create a unique campaign directory under the repository's ignored `artwork-results/` directory. Confirm it is not tracked by Git. Never put API keys, private source images, or raw KRA/PNG evidence in a commit or CI artifact.
6. Confirm the Bridge is authenticated and loopback-only, inspect `krita-agent capabilities`, and verify the intended document/output paths before the first native write.
7. If a visual model or reference-analysis provider will receive image data, obtain explicit campaign-scoped user consent first. For every external reference, confirm rights and upload permission separately. No consent means `BLOCKED` for that external-review step, not silent upload or a claimed pass.

Recommended campaign ID: `r12-<YYYYMMDD>-<source-sha7>`. If source code changes during testing, start a new campaign ID; do not combine results from different source revisions.

## 4. Three-build native smoke gate

Run this small gate separately on **Stable, Next Qt5, and Next Qt6** before spending time on the 24 artworks.

For each build:

- Connect to the actual Krita Bridge and record the reported build/capabilities.
- Create a disposable document, execute real native strokes on at least three ordered stages, and inspect the actual canvas after each stage.
- Capture the three full-scene stage previews from Krita's native preview operation; generated/mock images or screenshots of a test dashboard are not stage evidence.
- Save an editable KRA and export the first PNG from that same KRA. Reopen a fresh copy of the KRA in that same Krita build and export `reopened.png`.
- Record Export Integrity (embedded KRA projection versus first PNG) and Reopen Stability (freshly reopened KRA versus first PNG) separately.
- Require exact RGBA pixel equality, matching dimensions, and matching color-profile/ICC metadata for both gates. Zero differing pixels is the pass condition. A one-pixel or one-level difference is a failure to investigate, not an automatic tolerance pass.
- Verify the layer graph, native execution history, output hashes, and that the output is genuinely produced by Krita.

A smoke fixture is a technical test; it does not need eight artwork layers and cannot count as one of the 24 finished-art tasks. If a build fails this gate, mark that build `FAIL` and stop further expensive artwork work on that build until the cause is understood. Other builds may proceed independently. Do not claim cross-build parity from a pass on only one build.

## 5. Brush, color, opacity, and pressure acceptance

Perform the calibration on each of the three builds. Select and freeze at least three representative installed presets before testing: a clean/solid preset for measurement, a pressure-responsive preset, and a textured/material preset. At least one tested preset must demonstrate pressure-to-size and at least one must demonstrate pressure-to-opacity; the same preset may satisfy both. Record exact preset names and configuration. A missing preset is `BLOCKED`/unsupported for that build, not an excuse to silently substitute another after seeing results.

### 5.1 Native calibration matrix

For each selected preset, generate and run the Round 12 calibration task:

- Constant-pressure ladder: `0.1`, `0.3`, `0.6`, `0.9`.
- Bidirectional ramps: `0.05 → 0.95` and `0.95 → 0.05`.
- Nominal-size ladder: base size `24`, producing `12`, `24`, and `48` (subject to the implementation's documented bounds).

Use the documented commands:

    krita-agent brushcal generate --preset "PRESET_NAME" --size 24 --output .cache/brush-calibration/PRESET-task.json
    krita-agent job run --file .cache/brush-calibration/PRESET-task.json --wait --session <session.json>

Inspect the actual exported PNG at full resolution. Measure the central stroke body, not anti-aliased edge pixels. Record width and alpha/opacity measurements, the evidence PNG SHA-256, the build, preset, and reviewer.

Project acceptance thresholds (these are test criteria, not claims guaranteed by the implementation):

- **Nominal size:** median measured width must increase in the order 12 < 24 < 48; each adjacent level must be at least 1.20× the preceding level.
- **Pressure-to-size:** only set `pressure_size: true` when the 0.9 row is at least 1.25× the median width of the 0.1 row and the four pressure rows are monotonic, allowing at most a 10% full-range measurement tolerance between adjacent rows.
- **Pressure-to-opacity:** only set `pressure_opacity: true` when the 0.9 row's measured alpha/optical density exceeds the 0.1 row by at least 0.15 on a normalized 0–1 scale and the four rows are monotonic within the same 10% tolerance.
- **Pressure ramps:** the measured response must follow the intended direction in both ramps. Where a reproducible five-bin measurement is available, require Spearman rank correlation of at least 0.8 with the intended pressure sequence. Visible reversals, dropouts, or abrupt discontinuities are a failure even if the endpoints differ.
- **Export and evidence:** all expected strokes are present, non-empty, unclipped, and attributable to the selected preset. The evidence file must be non-empty and no larger than the existing 5 MB profile-evidence limit.

If a textured tip makes a numeric width/alpha measurement unreliable, do not invent a number: mark that measurement `INCONCLUSIVE`, and use the clean/solid preset for the quantitative gate. Textured presets still require visual inspection for continuity, texture, edge quality, and repeatability.

### 5.2 Physical tablet pressure is a separate test

The generated calibration task sends pressure values through the Bridge. It tests how the installed Krita brush preset responds to supplied pressure values; **it does not verify the physical tablet, stylus sensor, Windows driver, or live input path**.

If a pressure-sensitive tablet/stylus is available, separately draw at least five repeated low-, medium-, and high-pressure strokes using the physical pen in Krita. Record the device model, driver version, preset, and a screenshot/export. The response must be repeatable and visibly ordered in the intended channel, without pressure dropouts. If no tablet is available, mark hardware pressure `NOT_RUN`; do not describe the generated Bridge pressure test as physical pen verification.

### 5.3 Color and opacity controls

Using the clean/solid preset on a transparent layer:

- Draw three preselected, clearly distinct colors at 100% opacity. Confirm the actual exported core colors are distinct and correspond to the requested colors after the document profile is applied. If using a colorimetric measurement, require target-color ΔE00 ≤ 5 and pairwise swatch ΔE00 ≥ 20.
- Draw the same color at 25%, 50%, and 100% opacity with pressure fixed. Measured alpha/optical density must increase in that order; the 25%-to-100% difference must be at least 0.25 on a normalized 0–1 scale.
- Change size, color, opacity, and preset between adjacent strokes. Confirm each stroke uses the requested setting and that no previous stroke's setting leaks into the next one.

A color/opacity control passes only when the native PNG visibly contains the expected distinct results and the settings are traceable to the executed strokes. Record any color-profile conversion and do not compare unconverted RGB values across different profiles.

### 5.4 Registering a brush profile

Only after human inspection, record a build-specific profile with `krita-agent brushcal record`. Set capability booleans truthfully. A profile intended for automatic selection must have confidence ≥ 0.8 (the current default selection threshold); otherwise retain the evidence but do not treat the profile as eligible. Recalibrate for every different Krita build. Never reuse a Stable profile as evidence for Next Qt5/Qt6.

## 6. Controlled material A/B experiment

Run one fixed native scene containing at least three materially distinct regions (for example water, foliage, and stone; or cloud, fabric, and metal). Compare the baseline recipe against the candidate recipe.

Hold constant: prompt/scene plan and geometry, canvas, seed, Krita build, brush preset availability, color palette, nominal size, opacity, effort profile, native-step ceiling, and model/provider settings. Change only the material recipe under test. Save both actual KRA/PNG outputs and matching ROI crops. Randomize A/B labels before independent review.

Score each target material ROI from 0–4 on:

1. material recognizability/plausibility;
2. direction and scale of marks relative to the surface;
3. value, color, and lighting coherence;
4. edge handling and absence of mechanical repetition.

A material A/B gate passes when the candidate averages at least 3.0/4 across the selected ROIs, is not below the baseline average, and no individual ROI is below 2.0. Claim a demonstrated improvement only if the candidate exceeds the baseline average by at least 0.5/4. If it is equal or worse, report `NO_IMPROVEMENT`/`FAIL` honestly; do not call a visually neutral result an improvement.

## 7. The 24 finished-artwork tasks

Run the 24 tasks on the designated primary build only after that build passes Section 4. For each task:

1. Initialize a fresh workflow directory and use the frozen task brief. For model-generated generalist planning, use `creative plan --generalist --model ...`; use `--reference <path>` only for the relevant authorized reference task and only with the required upload consent.
2. Inspect the actual ScenePlan v4 proposal, subject hierarchy, required parts/relations, material assignments, bounds, stage goals, compiled native-step budget, and `brush_quality_v12` diagnostics. Reject an invalid or obviously incomplete plan before native painting. Record the plan hash and any unmet advisory floors.
3. Approve the plan explicitly. Execute `creative paint-stage --confirm` **one stage at a time**. After every stage, inspect the actual Krita canvas and layer tree before approving the next stage. Do not run all stages unattended.
4. Export from the real Krita document. Preserve the original KRA and first PNG before review. Perform the fresh-copy KRA reopen and strict pixel/profile comparison. Do not repair a failed original in place; any repair is a new version and the failed version remains in the denominator.
5. Capture the actual Krita window screenshot, the three genuine full-scene stage previews, scene plan, native execution history, layer graph, and per-layer contribution evidence.
6. Require **at least eight genuinely contributing editable paint layers** for every task counted as a finished-artwork result. Each claimed layer must contain visible, purposeful content; empty layers, duplicate names, or metadata alone do not count. A flattened reference import is forbidden.
7. Obtain the independent visual-model review and separate human review described in Section 8. The reviewers must assess actual image pixels and the task contract, not filenames, object labels, step counts, or the model's own planning explanation.
8. Record `creative metrics`, dashboard output, actual wall-clock time, model calls/tokens/cost where available, native step count, and any failure/revision history.

The three stage previews must be genuine Krita previews at meaningful layout, color/block-in, and final/detail boundaries. If a task's stage plan uses different names, record the mapping; do not fabricate a three-image montage from the final PNG.

## 8. Artwork scoring, reviews, and campaign pass threshold

### 8.1 Per-task rubric

Both the independent visual reviewer and the human reviewer score the same six dimensions from 0 to 4. Each score must include a concrete observation tied to visible pixels:

| Dimension | 0 | 2 | 4 |
| --- | --- | --- | --- |
| Brief / reference fidelity | Main request or reference objective absent | Partially fulfilled; major omissions | All key requirements clearly fulfilled |
| Composition / visual hierarchy | Incoherent or unreadable | Understandable but unbalanced | Clear focal hierarchy and deliberate composition |
| Subject recognition / structure | Main subject unrecognizable or structurally broken | Recognizable with major proportion/pose/perspective defects | Clear, coherent, convincing structure |
| Material / light / color | No meaningful separation or contradictory lighting | Some separation; obvious inconsistencies | Materials, values, color, and light reinforce form |
| Purposeful natural mark-making | Mechanical repetition or arbitrary marks dominate | Some purposeful variation; repetition remains obvious | Marks follow form/material/light with controlled variation |
| Completion / cohesion | Fragmentary or unfinished | Mostly complete with visible unresolved areas | Cohesive, intentional, finished presentation |

Scores 1 and 3 are intermediate levels. For reference tasks, fidelity means the predeclared target (composition/structure, palette/material, or style) is recognizable; pixel identity or tracing is not required.

A review passes only when all of the following hold:

- Total score is **at least 18/24**.
- No dimension is below 2.
- Brief/reference fidelity, subject recognition/structure, and completion/cohesion are each at least 3.
- The reviewer records no unresolved critical defect and gives concrete evidence for every required object and spatial relation.
- The visual-model decision is `pass` and the separate human decision is `pass`.

The human reviewer must actually view the final PNG and reopen/view the editable KRA. The visual model must receive actual image pixels and the task contract. The planner cannot review or approve its own work. If the visual model and human disagree, mark the task `DISPUTED` and obtain a fresh independent review; do not average away a rejection. The human verdict remains the final artistic decision.

For each review, bind the record to the exact final PNG and KRA SHA-256 values. Bind the visual review to the reference (when applicable) and all three stage-preview hashes. Include `rubric_scores` and `rubric_evidence` in the review record or a companion `reviews/scorecard.json`. Use the existing `krita-agent-artwork-vlm/2` and `krita-agent-artwork-human/2` review schemas where applicable; the schemas validate evidence binding, not artistic truth.

### 8.2 Campaign-level pass threshold

The 24-task campaign passes only if all of these conditions are met:

- At least **18 of 24** tasks pass their technical gate and both independent reviews.
- Every genre has at least **3 of its 4** tasks accepted, including at least **2 of its 3** held-out text tasks.
- At least **4 of the 6** reference tasks pass.
- All accepted tasks meet the eight-contributing-layer, native KRA/PNG, three-stage-preview, and strict export/reopen requirements.
- No critical safety/privacy/rights violation occurred. All failed, blocked, disputed, and retried tasks remain visible in the final denominator and report.

`BLOCKED`, `NOT_RUN`, or missing review evidence counts as not accepted. Report the numerator and denominator, per-genre counts, reference-task count, score distributions, and every failure. Passing this campaign supports a bounded generalization claim across these six tested genres; it does not prove universal drawing ability or professional-level quality.

### 8.3 Existing artifact auditor limitation

`scripts/artwork_acceptance_audit.py` currently loads the fixed `sunset_alpine_lake.v1.json` contract, including its required landscape objects, 16:9 canvas, and output rules. Run it on `LND-REF` and retain `audit.json`. **Do not run it on the other 23 tasks and call the result a generic audit**: it is not yet a task-manifest-driven campaign auditor. For the other tasks, apply the same strict KRA/PNG/reopen/hash/layer/review checks manually and record them in each task's evidence checklist and the campaign summary. A reusable multi-contract campaign auditor would be a separate implementation task, not something this document claims already exists.

## 9. Performance and workflow reliability

- For each build, run the same bounded three-stage technical fixture three times in fresh documents. Record plan, compile, paint/stage, export, reopen, and review durations from `operation-metrics-v12.jsonl`; verify the hash chain and privacy exclusions.
- Report median and p95 per phase and total wall-clock duration. Do not sum nested operation timings as if they were wall-clock time.
- The current time budget is advisory. Exceeding it is reported, not an automatic failure, unless a separate time SLA was frozen in the campaign manifest before testing.
- A compiled plan must respect its selected native-step ceiling. No silent stroke dropping is allowed.
- Any lost/ambiguous native response remains `unknown_needs_review`; inspect the actual Krita document and ledger before any further action. Never auto-replay an uncertain stroke, stage, export, reopen, or revision.
- Performance numbers are comparable only when build, canvas, plan, preset, seed, and hardware are held constant.

## 10. Evidence layout and final report

Use this local layout; keep it ignored by Git:

    artwork-results/<campaign-id>/
      campaign-manifest.json
      campaign-summary.md
      brush-calibration/
        <build-id>/<preset-id>/task.json
        <build-id>/<preset-id>/evidence.png
        <build-id>/<preset-id>/review.json
      material-ab/
        baseline.kra
        baseline.png
        candidate.kra
        candidate.png
        roi-crops/
        blind-scorecard.json
      tasks/
        <task-id>/
          brief.json
          task-contract.json
          scene-plan.json              # approved-plan index/normalized copy; never a hand-edited substitute
          scene-plan-v4.json
          scene-plan-v3.json
          execution.json
          artwork.kra
          artwork.png
          reopened.png
          reopen-evidence.json
          krita-screen.png
          layer-graph.json
          layer-contributions.json
          stages/
            01-layout.png
            02-color.png
            03-final.png
          reviews/
            visual-model.json
            human.json
            scorecard.json
          audit.json              # required for LND-REF; not a generic audit for other tasks

For each task, preserve the exact source commit, prompt/contract/reference hashes, model identifier, build metadata, plan hash, native execution evidence, KRA/PNG/reopen hashes, reviewer identities/timestamps, rubric scores, and final state. For `LND-REF`, `scene-plan.json` must satisfy the existing auditor's required filename and reflect the actual approved plan; it may be a normalized export/index of the v4/v3 files, never an invented plan. Its `execution.json` must also explicitly record that the reference was not imported as the final artwork. Keep original failed files and repaired successors as separate versions.

`campaign-summary.md` must include:

- source commit and environment/build matrix;
- Tier-2 cloud-native state (do not mark it passed without an actual run);
- each build's smoke and calibration result;
- color/opacity/pressure results and build-specific brush-profile IDs;
- material A/B scores and whether improvement was demonstrated;
- a 24-row task table with technical, visual-model, human, total score, and final state;
- accepted counts by genre and by text/reference task;
- p50/p95 timings and model usage/cost where available;
- failures, blocked items, retries, known limitations, and the exact claim supported by the evidence.

Do not commit raw campaign directories, KRA files, private references, screenshots, API credentials, or local absolute paths. Only publish a sanitized summary or curated preview after separate privacy/rights review and explicit authorization.

## 11. Completion rule

Round 12 local acceptance is complete only when the three-build smoke/calibration results, the controlled material A/B experiment, the full 24-task campaign, all required evidence, and the Section 8 aggregate thresholds are reported. Until then, keep the corresponding checklist items open. A successful technical smoke alone is `local_native_verified`, not `artwork_human_accepted` or `campaign_passed`.
