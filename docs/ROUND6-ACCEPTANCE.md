# Round 6 brush flexibility — implementation and acceptance gates

## Source and offline contracts

- [x] Object palettes support validated named brush styles and per-stroke overrides.
- [x] Native compilation emits the exact effective `brush.configure` between
  strokes, avoids redundant configuration, and restores the baseline.
- [x] Continuous strokes carry bounded, deterministic arc-length pressure
  curves, optional speed sensitivity and seeded modulation; authored pressure
  is preserved when no curve is present.
- [x] Bézier and freeform brush styles pass through the existing native
  allowlist; no new arbitrary command channel is introduced.
- [x] Evidence-backed per-stroke preset categories fail closed without a
  reviewed calibration profile/build.
- [x] Per-object `min_strokes` budgets and up to 900 elements are supported
  under the existing global/IPC safety bounds.
- [x] Brush-diversity and sparse-detail diagnostics are labeled
  **diagnostic_only**, never artwork approval.
- [x] ROI revisions support multicolor/multisize native strokes and retain
  new-layer, source-hash, checkpoint and confirmation protections.
- [x] Dedicated offline regression tests and a complete ScenePlan example
  were added to the repository.

## Required real-build native acceptance (NOT YET CLAIMED)

- [ ] Stable 5.3.4.1: confirm preset, color, size, opacity changes across
  adjacent strokes; inspect actual pixel evidence and original KRA layers.
- [ ] Next Qt5 5.4.0-prealpha: verify real continuous pressure and no join seams.
- [ ] Next Qt6 6.1.0-prealpha: verify pressure curves, opacity accumulation,
  profile switching and compatibility with fresh-KRA reopen integrity checks.
- [ ] Calibrate at least three representative presets per category; demonstrate
  that an unsupported pressure mapping is not misreported as working.
- [ ] Paint a coherent, complete landscape with natural clouds, mountains,
  water and foreground detail; run the locked reference artwork audit and
  independent human/visual-model reviews.
- [ ] Quantify remaining banding, periodic marks, pressure fidelity and native
  runtime cost against the earlier Needle Lake result.

Offline compilation or CI success is **technical-source evidence only**; it
does not make these native or visual gates pass.
