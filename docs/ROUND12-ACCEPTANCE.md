# Round 12 — integration and acceptance checklist

**Execution protocol:** [Consolidated Windows / Krita local acceptance protocol](ROUND12-LOCAL-ACCEPTANCE-PROTOCOL.md) defines the build matrix, exact brush/color/pressure tests, controlled material A/B, 24-task benchmark, evidence layout, and quantitative pass thresholds. This file tracks execution status; adding the protocol does not mark any native gate passed.

## Tier 1: source and offline regression
- [x] New isolated branch based on merged Round 11 main.
- [x] Quick-sketch / standard / detailed profiles with bounded override and legacy defaults.
- [x] Enforce compiled native-step ceiling before plan archival and approval.
- [x] Hash-chained, bounded operation timing with before/after workflow state.
- [x] Telemetry omits prompts, image bytes, credentials, local paths and exception messages.
- [x] Telemetry failure cannot change a native operation result.
- [x] Read-only CLI summary and dashboard with planned-only brush diagnostics.
- [x] Per-channel pixel drift localization; strict equality remains mandatory.
- [x] Python 3.10 and 3.13 Windows GitHub Actions offline suites: 325 passed on each version.

## Tier 2: cloud native
- [ ] Run real Krita 5.3.4.1 staged fixture on this branch.
- [ ] Collect timings for a bounded multi-stage native run.
- [ ] Verify drift diagnostics against a real fresh-KRA reopen.

## Tier 3: consolidated Windows / artwork campaign
- [ ] Stable Qt5, Next Qt5 and Next Qt6 smoke.
- [ ] Confirm actual pressure response of selected presets.
- [ ] A/B material recipes at fixed scene, seed, canvas and preset.
- [ ] Held-out campaign: 18 text tasks (six genres × three complexity levels) plus six reference tasks (one per genre; the landscape slot uses the locked project benchmark) — 24 total.
- [ ] Preserve KRA, PNG, execution, stage, layer, visual and separate human-review evidence for every task.

## Non-claims
Offline CI is not native verification. Planned brush diversity is not proof of visible dynamics or natural painting. Time budget is advisory. Drift localization is not a root-cause fix. No complete artwork or human acceptance is claimed.

- [x] Profile-aware per-subject brush diversity floor with advisory/enforce modes and deterministic regression scenes.
- [x] Generalist brush diversity evaluated across the complete logical subject rather than isolated stage-layer fragments.

- [x] Expanded native brush calibration task with constant-pressure ladder, increasing/decreasing pressure ramps and nominal size ladder.
- [x] Added evidence catalogue validation for malformed, unreviewed, wrong-build and tampered profiles.
- [ ] Run the calibration matrix in the user's installed Krita builds and manually inspect exported native results.


## Tier 3 pass criteria

A finished-artwork task counts as accepted only when its native technical gate passes, it has at least eight genuinely contributing editable paint layers, three genuine Krita stage previews, strict KRA export/reopen equality (RGBA and color profile), and both independent visual-model and human reviews pass.

Each reviewer uses the six-dimension 0–4 rubric in the local protocol: at least 18/24 total, no dimension below 2, and brief/reference fidelity, subject structure/recognition, and completion each at least 3. The campaign target is at least 18/24 accepted overall, at least 3/4 accepted in every genre (including at least 2/3 text tasks), and at least 4/6 reference tasks. Failed, blocked, disputed, and retried tasks remain in the denominator.

The existing `artwork_acceptance_audit.py` is bound to the fixed sunset-alpine-lake contract; use it for the landscape reference task only. It is not a generic auditor for the other 23 tasks. See the protocol for the exact evidence and manual checks.
