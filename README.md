# Krita Agent

**Round 8 source development (native/artwork QA pending):** opt-in material-aware native brush recipes with directional flow, bounded blue-noise mark placement, layered size/pressure/color, coverage edge stitching, and read-only real stage-pixel diagnostics. Existing ScenePlan v4 plans remain supported. See [Round 8 API](docs/ROUND8-API.md), [Acceptance](docs/ROUND8-ACCEPTANCE.md) and [R7 failed-art baseline](docs/ROUND7-ARTWORK-ATTEMPTS.md). Windows CI [#42990495459](https://github.com/yanpr1332/Krita-agent/actions/runs/42990495459) passed 223 offline tests on each Python version; this does not prove human-like art.

**Round 7 source update (new branch, native QA pending):** free-form ScenePlan v4 subjects, staged painting intents (`gesture`, `coverage`, `accents`), deterministic safe Krita stroke compilation, optional model proposal, and individual `creative paint-stage --confirm` approvals. See [Round 7 API](docs/ROUND7-API.md) and [Acceptance](docs/ROUND7-ACCEPTANCE.md). No natural-artwork or real-build acceptance is asserted by the source branch.

**Future artistic direction (proposed):** develop Krita Agent into a generalist, human-like painting assistant: natural, purposeful brushwork; people/animals/still life/architecture as well as landscapes; reference-based repainting and reusable technique learning. The detailed Round 7–12 implementation and acceptance plan is in **[Generalist Artist Roadmap](docs/ARTIST-ROADMAP-R7-R12.md)**. API-based model *evaluation* is intentionally scheduled for Round 11; authorized model-based planning may be used earlier.

**Round 6 verified scope:** per-stroke size, color, opacity and preset changes, pressure curves, and flexible revisions have native-fixture evidence on three tested Krita builds. See [Round 6 API](docs/ROUND6-API.md), [Acceptance Checklist](docs/ROUND6-ACCEPTANCE.md) and [Native Reacceptance](docs/ROUND6-REACCEPTANCE.md). Independent human artwork review and the rendering-drift root-cause fix remain pending.

**Artwork acceptance policy (R4.5):** native drawing command tests do not prove a complete illustration. The original visual reference, fixed contract, required local KRA/PNG artifacts and independent reviews are documented in [Artwork Acceptance](docs/ARTWORK-ACCEPTANCE.md). Local agent instructions: [AGENTS.md](AGENTS.md).

English | [简体中文](README.zh-CN.md)

Krita Agent is a Windows-native Python/Qt automation system for **real editable Krita painting**. An authenticated loopback IPC channel connects an external Controller to a Krita Python Extension running on the GUI thread. The project deliberately separates source implementation, offline test results and actual installed-build acceptance.

## Project status (2026-11-08)

| Milestone | Status | Evidence |
| --- | --- | --- |
| Round 1: Native painting and basic tasks | **Accepted** on Stable and both Next builds | [REPORT-004](docs/REPORT-004.md) |
| Round 2: Editable workflow, previews, images and Dock | **Accepted**, 34 offline tests passed and pixel/Dock real-build checks recorded | [REPORT-006](docs/REPORT-006.md), [REPORT-007](docs/REPORT-007.md) |
| Round 3: Durable checkpoints, non-destructive masks, revision planner and upstream registry | **Accepted on the three installed builds; 57 offline tests passed** | [REPORT-009](docs/REPORT-009.md), [Round 3 acceptance checklist](docs/ROUND3-ACCEPTANCE.md) |
| Round 4: Layer-aware painting, large jobs, brush profiles and ScenePlan v2 | **LOCAL ACCEPTANCE RECORDED** | [REPORT-011](docs/REPORT-011.md), [ROUND4-ACCEPTANCE](docs/ROUND4-ACCEPTANCE.md) |
| Round 5: Autonomous creative workflow, semantic planner, pixel critic and revisions | **SOURCE IMPLEMENTED; 129/129 OFFLINE CI PASSED ON EACH PYTHON VERSION; NATIVE ARTWORK ACCEPTANCE PENDING** | [ROUND5-API](docs/ROUND5-API.md), [ROUND5-ACCEPTANCE](docs/ROUND5-ACCEPTANCE.md) |
| Round 6: Multi-style brush control and pressure dynamics | **SOURCE IMPLEMENTED; THREE-BUILD NATIVE FIXTURES RECORDED; HUMAN ARTWORK AUDIT PENDING** | [ROUND6-REACCEPTANCE](docs/ROUND6-REACCEPTANCE.md), [ROUND6-ACCEPTANCE](docs/ROUND6-ACCEPTANCE.md) |

Prior acceptance covers specific Stable/Next builds: Krita Stable 5.3.4.1, Next Qt5 5.4.0-prealpha and Next Qt6 6.1.0-prealpha, not newer features automatically. Round 3 results are in [REPORT-009](docs/REPORT-009.md). Round 4 local tests and installed-build acceptance are documented in [REPORT-011](docs/REPORT-011.md).

## Main architecture

```text
src/krita_agent/              External Controller, task protocol, geometry,
                              structured scenes, local image revisions,
                              feedback, Git upstream inventory
plugin/krita_agent_bridge/    Krita Python Extension, native nodes/brush,
                              masks, checkpoints, per-pixel reversible history,
                              compressed clips, optional local Dock
tests/                        Round 4: 82 offline tests passed
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


## Round 4 commands

    krita-agent graph capture --output ".\plans\graph.json"
    krita-agent overlay plan --before ".\images\before.png" --target ".\references\goal.png" --graph ".\plans\graph.json" --output ".\plans\overlay.json"
    krita-agent overlay apply --plan ".\plans\overlay.json" --confirm
    krita-agent longjob plan --file ".\examples\round4-longjob.json"
    krita-agent longjob run --file ".\examples\round4-longjob.json"
    krita-agent brushcal generate --preset "b) Basic-5 Size" --output ".\plans\calibration.json"
    krita-agent scene-v2 compile --file ".\examples\round4-scene-v2.json"
    krita-agent feedback-v2 review --current ".\images\current.png" --goal ".\references\goal.png" --graph ".\plans\graph.json" --output ".\plans\review.json"

The multi-layer workflow creates an independent top-level editable overlay only
for fully opaque target changes. It does not reverse arbitrary blending/masks.
The long-job scheduler submits bounded native jobs serially and stops if any
response has uncertain effects, rather than blindly retrying. ScenePlan v2 is
deterministic JSON; no LLM or third-party Krita plugin is installed.

## Round 5 autonomous creative workflow (source implementation; native acceptance pending)

~~~powershell
# Offline structural preflight; no Krita connection or document mutation
krita-agent scene-v2 validate --file ".\plans\landscape.json" --min-painted-layers 8

# Explicitly continue only from a verified KRA checkpoint boundary
krita-agent longjob resume --file ".\examples\round4-longjob.json" --ledger ".\logs\long-job-ID.json" --confirm
~~~

Long-job continuation first opens a fresh copy of the verified checkpoint KRA; an ambiguous restore reply blocks further submissions. The visual and human artwork-review records are now hash-bound to the exact reference, final PNG, editable KRA and stage previews. This improves evidence integrity; it does not automatically judge artistic quality or claim that a complete illustration has been accepted. See [Artwork review v2](docs/ARTWORK-VLM-REVIEW.md).

R5 now implements an explicit creative lifecycle: natural-language (opt-in JSON-capable model) or human-provided ScenePlan v3 → semantic objects and brush strategies → approved Krita native painting → real exported PNG critique → approved ROI-limited new-layer revision → versioned KRA/PNG delivery. The external model never gets direct Bridge command authority; native drawing is never silently retried. The internal VLM critique does not count as independent artwork acceptance. See [Round 5 API](docs/ROUND5-API.md) for all `krita-agent creative` commands. Run-scoped actual Krita stage previews and a static local HTML dashboard are also provided; a live Krita Dock integration is still deferred. No new Krita third-party plugin is required.

## Documentation and contribution

[Round 4 API](docs/ROUND4-API.md) · [Round 4 acceptance checklist](docs/ROUND4-ACCEPTANCE.md) · [Round 4 acceptance report](docs/REPORT-011.md) · [Release notes](docs/RELEASE.md) · [Round 3 API](docs/ROUND3-API.md) · [Round 3 acceptance checklist](docs/ROUND3-ACCEPTANCE.md) · [Current roadmap](docs/ROADMAP.md) · [Architecture](docs/ARCHITECTURE.md) · [Round 3 implementation report](docs/REPORT-008.md) · [Contributing](CONTRIBUTING.md).

The project-authored code is MIT-licensed. Krita and all third-party dependencies retain their own licensing terms.
