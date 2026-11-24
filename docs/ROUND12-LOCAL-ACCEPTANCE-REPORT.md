# Round 12 local Windows acceptance — 2026-11-24

Tested source `6ed4ba8c24a5c43b800dac8aae2952410d2b63ab` (merged Round 12) from a clean checkout on `docs/round12-local-acceptance`. **The staged local smoke passed on all three builds. The complete campaign has not passed.** The material A/B failed its quality threshold, and the 24 finished-artwork tasks are blocked.

| Level | Result | Scope |
| --- | --- | --- |
| Tier 1 Windows CI | PASS | Existing 325-test results on Python 3.10 and 3.13. |
| Local offline | BLOCKED for one case | Python 3.14.6: 324 passed. One Round 10 test failed to create its test symlink (`WinError 1314`), before invoking the application code under test. This reproduces on the unmodified baseline. |
| `cloud_native_verified` | NOT_RUN | No Tier 2 cloud run for this exact source was started in this local campaign. Prior rounds' results remain historical. |
| `local_native_verified` | PASS for staged smoke | 9/9 three-stage runs, zero differing RGBA pixels in export and reopen comparisons with matching profile metadata within each pair. |
| `artwork_human_accepted` | BLOCKED | No candidate artwork from the 24-task benchmark was produced or human-reviewed. |
| `campaign_passed` | BLOCKED | 0/24 accepted, with the required planning model and references pending. |

## Native builds and evidence

Windows 11 build 26300. The installed Bridge Python sources matched the checked-out source byte-for-byte after line-ending normalization. Each build ran in a separate owned process with an authenticated loopback session, a new disposable document per sample, and a unique input/output directory. Metadata, executable paths, Bridge file hashes and build capabilities are in the ignored local evidence. The document color space was RGBA/U8 sRGB. The active display ICC and physical input driver were not verified.

| Build | Reported version | Qt | Three-stage smoke | Export / fresh reopen mismatches | PNG ICC payload |
| --- | --- | --- | --- | --- | ---: |
| Stable | 5.3.4.1 `bd6e8d0` | 5.15.7 | 3/3 PASS | 0 / 0 per attempt | none |
| Next Qt5 | 5.4.0-prealpha `216446e` | 5.15.7 | 3/3 PASS | 0 / 0 per attempt | 9,080 bytes |
| Next Qt6 | 6.1.0-prealpha `216446e` | 6.11.3 | 3/3 PASS | 0 / 0 per attempt | 9,080 bytes |

Each native attempt ran the same 512×384 plan and used 78 compiled steps against a selected ceiling of 300. The nine runs retained the authentic three-stage previews, execution ledgers, editable KRA, first export, fresh-reopen export, artifact hashes, pixel measurements, layer graph and dashboard. Each stage made a nonzero contribution. Stable changed 1,608 / 89,024 / 173 pixels across sketch / block-in / detail. Both Next builds changed 1,604 / 89,124 / 170. Stage sheets were visually inspected. These results establish within-build consistency. The PNG encoding/profile metadata and marks differ between Stable and Next.

The initial runner erroneously compared the normal stage PNG to its identical layout alias at the next stage. These interrupted smoke attempts are retained as test-harness failures. The corrected run grouped previews by stage identity and started fresh documents. The independent calibration jobs from the first run are valid. On all nine completed smoke attempts and both A/B results, `creative diagnose` reproduced the existing Windows archive path mismatch. Krita produced the preview files, but the diagnostic reader rejected the backslash separator in the archive record. The prior fix remains isolated in local commit `14b0ddd` and was excluded from this baseline run.

## Performance and workflow metrics

Each row gives measured p50/p95 in milliseconds. Wall time includes the technical review of each stage and the diagnostic probe. The plan event includes compilation, and export includes archive and fresh reopen. Nested phases must not be added to estimate wall time. With three samples, the wall and other once-per-run p95 values are the observed maxima. Metrics hash chains verified on all nine runs, and sampled logs contained no workflow prompt, token or absolute workflow directory. Provider reviews, physical input latency and usage/cost were not measured.

| Build | Plan + compile | Approve | Paint stage | Archive | Reopen | Export | Diagnostic probe | Wall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Stable | 128/132 | 42/43 | 2,413/3,092 | 351/388 | 2,624/2,994 | 3,442/3,757 | 9/13 | 11,765/12,171 |
| Next Qt5 | 118/122 | 45/46 | 2,248/3,409 | 311/333 | 3,242/3,333 | 4,061/4,280 | 11/15 | 11,964/12,657 |
| Next Qt6 | 121/137 | 44/44 | 2,139/3,255 | 319/338 | 3,431/3,622 | 4,231/4,597 | 10/10 | 12,382/12,425 |

## Native brush matrix and controls

Nine native calibration PNGs were generated and inspected for the frozen presets `b) Basic-5 Size`, `b) Basic-2 Opacity` and `c) Pencil-2`. All builds met nominal-size ordering for the two clean presets. Basic-5's measured widths at 0.1/0.3/0.6/0.9 were 1/1/7/18 px on Stable and 1/1/8/18 px on both Next builds. Its increasing and decreasing width ramps each reached Spearman ρ ≈ 0.975. Basic-2 kept a 22 px measured width over the pressure ladder and increased optical density from 0.089 to 0.813. Its bidirectional density ramp correlations were 0.900 on Stable and 1.000 on both Next versions. The Pencil-2 sample showed a faint low-pressure line, textured edges and thinning through both ramps. Its soft tip makes the numerical width near the lowest pressure inconclusive. Numeric measurements and evidence SHA-256 values are retained locally.

The three control colors matched the requested core RGB values, and all three builds produced the intended ordered 25% / 50% / 100% alpha (64/128/255) along the regular stroke body on a transparent layer. Alternating preset, size, color and opacity produced distinct expected adjacent marks. On Stable only, the partial-opacity strokes darken around the shared point at the segment join (112/192 instead of 64/128). Stable also showed repeated dark deposits at intermediate points of both Basic-2 ramps. Thus the pressure response is observable in Stable, but **Stable fails the ramp continuity criterion**. Both Next builds passed the tested size and opacity mapping and control criteria. Physical tablet verification is `NOT_RUN` and human profile registration is `BLOCKED`; there are no new profile IDs.

## Controlled material A/B

Stable rendered both 512×384 variants with matching scene geometry, seed 57, palettes, brush settings, stage layout, effort and 300-step ceiling. Only the placement setting changed from staggered to blue noise. The actual compiled steps were 115 and 119 respectively. Both outputs passed strict native integrity and fresh reopen. The independent reviewer received randomized image labels and examined real final exports and ROI crops before the label key was disclosed.

| Recipe | Plaster / room | Figure materials | Ceramic | Mean | Wall time |
| --- | ---: | ---: | ---: | ---: | ---: |
| Staggered (A) | 0.50 | 0.25 | 0.75 | 0.50/4 | 16.30 s |
| Blue noise (B) | 0.50 | 0.25 | 0.75 | 0.50/4 | 19.63 s |

**FAIL / NO_IMPROVEMENT.** Both variants left broad gaps, neither established the figure materials, and the vessel showed sparse marks with incomplete form. Neither reached 3.0 average or 2.0 per material. The hash-bound ROI scorecard retains the actual observations.

## Artwork benchmark state

The locked landscape reference and scene contract were hashed. An ignored draft of the other tasks was prepared without exposing held-out prompts in this report. A shared authorized planning model is unavailable and the five additional rights-confirmed references were not supplied. All 24 technical entries are `BLOCKED` at preflight, with visual and human reviews `NOT_RUN`. No model calls or image uploads went through a provider API. Counts are 0/24 overall, 0/4 per genre, 0/18 text, and 0/6 reference. There are no artwork score distributions.

| Task | Technical | Visual | Human | Score | Final |
| --- | --- | --- | --- | --- | --- |
| LND-T1 | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| LND-T2 | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| LND-T3 | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| LND-REF | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| STL-T1 | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| STL-T2 | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| STL-T3 | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| STL-REF | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| ARC-T1 | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| ARC-T2 | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| ARC-T3 | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| ARC-REF | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| HUM-T1 | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| HUM-T2 | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| HUM-T3 | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| HUM-REF | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| ANI-T1 | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| ANI-T2 | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| ANI-T3 | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| ANI-REF | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| ILL-T1 | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| ILL-T2 | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| ILL-T3 | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |
| ILL-REF | BLOCKED | NOT_RUN | NOT_RUN | — | BLOCKED |

## Local evidence

- `artwork-results/r12-20261124-111910-6ed4ba8/` — initial harness attempts and nine valid calibration outputs plus controls.
- `artwork-results/r12-20261124-112221-6ed4ba8/` — corrected smoke and performance evidence, two native A/B outputs, blind scorecard, and held-out task draft.

Both runs are ignored by Git. No KRA, PNG, private reference, local absolute path or credential is included in the commit.

## Follow-up on Windows archive paths, stroke joins and material coverage

Native follow-up ran from clean `bbfdf01` with the same code as `main` at `6ed4ba8`. The separate archived-stage verification used `14b0ddd` in an isolated checkout. Evidence is retained under `artwork-results/r12-followup-20261124-113955-bbfdf01/`.

### Archived-stage diagnostics — fix verified

The real Windows archives from all nine smoke attempts and both original A/B runs were copied into the follow-up evidence directory. On `14b0ddd`, `CreativeWorkflow.diagnose_materials()` verified all **11 archives and 33 canonical stage PNGs** with the recorded Windows separators and hashes. The focused Round 8 suite passed **34 tests**, including the traversal and tampering checks. The original evidence was left intact. The fix remains on `fix/windows-stage-archive-path`.

### Stroke join isolation — reproducible segmented-mode limitation

A transparent canvas used `b) Basic-2 Opacity`, size 24, constant pressure and the same color and geometry. Two repeats compared two-, three- and five-point automatic strokes, explicit segmented strokes, and explicit continuous strokes where supported. Results were identical across repeats. The real Bridge response identified the actual stroke path used.

| Build and execution path | 25% alpha, body / interior join | 50% alpha, body / interior join |
| --- | --- | --- |
| Stable, automatic two-point | 64 / 64 | 128 / 128 |
| Stable, automatic three- or five-point (segmented fallback) | 64 / 112 | 128 / 192 |
| Next Qt5 and Qt6, automatic or explicit continuous | 64 / 64 | 128 / 128 |
| All three builds, explicit segmented three-point | 64 / 112 | 128 / 192 |

Stable lacked the continuous API in this build. The Next controls reproduced the same dark deposits only when forced through the segmented path. The measured values match two overlapping alpha applications at shared segment endpoints. This identifies the segmented fallback as the cause for the tested fixture. The Stable continuity criterion remains **FAIL**. Continuous strokes passed this focused check on both Next builds.

### Material coverage A/B — failed visual threshold

Stable rerendered the same blue-noise scene with the same geometry, seed, brushes, colors, stage layout and 300-step ceiling. Only the render spacing changed from 75 to 36 pixels. Both original KRA/PNG pairs passed strict export and fresh reopen with zero differing pixels. The blinded reviewer inspected both final exports and all six ROI crops, and those hashes were verified before unblinding.

| Spacing | Compiled steps | Wall time | Room / person / cup nonwhite coverage | Blind room / person / cup | Mean |
| --- | ---: | ---: | --- | --- | ---: |
| 75 px (B) | 119 | 18.16 s | 59.2% / 20.7% / 3.7% | 0.50 / 0.25 / 0.75 | 0.50/4 |
| 36 px (A) | 257 | 47.05 s | 98.9% / 43.4% / 8.8% | 0.75 / 0.25 / 0.75 | 0.58/4 |

Coverage counts pixels with at least one RGB channel 20 levels away from white inside fixed rectangular crops. Coverage includes any underlying marks in each crop. The 0.083-point score change is below the required 0.5-point improvement. The 0.58 mean and all three ROI scores are also below the 3.0 and 2.0 pass thresholds. **FAIL / NO_IMPROVEMENT.** Denser strokes covered the wall more fully while leaving recognizable form and lighting unresolved. The next material revision should establish base values and coherent surface directions before adding detail.

### Formal campaign readiness

The repository's 1600×900 landscape benchmark matches the locked contract hash. The 24-task campaign remains `BLOCKED` because it needs one configured and authorized planning model and five further rights-confirmed references. The existing default online planner would require a configured provider credential for the first planning call. No paid provider was used during this follow-up. An API key alone does not resolve reference rights or human review.
