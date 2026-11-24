# Round 13 — native reliability source slice acceptance

**Source branch:** `feat/round13-native-reliability` (independent from merged R12 and R13–R20 docs PR).  
**Status:** new code and offline regression authored; **real Windows/native acceptance NOT_RUN** until explicitly executed. Do not promote previous Round 12 native successes to this new commit.  
**Scope of this PR:** Windows archived stage path portability, hash-preserving read-only diagnostics, and opt-in native stroke-join capability audit. The full [R13 roadmap](ARTIST-ROADMAP-R13-R20.md) additionally requests build-specific brush calibration, true Stable fallback research and cross-build native testing.

## 1. Historical failure baseline (not R13 PASS evidence)

From [R12 local Windows report](ROUND12-LOCAL-ACCEPTANCE-REPORT.md):

- Native 3-build staged smoke: 9/9 passed source state at R12, with tested KRA export/fresh reopen strict RGBA consistency.
- `creative diagnose` on Windows could reject valid stored stage previews when manifest path separators were backslashes.
- On Stable Krita 5.3.4.1, `b) Basic-2 Opacity` automatic multi-point stroke used segmented fallback, with 25% body/join alpha `64/112` and 50% `128/192`; Next continuous modes had `64/64`, `128/128`. Separate paintLine calls at interior joins caused extra deposits.
- 24-task complete artwork acceptance not passed. Technical drawing smoke is not artistic acceptance.

## 2. Implemented source scope and offline evidence checklist

| Gate | Target | Status | Evidence / pending work |
| --- | --- | --- | --- |
| Git branch isolation | New feature branch from reviewed main SHA | PASS | `feat/round13-native-reliability`, base `8600ec9f1d708c76d41a2b15ec05c7886da4730e` |
| Windows path format | New archive uses portable POSIX relative paths | SOURCE_IMPLEMENTED | `creative_workflow.py` |
| Legacy manifests | Backslash stage paths accepted only if exact expected relative path | SOURCE_IMPLEMENTED | `render_quality_v1.py`, `creative_workflow.py` |
| Tamper safety | Missing/renamed/traversal/hash mismatch remains refused | SOURCE_IMPLEMENTED | `test_round13_native_reliability.py` |
| Read-only connected preflight | Approved v4 stage or v3 legacy plan and actual build symbol inventory, no drawing | SOURCE_IMPLEMENTED | `native_continuity_v13.py`, `native-preflight` |
| Opt-in no-join risk | Strict flag on `paint` or `paint-stage` blocks before status mutation/native job submit | SOURCE_IMPLEMENTED | `paint --reject-segmented-joins`, `paint-stage --reject-segmented-joins` |
| Legacy workflows | No default mode change, no new ScenePlan/Bridge command | SOURCE_IMPLEMENTED | Older smoke and CLI tests must pass |
| Windows CI Py3.10 / 3.13 | Full repository pytest | NOT_RUN | Check actual GitHub Actions workflow on PR |
| Cloud Linux real Krita | Native smoke of changed workflow | NOT_RUN | If suitable runner and authorization available |
| Windows Stable actual opacity endpoints | Native 25%/50% body/join evidence | NOT_RUN | Requires user-approved local Krita session |
| Windows Next Qt5/Qt6 actual native continuity | Real KRA/Png and join evidence | NOT_RUN | Requires user-approved local Krita session |
| Human artistic evaluation | Natural brushwork and whole artwork | NOT_RUN | Not claimed in this reliability slice |

**Important:** `SOURCE_IMPLEMENTED` is descriptive only, **not** a PASS of native functionality. These rows must be updated only with actual workflow/test evidence and commit SHA.

## 3. Native T3 handoff steps (once authorized)

1. On a separate test document/session for each Krita build (Stable, Next Qt5, Next Qt6), record `capabilities` response with Krita/Qt version, compare `Node.paintPolylineStroke` and `StrokePoint` presence. Capability presence is not yet actual rendering proof.
2. Prepare the exact same sample multi-point stroke with `b) Basic-2 Opacity`, size 24, matching foreground color and 25% then 50% opacity. Compare automatic, explicit segmented, and explicitly continuous (where supported) with two-, three- and five-point paths. Measure body and interior join alpha. Preserve PNG+KRA and one immutable run directory per attempt; check actual prestroke background.
3. For an approved R7/R8 v4 test run, call `creative native-preflight --directory ... --session ...` on each build. Confirm read-only operation and correct risk report, then run `paint-stage --confirm --reject-segmented-joins` against multi-point plan. On missing continuous API it must reject **before** any new layer, stroke or manifest stage transition. On supported build it may submit after approval; verify native pixels separately.
4. Execute a three-stage task and native export on each build, confirm stage previews saved inside authorized Krita output root and archived with portable slash paths. `creative diagnose` must verify all images and compute ROI deltas; a copied legacy manifest with backslash paths must still work and remain byte-identical.
5. Check export integrity and fresh KRA reopen with strict RGBA and color-profile consistency; preserve all failed originals with hashes and separate remediation versions.
6. Recheck cross-build connection, state journaling, refusal to replay uncertain side effects and older v2/v3/v4 sample plans.
7. Mark unsupported and failed features honestly; do **not** claim the Stable join defect fixed simply because strict mode refuses it. If no safe continuous Krita API exists, record `BLOCKED` for quality-critical multi-point strokes on Stable.

## 4. Security/compatibility constraints

- No arbitrary shell/IPC added, no external model call or image upload in this patch.
- Strict checking is **opt-in**; legacy `draw.stroke` `auto` and explicitly segmented modes remain supported but may have visual seams.
- `native-preflight` does not archive or rewrite user artwork and cannot certify real brush pressure/color response.
- The archive path parser accepts only the expected file under the authorized run's stages directory and still verifies SHA.
- Existing stage source hash and per-stage user confirmation remain mandatory; failed/unknown native results are not automatically retried.
- No changes to the frozen R12 artwork contract, and nothing in this patch counts as human acceptance.

## 5. Handoff to the next R13 slice / R14

After code tests and native review: determine whether Stable has a genuine continuous API alternative; if not, expose a clearly documented capability-limited artist profile and require user choice before sending risk-prone multipt strokes. Complete real build-specific calibration and cross-build matrix. R14 semantic/geometry restructuring can proceed independently on a separate branch but must not be counted as R13 remediation.
