# R4.5 artwork acceptance retry — Afterglow at Needle Lake

The 2026-11-07 run on Krita Next Qt5 5.4.0-prealpha (2687e5d) is **not accepted**. Local evidence is in [sunset-brush-20261107-194938](../artwork-results/sunset-brush-20261107-194938/). The benchmark and scene contract were hashed before execution. The first launch attempt could not establish its Bridge connection and remains in its own local run directory.

Krita completed 1,098 continuous native brush strokes in 25 jobs on a 1600 × 900 canvas. The scene used Basic-5 Size, Basic-2 Opacity and Pencil-2 with pressure samples. The execution log records zero shape commands and zero reference imports. Three exported stage images show the composition, the lake and shore, and the finished foreground. The saved screenshot shows the reopened artwork and its layer stack.

The exported RGBA image matches the KRA composite exactly. A fresh reopen and export differ from that image at 9 pixels, by at most one channel level. Hiding each paint layer individually in Krita changed the reopened projection for all 12 authored layers. The per-layer exports and pixel counts remain with the run.

The executor saw recognizable snow peaks, reflected ridges and sunset light, pines, rocks and flowers. The angular ribbon clouds and regularly spaced strokes along the mountain silhouettes leave the benchmark's requirement for varied cloud volume unresolved. An independent visual-model review and an independent human review are still missing. The formal audit is pending those reviews.

The final PNG SHA256 is `def64ff3c53686ee7542fcaa18fdd393b35148330924d23f4759ce1095e8d85a`. The KRA SHA256 is `2d1939b84f2d18bb6ff457caf8e0989984038ac8e0375e0dc44a9cb64939991e`. Raw evidence remains local under the repository's artwork policy.
