# Project roadmap

## Verified first-round baseline (2026-11-03)

The actual local acceptance results are documented in [REPORT-004](REPORT-004.md), not inferred from this roadmap.

- [x] Krita Stable / Next Qt5 / Next Qt6 environment and Bridge connectivity acceptance.
- [x] Native canvas, layers, brushes, pressure stroke (segmented or continuous by build).
- [x] Editable KRA save and reopen, PNG export and overwrite/fault rejection.
- [x] Job queue pause/resume/cancel at step checkpoints; 18 offline automated tests passed.
- [x] Read-only upstream tracking baseline and controlled source-diff fixture.

## Second-round source implementation (unverified)

The branch `feat/round2-advanced-workflow` contains staged code for:

- [ ] **R2-A** Layer metadata, groups, stable node IDs, order, transforms and documents — code authored; runtime pending.
- [ ] **R2-B** Selection, protected pixel region replacement, reference and editable image import — code authored; runtime pending.
- [ ] **R2-C** Spline planning, smoothing, spacing, pressure/sensor interpolation — code authored; runtime pending.
- [ ] **R2-D** Canvas/region/layer preview, digest and optional pixel-diff feedback — code authored; runtime pending.
- [ ] **R2-E** Persistent journal, interrupted-job inspection, manual recovery safety — code authored; runtime pending.
- [ ] **R2-F** Upstream change classification, test suggestions, build evidence matrix — code authored; runtime pending.
- [ ] **R2-G** Modular advanced handlers, bilingual docs, manual CI workflow — code authored; runtime pending.
- [ ] **R2-H** Optional Krita Qt Docker status/control panel — code authored; runtime pending.

Unchecked means new runtime acceptance has **not** been performed, not that source is absent.

## Future

Advanced visual planning, non-destructive partial-pixel masks, durable KRA step snapshots, Qt6 polish, better access controls, optional monitoring and agentic iteration. No production-grade behavior is claimed for these unverified features.
