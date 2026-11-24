# REPORT-012 — Round 12 integration source milestone

**Branch:** `feat/round12-generalist-acceptance`  
**Base:** merged Round 11 main `b8080aad623c13f77e97d7a450d9e3ff58a16688`

## Implemented
1. Added quick-sketch / standard / detailed planning profiles with default native-step ceilings of 2,500 / 6,000 / 10,000.
2. Added an explicit compiled-step budget enforced before the plan is archived.
3. Added advisory time targets to legacy and generalist planning prompts.
4. Added privacy-safe, hash-chained operation timings and a `creative metrics` command.
5. Extended the read-only dashboard with timing and planned brush/pressure summaries.
6. Added per-channel pixel drift statistics and difference bounds without changing strict acceptance.
7. Added offline regression coverage for profiles, budget enforcement, telemetry privacy/integrity, dashboard and drift diagnostics.

## Validation status
- Source implementation: complete for this milestone.
- Offline tests: pending GitHub Actions.
- Cloud native timing / fresh-KRA reopen: pending.
- Windows Stable / Next Qt5 / Next Qt6: pending.
- Whole-artwork / multi-genre / human acceptance: pending.

Metrics report planned values and command durations only; they do not infer that native painting happened or that an artwork is accepted.
