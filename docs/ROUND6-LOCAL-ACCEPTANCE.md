# Round 6 local acceptance — 2026-11-10

Source `b03eb7c` was tested with the fixes accompanying this report. The full local suite passed 164 tests and compilation. Stable 5.3.4.1, Next Qt5 5.4.0-prealpha and Next Qt6 6.1.0-prealpha were tested in owned Krita sessions.

| Build | Red 18 px / blue 6 px stroke | Pressure width at start / middle / end | Native continuous stroke |
| --- | --- | --- | --- |
| Stable | 18 / 5 pixels | 1 / 29 / 5 pixels | unavailable, segmented fallback |
| Next Qt5 | 18 / 5 pixels | 1 / 29 / 6 pixels | available |
| Next Qt6 | 18 / 5 pixels | 1 / 29 / 6 pixels | available |

The translucent green stroke was visibly lighter than an opaque one on each build. Initial KRA and PNG, three native stage previews and strict fresh-reopen integrity passed for these technical fixtures. Three presets were separately calibrated on each build. Basic-5 Size showed increasing width, Basic-2 Opacity showed constant width with increasing density, and Pencil-2 showed increasing textured width. Those observations cover one preset each for ink, paint and sketch. They do not constitute three calibrated presets per category, or a complete mapping of every pressure sensor. Unsupported build profiles and unknown preset names were rejected. [Technical results](acceptance-evidence/round6-native.json)

A pressure curve reaching exactly 1 exposed an integer-versus-float normalization inconsistency. Revalidating the plan changed its hash and prevented the creative workflow from reaching native painting. The curve clamp now yields a stable floating-point endpoint and has a regression test.

The Qt6 landscape used a locally authored ScenePlan v3 adapted from an earlier native brush plan, with per-stroke brush settings preserved. Its initial KRA/PNG was archived, but fresh reopen differed at nine pixels by at most one channel level. The strict gate blocked it. A new editable correction layer restored those nine original PNG pixels, and a separately archived v02 passed embedded-image and fresh-reopen integrity. The original rejected v01 remains available. Thirteen paint layers contribute visible pixels. [Local landscape run](../artwork-results/round6-landscape-20261110-092417/)

Independent visual review rejected the actual candidate. The cloud forms remain narrow repeated angular bands, mountain outlines have regularly stepped brush ends, and forest and meadow detail is sparse against the locked benchmark. The review is bound to the final KRA, PNG and native stages. The screenshot and all source artifacts are retained locally. No human verdict was supplied, and the formal artwork audit remains pending. [Visual review](../artwork-results/round6-landscape-20261110-092417/reviews/visual-model.json)

During the contribution check, opening an already-open KRA returned an identity error after adding a duplicate document. The Bridge now refuses the duplicate before opening it. The guard was exercised on all three builds, and the document list remained unchanged. The earlier failed attempt remains in the local run. The underlying Qt6 render-rounding cause is still open.

Preset switching between adjacent strokes, seam comparison, three representative presets for every category, quantitative material/banding benchmarks and complete human-approved artwork remain open. The test used no real model provider or API key.
