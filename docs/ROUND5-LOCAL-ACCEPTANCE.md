# Round 5 local acceptance, 2026-11-09

The local technical checks ran against the installed Stable 5.3.4.1, Next Qt5 5.4.0-prealpha and Next Qt6 6.1.0-prealpha builds. The run used branch `feat/round5-autonomous-creative-workflow` at `400273a` with the fixes in this workspace. The [local evidence directory](../artwork-results/round5-20261109-123022/) retains the native results, test failures and generated artifacts.

| Check | Result |
| --- | --- |
| Offline suite and source compilation | 129 passed locally |
| ScenePlan v2 preflight and ScenePlan v3 supplied-plan compilation | Passed. The native planner inputs were locally authored candidates. |
| Native painting, export, three stage previews and dashboard | Passed on Stable, Next Qt5 and Next Qt6 |
| KRA reopen and export pixel comparison | Stable and Next Qt5 were exact. The Next Qt6 candidate changed at five pixels by at most one level per channel. |
| Safe continuation | Stable and Next Qt6 restored an actual verified KRA copy and submitted only the remaining batch. A dropped restore reply resulted in one restore request and zero suffix submissions. |
| Reply-loss fault injection | On Next Qt6, paint and revision each reached the native job queue once. The export case performed one actual KRA save. Reinvocation was blocked in all three cases. |
| Bounded native revision and version retention | Stable rendered a 25 px brush against the ROI boundary. The pixel change was confined to the approved region. The revision used a new layer, preserved the pre-revision KRA checkpoint and archived both versions. |
| Critique, revise, export and deliver | Completed the Stable technical fixture with a local provider double. The fixture exercised PNG and crop handling and workflow state transitions. |
| Full artwork | Pending. The Next Qt6 candidate retained a real editable KRA, screenshot and three native stages. Hiding layers individually showed 29 of 32 layers contributed visible pixels. Cloud bands and peak contours remained repetitive and the sky retained visible banding. |

Two changes came out of acceptance. A revision export now validates and reuses previously archived stage previews, allowing a second version without overwriting the first stages. Native revisions use a rectangular selection to clip the rendered brush footprint, and require an unselected document before creating the pre-revision checkpoint.

Real model planning and visual critique remain pending by request. The local provider double produced test responses only and does not count toward model or artwork acceptance. The Qt6 candidate still needs an independent visual review, human approval, and a formal artifact audit after both reviews. Its reopen pixel difference is retained as a separate technical finding.

[Native matrix](../artwork-results/round5-20261109-123022/native-summary.json) · [Stable revision proof](../artwork-results/round5-20261109-123022/stable/native-revision-proof.json) · [Fault-injection proof](../artwork-results/round5-20261109-123022/native-fault-proof.json) · [Qt6 dashboard](../artwork-results/round5-20261109-123022/qt6/dashboard.html)

## Next Qt6 retest

The [second native run](../artwork-results/round5-retry-20261109-124417/qt6/) used a newly prepared local ScenePlan v3 with more distinct cloud groups and separate dark rock and snow passes. Krita produced the KRA, PNG, three native stages, a reopened export and a screenshot. Hiding each layer in Krita showed 30 of 33 paint layers affected the visible composite.

Two fresh copies of the first Qt6 KRA each reproduced a difference of five pixels, at most one level in red and green. The new KRA reopened and exported with zero differing RGBA pixels. The first file's mismatch remains reproducible. [Prior comparison](../artwork-results/round5-retry-20261109-124417/qt6/prior-reopen-retest.json) · [Retest result](../artwork-results/round5-retry-20261109-124417/qt6/retest-result.json)

Independent visual review rejected the new candidate against the fixed benchmark. All eight objects and six spatial relationships were recognizable. Hard bands across the sky and lake, repeated stepped peak contours, and sparse forest and meadow detail remained. The review is bound to the exact PNG, KRA and three stage previews. Human review remains pending. [Candidate](../artwork-results/round5-retry-20261109-124417/qt6/artwork.png) · [Independent review](../artwork-results/round5-retry-20261109-124417/qt6/reviews/visual-model.json)

The targeted local review, audit, planner and revision suite passed 19 cases. No configured model API was invoked. Real provider planning and the provider-based pixel critique remain open.

## Qt6 exact pixel repair and visual re-acceptance

The original failing KRA was repaired on a copy. An editable layer restores the original PNG values at exactly the five recorded coordinates. The repaired PNG is byte-identical to the original PNG. The embedded KRA composite and three freshly reopened copies each matched the original PNG at every RGBA pixel. Existing layer IDs, names, ordering and recorded properties were preserved. [Repaired original KRA](../artwork-results/round5-qt6-repair-20261109-125527/repair-exact/repaired-exact.kra) · [Original repair proof](../artwork-results/round5-qt6-repair-20261109-125527/repair-exact/proof.json)

The visual pass refined the second native candidate with editable Krita strokes. It replaces the hard sky and water bands with gradual washes, redraws the three stepped peak outlines and adds clustered shore conifers, ripples and meadow details. The visual polish also produced a five-pixel reopen difference. A separate editable correction layer restored the reviewed PNG exactly. The delivered KRA's embedded projection and three fresh reopen exports matched that PNG at every pixel. Native layer ablation identified 29 layers with a visible contribution. The refinement was performed on the prior Round 5 candidate using direct native Bridge edits. [Final KRA](../artwork-results/round5-qt6-repair-20261109-125527/final-verified/artwork.kra) · [Final proof](../artwork-results/round5-qt6-repair-20261109-125527/final-verified/proof.json)

The independent visual reviewer passed the final variant against the fixed benchmark and bound the verdict to the corrected KRA, unchanged PNG and three stage previews. Forest and meadow detail remains sparser than in the benchmark. Human approval and the formal combined audit are pending. The real model-provider checks remain deferred by request. [Final visual review](../artwork-results/round5-qt6-repair-20261109-125527/final-verified/reviews/visual-model.json)

For a future repository change, add a fresh-copy reopen and RGBA comparison to creative archive verification, separately reporting export integrity and reopen stability. Keep a stable KRA/PNG pair as a new version when a local mismatch is corrected. A second useful change would be validated brush changes within each semantic object, which would reduce banding caused by dividing tonal work into single-brush passes.
