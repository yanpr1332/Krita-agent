# Krita Agent

[English](README.md) | [简体中文](README.zh-CN.md)

Local Windows controller for Krita's **native** painting engine: Python CLI and SDK, authenticated loopback Bridge running inside Krita, editable-layer jobs, pressure-aware strokes, and upstream API change tracking.

**Development status (2026-11-03): first-round source implemented, NOT verified against either installed Krita build.** No tests, application launch, plugin deployment, painting or KRA acceptance were performed in this development round, as requested.

Architecture: External controller → 127.0.0.1 JSON protocol with a random credential → Krita Python Extension on the Qt GUI thread → native Krita painting engine. The ordinary Python interpreter does not import Krita.

## Source layout

- src/krita_agent: CLI, client, task validation, geometry, session management, upstream tracker
- plugin/krita_agent_bridge: Qt5/Qt6-compatible import strategy, GUI dispatch, native painting and job queue
- scripts/install_plugin.py: explicit, backup-first plugin deployment, dry-run by default
- examples: structured pressure and multi-layer tasks
- tests: offline Python and synthetic Git tests (present but not executed)
- docs: architecture, design, milestone plan, acceptance checklist and development reports

## Getting started (instructions, not verification results)

From a native Windows PowerShell in the repository:

~~~powershell
python -m pip install -e .
python scripts\install_plugin.py
# Carefully check the shared Krita resources; then explicitly:
python scripts\install_plugin.py --apply
~~~

Enable Krita Agent Bridge in Krita's Python Plugin Manager, then restart the application. The Bridge is inert during ordinary Krita launches; it requires the controller-injected credential.

~~~powershell
krita-agent doctor
krita-agent launch --krita "D:\computer\Krita\Krita_Next\bin\krita.exe"
krita-agent connect
krita-agent capabilities
krita-agent draw demo --wait
krita-agent job run --file ".\examples\pressure-demo.json" --wait
~~~

Launch creates a local session file with a random authentication token. Connecting does not start Krita. Outputs are confined to a selected local directory (default: Pictures/KritaAgent) and overwriting is opt-in. Stable and Next may share user plugin resources; use care before installing.

## Upstream feature tracker

~~~powershell
krita-agent upstream snapshot --repo "D:\computer\Krita\Krita-upstream"
krita-agent upstream init --repo "D:\computer\Krita\Krita-upstream"
krita-agent upstream check --repo "D:\computer\Krita\Krita-upstream" --write-report ".cache\upstream.md"
~~~

By default it does not fetch remote changes or change a baseline. Source changes are candidates, not evidence of working installed APIs. Explicit --fetch and --update-baseline opt in to these operations.

See [Chinese guide](README.zh-CN.md), [acceptance checklist](docs/ACCEPTANCE.md), and [development report](docs/REPORT-003.md). Original project code is MIT-licensed; Krita and third-party components retain their own licenses.
