# Round 13 — Windows stage archive portability and native stroke continuity preflight

**Status:** source implemented on `feat/round13-native-reliability`; offline CI and real installed-build acceptance are separate and must be checked in [R13 acceptance](ROUND13-ACCEPTANCE.md). This is a targeted R13 reliability slice, not completion of all planned R13 tasks or proof of natural brushwork.

Related: [R13–R20 roadmap](ARTIST-ROADMAP-R13-R20.md) · [R12 Windows report](ROUND12-LOCAL-ACCEPTANCE-REPORT.md) · [R12 brush calibration](ROUND12-BRUSH-CALIBRATION.md).

## 1. Windows stage archive paths

R12 discovered that Windows' `Path.relative_to(root)` serialized the stage manifest with `stages\\stage-01-...png`, while the read-only `creative diagnose` code required exactly `stages/stage-01-...png`. That mismatch produced a false "missing" diagnosis for otherwise valid, hash-bound archived Krita PNG evidence.

This change:

- Always records **new** stage preview paths as portable POSIX-style `stages/name.png` using `Path.as_posix()`.
- Accepts **existing** legacy backslash paths and new forward-slash paths when verifying cached `stage_previews`, without rewriting or mutating original evidence.
- In `archived_stage_diagnostics`, validates the canonical relative path against the expected stage file name and builds the actual local path from `root / "stages" / expected_name`. Never interprets an arbitrary path from the manifest as the physical file to open.
- Preserves the exact SHA-256 check for the real file and refuses mismatched names, traversal-like values, lost files, or tampered pixels.

The old R12 failure remains on record. This source patch alone is not a new Windows native PASS; a real R13 local recheck is required.

## 2. Native stroke join risk audit

R12 isolated a reproducible non-continuity artifact: in Stable Krita 5.3.4.1 without `Node.paintPolylineStroke`/`StrokePoint`, automatic multi-point `draw.stroke` becomes several `paintLine` calls. At shared endpoints, semi-transparent presets can deposit alpha twice. Under the R12 tested preset and pressure, 25% alpha changed from 64 at the body to 112 at a join; 50% changed from 128 to 192. On Next builds the continuous native method avoided that specific artifact; forcing segmented strokes reproduced it.

**Important:** There is no evidence-backed general way in the current Stable API to preserve every continuous stroke's pressure, taper and opacity semantics by joining independent `paintLine` calls. We therefore **do not fake a seam fix**, quietly offset endpoints, modify alpha values, or claim full support. The legacy `auto` mode remains backwards compatible and is explicitly a known quality limitation.

New read-only module `src/krita_agent/native_continuity_v13.py`:

- Queries the actual connected Krita build's `capabilities` (only present native symbols, not an artistic verification).
- Inspects compiled `draw.stroke` mode and point count for the *next approved v4 stage* or the *entire approved legacy v3 creative plan*.
- Flags `auto` multi-point strokes on builds without continuous API, explicitly `segmented` multi-point strokes on any build, and explicitly `continuous` strokes on builds where it cannot run.
- Outputs bounded examples, counts, selected Krita/Qt versions, and `artwork_accepted: false`.
- Does not modify the plan, manifest, KRA, drawing commands, or preview files.

### Read-only preflight before painting

```powershell
krita-agent creative native-preflight --directory artwork-results/<run-id> --session .cache/session.json
```

Requires an **approved generalist v4 stage or legacy v3 creative plan** and a currently connected authenticated Krita session. Calls only `capabilities` on the native Bridge; this is **not** an artwork preview or a physical stylus test. The plan is bound to existing SHA/proposal/stage checks before inspection.

### Opt-in guard before executing a stage

```powershell
# Generalist v4: separate approval for each stage
krita-agent creative paint-stage --directory artwork-results/<run-id> --session .cache/session.json --confirm --reject-segmented-joins

# Legacy v3: guard the entire approved plan
krita-agent creative paint --directory artwork-results/<run-id> --session .cache/session.json --reject-segmented-joins
```

When enabled for either legacy `creative paint` or generalist `creative paint-stage`, the workflow checks the native capability report against the approved plan or upcoming stage **before** recording the native submission intent or sending any job. If a multi-point segmented join or unsupported explicit continuous mode exists, the command fails closed with a `TaskError`, leaving the plan or stage in its original approved state for manual review or plan revision.

The flag does **not** assert that all continuous strokes are visually seamless, pressure-responsive, or human-accepted: native brush presets must be calibrated on that build. On an incompatible Stable build with multi-point strokes, a strict v4 stage may be **BLOCKED**, not PASS. Legacy callers that omit the flag retain their historical fallback behavior.

This release is intentionally **opt-in**, because silently upgrading all legacy `draw.stroke` to mandatory continuous would break existing Stable plans. A future version can consider making strict continuity an artist-profile policy after cross-build tests and review.

## 3. Safety and compatibility

- No new arbitrary command, renderer, local file traversal, device access, or external model call is added.
- The Bridge still uses its original localhost token auth and allowlisted `capabilities` command.
- All plan/artifact hashes and stage approval gates stay in place.
- Failure before submission leaves workflow state unchanged; unknown native result is still never retried automatically.
- User files, public image references and `artwork-results/` are not committed to GitHub.
- No legacy ScenePlan v2/v3/v4 schema change; no change to `draw.stroke` native parameter semantics.
- Existing R12 smoke tests establish a historical baseline, not this patch's real native acceptance.

## 4. Offline tests and required subsequent real checks

Offline regression `tests/test_round13_native_reliability.py` tests:

1. All auto/continuous/segmented combinations on mock Stable and mock Next capabilities; 2-point vs multi-point risk.
2. Opt-in guard blocking before `run_longjob`, with unchanged approved stage cursor.
3. Read-only preflight preserving workflow bytes, normal opt-in execution on mocked capable builds, and backwards-compatible CLI flag.
4. Existing Windows-style manifest path correctly running material diagnostics on synthetic **test** PNGs, path traversal rejected, and SHA mismatch detected. These fixture PNGs are not native Krita artwork.

**Required T3:** Re-run on real Windows Stable/Next Qt5/Next Qt6 in a separately authorized local session, including 25% and 50% native pressure/opacity join measurement, Windows archived stage paths, original native KRA/PNG/fresh reopen, and confirm strict mode rejects *before* painting. Mark NOT_RUN/BLOCKED unless actually performed.

**Remaining R13 work after this slice:** investigate whether any supported Stable-native alternative provides continuous semantics, complete actual preset-specific calibration/capability profiles, and integrate all remaining three-build native reliability findings. The source patch does not solve the broader R14–R20 artistic quality deficits.
