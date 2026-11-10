# Round 6 local re-acceptance — 2026-11-10

The rerun used branch `feat/round6-brush-dynamics` at `b03e929` plus the transparency-mask stroke change in this workspace. All 165 offline tests and source compilation passed. Real Krita checks used Stable 5.3.4.1, Next Qt5 5.4.0-prealpha and Next Qt6 6.1.0-prealpha.

| Native check | Stable | Next Qt5 | Next Qt6 |
| --- | --- | --- | --- |
| Adjacent Basic-5 Size / Basic-2 Opacity switching | passed | passed | passed |
| Evidence-backed ink / paint profile switching and wrong-build rejection | passed | passed | passed |
| Black at 25% opacity, one / two strokes | RGB 191 / 143 | RGB 191 / 143 | RGB 191 / 143 |
| Constant-pressure join | no gap in sampled pixels, segmented fallback | no gap in sampled pixels, continuous | no gap in sampled pixels, continuous |
| Three presets per ink, sketch, paint, texture and erase category | measured | measured | measured |
| Three presets painted on a real transparency mask | measured | measured | measured |

Seam results cover one straight constant-pressure fixture. Stable lacks Krita's continuous-stroke API and correctly rejects a request for it. No general claim is made about all brushes or paths.

For each build, four force levels were recorded for three presets per category. On a real transparency mask, Basic-1 produced the same 26 px width and density at all four levels. Basic-2 Opacity stayed 24 px wide while density increased. Basic-5 Size widened from 1 to 20 px. The unsupported Basic-1 pressure response is recorded as an observation rather than promoted as pressure-sensitive. Eraser checks started with a dark painted layer so that removed pixels were measurable. Full measurements and SHA-bound image paths are retained in the local run. [Numerical results](acceptance-evidence/round6-reacceptance.json) · [Local calibration files](../artwork-results/round6-adjacent-20261110-101309/)

The Bridge previously rejected direct strokes on transparency masks. It now accepts line and stroke commands only when the mask is unlocked and Krita reports `paintAbility() == "PAINT"`. All three documented builds produced real changed mask pixels for Basic-1, Basic-2 Opacity and Basic-5 Size. Paint-layer and selection-transfer checks remain separate.

The optimized Qt6 landscape was painted through the Round 6 per-stroke ScenePlan workflow. Its authored plan adapts the prior local Needle Lake drawing and includes the sky, lake and peak refinements. The initial version had a five-pixel fresh-reopen difference and was retained. A second KRA with a separate five-pixel correction layer passed both embedded export and fresh-reopen checks. The independent visual review passed the optimized image, while noting that distant trees, meadow and cool ripples are still sparser than the benchmark. Twenty-eight layers had measurable visible contributions. Human review and the formal artwork audit remain pending. [Candidate PNG](../artwork-results/round6-landscape-20261110-101445/artwork.png) · [Candidate KRA](../artwork-results/round6-landscape-20261110-101445/artwork.kra) · [Visual review](../artwork-results/round6-landscape-20261110-101445/reviews/visual-model.json)

A limited comparison against the earlier Round 5 Needle Lake candidate sampled rows 0–119 at x=50–199. Adjacent mean RGB jumps above three levels fell from 2 to 0, and the largest sampled jump fell from 17.542 to 2.0. The compiler's sum of repeated trajectory signatures was 94 for 889 strokes in the earlier plan and 646 for 1,969 strokes in the new plan. That diagnostic counts geometric repetition and is not a visual-quality score. Single-run native batch times, including checkpoints and polling, were 109.147 seconds for 957 steps and 344.590 seconds for 2,564 steps respectively. These different plans are not a controlled performance benchmark.

On the known Qt6 five-pixel case, refreshing the top layer and then all paint layers left the same five one-level differences against the original pre-reopen PNG. Saving the refreshed document and reopening it retained those differences. The editable correction layer restores the original pixels and the strict gate detects the drift, but this experiment does not establish or fix the underlying Krita rendering cause. The user-requested human verdict and the source of that drift are still open.
