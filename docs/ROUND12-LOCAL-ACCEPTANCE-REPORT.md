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

## DeepSeek campaign — public reference library and first formal planning pass

On 2026-11-24 the official DeepSeek models endpoint accepted the user-configured credential and listed `deepseek-flash` with text and image input. This API name resolves to DeepSeek-V4.1-Flash-1017 according to [the provider model documentation](https://api-docs.deepseek.com/quick_start/pricing/). All completion requests went to the DeepSeek official endpoint. This run sent text only.

Five historical, human-authored reference reproductions were located through web search and downloaded from the source institutions. The local library is `artwork-results/reference-library/r12-20261124-public-domain/`. Every file was opened, checked against its SHA-256 and read through the local reference-analysis path. The provenance includes creator, date, rights statement, item URL, image URL and file hash.

| Genre | Reference | Rights source |
| --- | --- | --- |
| Still life | Paul Cézanne, *The Basket of Apples* | [Art Institute of Chicago open-access item](https://www.artic.edu/artworks/111436/the-basket-of-apples) |
| Interior | Vincent van Gogh, *The Bedroom* | [Art Institute of Chicago open-access item](https://www.artic.edu/artworks/28560/the-bedroom) |
| Human | John Singer Sargent, *Mrs. George Swinton (Elizabeth Ebsworth)* | [Art Institute of Chicago open-access item](https://www.artic.edu/artworks/4749/mrs-george-swinton-elizabeth-ebsworth) |
| Animal | Rosa Bonheur, *The Horse Fair* | [The Met public-domain item](https://www.metmuseum.org/art/collection/search/435702) |
| Comic | Winsor McCay, *Little Nemo in Slumberland*, September 5, 1909 | [Library of Congress item and rights advisory](https://www.loc.gov/item/2009616052/) |

The landscape slot retains the repository's locked benchmark. The configuration and inputs of all 24 tasks were frozen before formal planning at source `0739e07`. The full manifest SHA-256 is `8e3d2b21354002ef369df2b3d8be74b04243225d9066d91a2a3625363dfcbb85`. The formal run is in `artwork-results/r12-formal-deepseek-20261124-0739e07/`. The manifest and raw evidence are kept locally.

**Formal result: 18/18 text plans rejected before Krita, 6/6 reference tasks blocked at image upload consent, and 0/24 artworks accepted.** Thirteen plans had a paint coordinate outside its declared subject bounds. Three used an out-of-range material setting, one exceeded the 400-stroke limit for a material intent, and one failed style validation. All original proposals and planning failures are retained. The 18 initial text requests consumed 107,100 reported tokens. A separate one-call diagnostic repeated the first text task with explicit numerical constraints and reached a different validation failure on style. It did not replace the original attempt. No native artwork from the formal matrix was executed and no human review took place.

**Separate text pilot:** The initial generic adapter call returned content that could not be parsed as a JSON object. A fresh one-call pilot, using explicit non-thinking mode and a compact JSON schema example in a local harness, returned valid JSON. This tested DeepSeek compatibility without changing production source. The authenticated Stable Bridge executed 146 planned steps over five individually inspected stages on a 1600×900 canvas. Strict export and fresh reopen both passed with zero differing pixels. Hiding paint layers in a fresh reopened working copy showed 13/13 made measurable pixel changes, including background. The independent reviewer scored **7/24**, failing visual acceptance because the jug remained built from repeated stripes with exposed gaps, large background passes showed lines and dots, and rosemary was almost entirely absent. The pilot is outside the 24-task denominator. Its native files, stage previews, screenshot and hash-bound review are in `artwork-results/r12-deepseek-pilot2-20261124-131200-0739e07/`.

To improve planning reliability, give the model the actual numerical bounds up front and validate the relationship between every point and its subject before compiling. Any corrections should remain new evidence-bearing attempts. Palette and surface coverage still require separate visible quality improvements. Reference generation and external image-based review remain pending explicit campaign upload authorization.

## Reorganized acceptance checkpoint — paused after user review

After the user authorized campaign image uploads, an isolated local harness tested a compact, normalized paint-plan format with DeepSeek Flash. It derives subject bounds from the proposed points, rejects points outside the normalized canvas, and compiles through the existing ScenePlan v4 validators. It uses overlapping opaque native strokes for base areas. No production source was modified. The previous formal planning failures remain recorded.

The three pilot cases in `artwork-results/r12-reorganized-gate-20261124-132554-4313d2f/` were compiled and painted in Krita Next Qt6 `216446e`. The static runner's first invocation stopped before painting due to an incorrect expected status name. The corrected invocation used a separate output directory and preserved the failed startup evidence.

| Pilot | Compiled steps | Contributing paint layers | Strict export and reopen | Independent visual score |
| --- | ---: | ---: | --- | ---: |
| LND-T1 | 117 | 15/20 | Pass, zero differing pixels | 6/24, fail |
| STL-REF | 186 | 19/26 | Pass, zero differing pixels | 6/24, fail |
| ARC-REF | 159 | 17/22 | Pass, zero differing pixels | 6/24, fail |

All three outputs had repeated round stroke ends and lacked convincing form. The pine crown and trunk were disconnected. In the still life, individual apples, the basket rim, and the cloth folds remained unresolved. In the interior, bed and chairs lacked visible support and the room lacked convincing depth. The still-life basket's block-in layer contributed 28,108 changed pixels outside its intended polygon, 27.6% of its visible contribution. The tree canopy's equivalent figure was 47.6%. These are visible layer-difference measurements, with later occlusion included in the result.

In the separate compile-only run `artwork-results/r12-reorganized-ref-preflight-20261124-133522-4313d2f/`, LND-REF and ANI-REF compiled. HUM-REF had an intersecting coverage boundary, and ILL-REF attempted an unsupported brush for an area. None of those four was painted.

The user paused further work after inspecting the visual results. These pilot runs do not count toward formal artwork acceptance. Raw assets, native files, layer measurements and independent reviews remain local and ignored by Git.
