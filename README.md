# Krita Agent

English | [简体中文](README.zh-CN.md)

Local Windows automation for Krita's **native painting engine**. Python Controller/SDK, authenticated loopback Bridge running as a Krita Extension, editable multi-layer jobs, pressure strokes, optional advanced editor commands, and upstream source tracking.

## Status

- **Round 1 verified (2026-11-03):** Krita Stable 5.3.4.1, Next Qt5 5.4.0-prealpha and Next Qt6 6.1.0-prealpha passed the documented core acceptance; 18 offline tests were reported passing. See [REPORT-004](docs/REPORT-004.md) for actual limits.
- **Round 2 source authored on \`feat/round2-advanced-workflow\`:** advanced layers/documents, import/reference images, selection, previews, curves, local feedback, persistent job journal, upstream impact classification, optional Docker, and a single-shot workflow CLI. **None of these NEW features has been tested or verified in this round.** See [REPORT-005](docs/REPORT-005.md).
- **No auto-merge, no automatic Krita installation, no CI validation triggered.** The manual CI workflow is opt-in only.

## Architecture

External Windows CLI → authenticated JSON over \`127.0.0.1\` → in-process Krita Python Extension on the Qt GUI thread → native editable Krita documents. No cloud model is required for the core system.

\`\`\`text
src/krita_agent/                  Controller, workflows, geometry, feedback, sessions
plugin/krita_agent_bridge/       Krita Extension, native handlers, journal, optional Docker
tests/                           Offline tests (new tests unexecuted)
scripts/                         Dry-run-first plugin installer and probe helpers
examples/                        Source-controlled example JSON workflows
docs/                            Reports, architecture, plans and API reference
\`\`\`

## Installation and usage

After reviewing the shared Krita user resource directory, install the native Windows controller and explicitly deploy the Bridge. Stable and Next may share plugin directories, so back up first.

\`\`\`powershell
python -m pip install -e .
python scripts\install_plugin.py
python scripts\install_plugin.py --apply
\`\`\`

Enable the Bridge in **Settings → Configure Krita → Python Plugin Manager**, then restart the chosen Krita build. An ordinary Krita launch will not start the bridge without a launch credential.

\`\`\`powershell
krita-agent doctor
krita-agent launch --krita "D:\computer\Krita\Krita_Next\bin\krita.exe" --output-dir "D:\drawings\out" --input-dir "D:\drawings\references"
krita-agent connect
krita-agent capabilities

# Existing first-round native painting task:
krita-agent job run --file ".\examples\pressure-demo.json" --wait

# New second-round source commands (runtime compatibility unverified):
krita-agent invoke layer.tree --params "{}"
krita-agent invoke brush.list --params "{}"
krita-agent workflow --file ".\examples\round2-edit-workflow.json" --wait
krita-agent job recover YOUR_JOB_ID
krita-agent feedback compare ".\a.png" ".\b.png"
\`\`\`

All Bridge commands use an explicit allowlist. For complex JSON on Windows PowerShell, save parameters to a file and invoke \`--params-file\`.

## Native drawing and recovery boundaries

Native stroke pressure is brush-preset-dependent. Next continuous strokes and Stable segmented fallback are different in performance, texture and undo granularity. The new stroke planner supports splines, smoothing and spatial resampling without depending on Qt outside Krita.

Jobs journal states to disk under the authorized output root. After an unexpected shutdown, an unfinished job becomes **interrupted**; no possibly duplicated brush stroke is replayed automatically. A real KRA save point must be managed explicitly; job metadata alone is not a full painting checkpoint.

Inputs are limited to the configured input root; outputs remain inside the authorized output root and do not overwrite existing art by default.

## References

[Round 2 command guide](docs/ROUND2-API.md) · [Architecture](docs/ARCHITECTURE.md) · [Roadmap](docs/ROADMAP.md) · [Verified Round 1](docs/REPORT-004.md) · [Unverified Round 2 implementation](docs/REPORT-005.md).

Original project code is MIT-licensed; Krita and other software are subject to their own licenses.
