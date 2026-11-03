# Runtime acceptance procedure — executed 2026-11-03

Executed against Stable, Next Qt5 and Next Qt6. See REPORT-004.md for actual results, evidence and limitations. The checklist below remains the repeatable procedure.

## 0. Safety preparation

1. Ensure Stable and Next have separate executable directories. Back up shared plugin and resource data.
2. Use a fresh test profile or a disposable environment. Do not overwrite existing art.
3. Check the installer's dry-run listing; do not silently deploy to the shared pykrita location.
4. Ensure the local port is free, and use a different --session and --port for each instance.

## 1. Offline quality gate (to run only when authorized)

- python -m pip install -e ".[test]"
- python -m pytest
- python -m compileall -q src plugin
- lint or static review as appropriate.
- Confirm no tokens or generated artwork are tracked.

## 2. Krita plugin gate

- Install explicitly with scripts/install_plugin.py --apply after reviewing resource path.
- Enable extension in Python Plugin Manager and restart.
- Launch target from krita-agent launch --krita ABSOLUTE_EXE.
- krita-agent connect and krita-agent capabilities.
- Save actual Stable and Next version/build IDs, Python and Qt bindings, symbol presence.
- Missing StrokePoint or paintPolylineStroke should result in segmented fallback, not silently claimed continuous stroke.

## 3. Native painting and editable KRA gate

- In an isolated output directory, execute krita-agent job run --file examples/pressure-demo.json --wait.
- Confirm three named layers, brush preset availability, and paintAbility.
- Inspect straight, curved, constant, increasing and thin–thick–thin samples.
- Verify pressure-to-size and pressure-to-opacity using presets configured for those mappings.
- Compare continuous vs segmented: seam, brush spacing, texture, performance and undo history.
- Save a fresh layered KRA and PNG. Reopen the KRA and inspect layer structure.
- Confirm repeated jobs do not silently overwrite existing files.

## 4. Fault and control gate

- Test missing/locked layer, invalid stroke data, disconnected Bridge, wrong credential, bad path, duplicate request ID.
- Pause and resume a multi-step job; cancel between strokes; check progress and partial-art preservation.
- Validate that non-loopback traffic, arbitrary command execution and output outside the allowed directory are denied.
- Compare Qt5 and Qt6 where both are installed.

## 5. Upstream feature tracker gate

- Record source SHA and baseline; use a controlled synthetic commit with added and changed signatures.
- Produce JSON / MD candidates with source link, kind, risk, suggested tests.
- Confirm source_seen is NOT tested_working.
- Test --fetch failure handling and baseline preservation, only if authorized.

## Known design boundaries

- The in-process Bridge must be installed and enabled separately. It does not attach to an existing uninstrumented Krita process.
- User-specified pressure values do not prove a visually pressure-sensitive preset.
- Two paintLine calls are not identical to a continuous stroke; only real Next behavior can be called tested.
- Jobs are not transactional: a failed job can leave a partial document.
- Long, single-stroke painting commands can still block the GUI until a checkpoint.
