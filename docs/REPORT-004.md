# Runtime acceptance report — 2026-11-03

## Result

The core acceptance checklist has been executed on the installed Windows builds. All 18 automated tests pass. Native painting, pressure dynamics, editable KRA roundtrip, unattended PNG export, job controls, fault rejection and source-tracker checks passed within the scope below. This is a build-specific functional acceptance, not a guarantee for every brush or future Krita version.

## Builds and isolation

- Stable 5.3.4.1 bd6e8d0: PyQt5 / Qt 5.15.7 / Python 3.13.5; segmented fallback confirmed.
- Next 5.4.0-prealpha 2687e5d: PyQt5 / Qt 5.15.7 / Python 3.13.5; continuous API exercised.
- Next 6.1.0-prealpha 2687e5d: PyQt6 / Qt 6.11.0 / Python 3.13.5; continuous API exercised.

Shared user resources were used with configuration/plugin backups rather than a fresh user profile. Only disposable documents and unique output directories were used. Each build ran separately to avoid Krita's single-instance forwarding; ports and session files were distinct. No existing artwork was overwritten. Temporary in-process acceptance instrumentation was removed by reinstalling the repository plugin before the final launch.

## Checklist evidence

- Offline: pytest 18 passed; compileall and git diff --check passed. Added behavior regressions for integer paintLine arguments, export batch-mode restoration (including failure), and failed fetch baseline preservation. No credentials or generated artwork are staged.
- Plugin: installed/enabled, authenticated connection and runtime capability probe succeeded on all three builds. Exact symbol matrices are in acceptance-evidence/acceptance-*.json.
- Drawing: pressure-demo completed 12/12 steps on every build. KRA reopened with Background plus Increasing Pressure, Thin Thick Thin and Constant Pressure paint layers. Existing-file overwrite was rejected. KRA archive integrity checked.
- Presets: real resource names were enumerated. Basic-5 Size, Basic-2 Opacity and Pencil-2 were selected explicitly. All returned PAINT from paintAbility. Preset XML confirmed PressureSize enabled for Size; disabled for Opacity, which uses its pressure opacity curve.
- Visual: inspected straight/increasing, constant and thin-thick-thin demo samples, then 101-point sine curves. Size produced a narrow-wide-narrow curve with stable color; Opacity retained roughly constant width while density varied. Pencil-2 produced a textured soft trace. These are observed preset-specific effects, not independent guarantees for all resources.
- Comparison: on both Next Qt bindings, six preset/mode combinations exported PNG and KRA successfully. Continuous stroke undo restored the blank layer in 1 step; segmented needed 100 steps. Qt5 timings for size/opacity/texture: continuous 0.054/0.031/0.037 s; segmented 1.022/0.759/0.450 s. Single-run timings include completion wait, not a statistical benchmark. Both paths produced connected curves, but segment joins/spacing and accumulated texture differ; segmented output is not equivalent to a single native stroke. Raw Qt6 timings are in extended-qt6.json.
- Faults: locked layer and empty document without paint layers rejected on both Next builds; missing named layer, invalid sample array, wrong credential, unknown command, traversal and overwrite rejected on all three. After process exit, client raises BridgeError. Repeated authenticated request ID returned the cached response and created exactly one layer.
- Controls: 400-step job paused before progress, resumed, and cancelled at checkpoints on all three builds; document remained available. Earlier failed overwrite jobs retained their painted layers and saved original artwork. Single native strokes remain non-interruptible until a checkpoint.
- Network: Windows listener reported only 127.0.0.1. Connections to two actual non-loopback interface addresses were denied. This is a local interface test, not a separate-machine penetration test. Allowlisted protocol rejected an arbitrary exec command.
- Upstream: recorded real source SHA 0b84fb7f8b0d79a5348711c162225a97607383e3 and source baseline. Controlled two-commit fixture detected added and changed signatures and generated JSON/Markdown candidates with kind, priority, source link and suggested test. Synthetic links describe the official source location shape, not published fixture commits. Evidence remains source_seen, never tested_working. Actual git fetch against a deliberately nonexistent local remote failed and left baseline bytes unchanged even with update requested; no network fetch required.

## Fixes

1. Convert QPointF to QPoint at all paintLine call sites (direct, single-point and segmented strokes).
2. Set document batchmode during save/export and restore it in finally, avoiding PNG option dialogs while preserving prior settings.

## Retained limits

Segmented fallback has distinct seams, dynamics, performance and undo granularity. Pressure behavior depends on the selected preset. Jobs are not transactional; partial artwork remains on failure. Very long native strokes can block the GUI. These documented boundaries were evaluated, not removed or represented as failures of unsupported promises.

Raw sanitized evidence lives in docs/acceptance-evidence. PNG/KRA and preset XML remain local outside Git. The final installed Bridge matches repository source; local session credentials remain outside Git.
