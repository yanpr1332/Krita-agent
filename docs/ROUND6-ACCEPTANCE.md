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

## Required real-build native acceptance

Initial results are in [ROUND6-LOCAL-ACCEPTANCE](ROUND6-LOCAL-ACCEPTANCE.md). The retest and remaining human review are recorded in [ROUND6-REACCEPTANCE](ROUND6-REACCEPTANCE.md).

- [x] Stable 5.3.4.1: actual adjacent preset, color, size and opacity switching verified on a disposable native fixture.
- [x] Next Qt5 5.4.0-prealpha: continuous pressure variation and a constant-pressure straight join were checked in native pixels.
- [x] Next Qt6 6.1.0-prealpha: pressure curves, two-pass opacity, reviewed profile switching and fresh-KRA integrity were exercised.
- [x] Calibrate at least three representative presets per category; demonstrate
  that an unsupported pressure mapping is not misreported as working.
- [x] Repaint the locked benchmark candidate and record independent visual review. The optimized candidate passed that review.
- [ ] Record independent human review of the optimized KRA and PNG, then run the formal artwork audit.
- [x] Record measured sky banding, repeated-trajectory diagnostics, sampled pressure response and single-run native timing against the earlier Needle Lake run. These are bounded diagnostics.

Offline compilation or CI success is **technical-source evidence only**; it
does not make these native or visual gates pass.
