# Round 12 — integration and acceptance checklist

## Tier 1: source and offline regression
- [x] New isolated branch based on merged Round 11 main.
- [x] Quick-sketch / standard / detailed profiles with bounded override and legacy defaults.
- [x] Enforce compiled native-step ceiling before plan archival and approval.
- [x] Hash-chained, bounded operation timing with before/after workflow state.
- [x] Telemetry omits prompts, image bytes, credentials, local paths and exception messages.
- [x] Telemetry failure cannot change a native operation result.
- [x] Read-only CLI summary and dashboard with planned-only brush diagnostics.
- [x] Per-channel pixel drift localization; strict equality remains mandatory.
- [ ] Python 3.10/3.13 CI and full offline suite (pending).

## Tier 2: cloud native
- [ ] Run real Krita 5.3.4.1 staged fixture on this branch.
- [ ] Collect timings for a bounded multi-stage native run.
- [ ] Verify drift diagnostics against a real fresh-KRA reopen.

## Tier 3: consolidated Windows / artwork campaign
- [ ] Stable Qt5, Next Qt5 and Next Qt6 smoke.
- [ ] Confirm actual pressure response of selected presets.
- [ ] A/B material recipes at fixed scene, seed, canvas and preset.
- [ ] Held-out campaign: six genres × three unseen text tasks plus six authorized reference tasks (24 total).
- [ ] Preserve KRA, PNG, execution, stage, layer, visual and separate human-review evidence for every task.

## Non-claims
Offline CI is not native verification. Planned brush diversity is not proof of visible dynamics or natural painting. Time budget is advisory. Drift localization is not a root-cause fix. No complete artwork or human acceptance is claimed.

- [x] Profile-aware per-subject brush diversity floor with advisory/enforce modes and deterministic regression scenes.
