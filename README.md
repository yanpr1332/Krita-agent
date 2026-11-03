# Krita Agent

English | [简体中文](README.zh-CN.md)

Krita Agent is a Windows-native Python/Qt automation system for **real editable Krita painting**. An authenticated loopback IPC channel connects an external Controller to a Krita Python Extension running on the GUI thread. The project deliberately separates source implementation, offline test results and actual installed-build acceptance.

## Project status (2026-11-03)

| Milestone | Status | Evidence |
| --- | --- | --- |
| Round 1: Native painting and basic tasks | **Accepted** on Stable and both Next builds | [REPORT-004](docs/REPORT-004.md) |
| Round 2: Editable workflow, previews, images and Dock | **Accepted**, 34 offline tests passed and pixel/Dock real-build checks recorded | [REPORT-006](docs/REPORT-006.md), [REPORT-007](docs/REPORT-007.md) |
| Round 3: Durable checkpoints, non-destructive masks, revision planner and upstream registry | **Accepted on the three installed builds; 57 offline tests passed** | [REPORT-009](docs/REPORT-009.md), [Round 3 acceptance checklist](docs/ROUND3-ACCEPTANCE.md) |

Acceptance covers three specific builds: Krita Stable 5.3.4.1, Next Qt5 5.4.0-prealpha and Next Qt6 6.1.0-prealpha. They are not blanket future-version guarantees. Round 3 native, crash-recovery, pixel and actual Dock acceptance is recorded in [REPORT-009](docs/REPORT-009.md). No CI was triggered.

## Main architecture

```text
src/krita_agent/              External Controller, task protocol, geometry,
                              structured scenes, local image revisions,
                              feedback, Git upstream inventory
plugin/krita_agent_bridge/    Krita Python Extension, native nodes/brush,
                              masks, checkpoints, per-pixel reversible history,
                              compressed clips, optional local Dock
tests/                        Offline regression tests (57 passed)
scripts/                      Dry-run plugin installer, acceptance helpers
examples/                     JSON geometry / workflow examples
docs/                         Milestone reports, architecture, acceptance
```

## Setup and existing first/second round API

The installer previews changes by default. **Krita Stable and Next may share the user plugin directory.** Back it up before an explicit install:

```powershell
cd "D:\computer\Krita\Krita-agent"
python -m pip install -e .
python scripts\install_plugin.py
# Review user resources / backup before choosing:
python scripts\install_plugin.py --apply
```

Enable the Bridge in **Settings → Configure Krita → Python Plugin Manager**, restart Krita and launch it explicitly with Controller credentials:

```powershell
krita-agent launch --krita "D:\computer\Krita\Krita_Next\bin\krita.exe" --output-dir "D:\drawings\out" --input-dir "D:\drawings\references" --dock
krita-agent connect
krita-agent capabilities
krita-agent workflow --file ".\examples\round2-edit-workflow.json" --wait
```

Installed-build evidence and limits are recorded in REPORT-009.

## Round 3 commands (installed-build acceptance recorded)

```powershell
# Real KRA snapshot + explicit inspect / restore to a fresh file copy:
krita-agent checkpoint create
krita-agent checkpoint list
krita-agent checkpoint inspect CHECKPOINT_ID
krita-agent checkpoint restore CHECKPOINT_ID --confirm

# Build an inspectable structured drawing plan:
krita-agent scene --file ".\examples\round3-scene.json" --output ".\plans\scene.json"

# Analyze a target image and plan a safe bounded local edit:
krita-agent revision plan --before ".\before.png" --target ".\reference\goal.png" --layer-id LAYER_ID --output ".\plans\revision.json"
krita-agent revision apply --plan ".\plans\revision.json" --confirm

# New mask/filter/color and separate reversible pixel commands use:
krita-agent invoke mask.create --params-file ".\examples\round3-mask.json"
krita-agent invoke color.info --params "{}"

# Local upstream source signature inventory (not runtime proof):
krita-agent upstream catalog --repo "D:\computer\Krita\Krita-upstream" --from-sha OLD_SHA --to-sha HEAD
```

An interrupted job is never replayed on startup. The restoration process verifies a stored KRA checksum and can explicitly restore a fresh copy and submit only the suffix after an authenticated job checkpoint. Direct RGBA U8 pixel undo is a separate, checksum-protected journal, **not** the Krita native Undo stack. The image revision planner requires an approved preview/target pair, a single visible fully opaque normal paint layer and a bounded patch.

Optional image-difference planning requires `pip install -e ".[feedback]"`. The core Controller has no required cloud API or generative model.

## Documentation and contribution

[Round 3 API](docs/ROUND3-API.md) · [Round 3 acceptance checklist](docs/ROUND3-ACCEPTANCE.md) · [Current roadmap](docs/ROADMAP.md) · [Architecture](docs/ARCHITECTURE.md) · [Round 3 implementation report](docs/REPORT-008.md) · [Contributing](CONTRIBUTING.md).

The project-authored code is MIT-licensed. Krita and all third-party dependencies retain their own licensing terms.
