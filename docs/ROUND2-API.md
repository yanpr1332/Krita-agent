# Round 2 API and CLI reference (source implemented; runtime unverified)

## Installation prerequisites

First-round Bridge must already be installed and enabled in Krita. After the second-round code is accepted, backup shared user resources before reinstalling the Bridge. Stable and Next may share Python plugin directories.

The user must explicitly launch the expected Krita executable with authorized paths. Do not launch multiple instances on the same port. The Bridge remains disabled when no credential is supplied.

```powershell
krita-agent launch --krita "D:\computer\Krita\Krita_Next\bin\krita.exe" --output-dir "D:\drawings\agent-out" --input-dir "D:\drawings\reference" --dock
krita-agent connect
krita-agent capabilities
```

## Whitelisted direct invocation

Use `krita-agent invoke NAME --params '{...}'` in a shell that preserves JSON quoting correctly, or prefer `--params-file command.json`.

```powershell
krita-agent invoke layer.tree --params "{}"
krita-agent invoke document.list --params "{}"
krita-agent invoke brush.list --params "{\"query\":\"Basic\",\"limit\":40}"
krita-agent invoke preview.canvas --params "{\"width\":512,\"height\":512,\"filename\":\"previews/p001.png\"}"
krita-agent invoke layer.rename --params-file ".\examples\rename-layer.json"
krita-agent invoke layer.set --params-file ".\examples\set-layer.json"
```

Supported *new* command families:

- `layer.tree / inspect / select_id / rename / set / move / duplicate / group / reorder / delete / scale / rotate`
- `document.list / activate / close / crop`
- `selection.rectangle / clear / info / copy / cut / paste`
- `brush.list / inspect`
- `reference.import / image.import`
- `preview.canvas / layer / region`
- `pixel.fill / clear`
- `history.undo / redo`
- `job.history / recover` (recovery inspection only; no automatic replay)

Mutating operations may require `confirm=true`. Stable node IDs are resolved within the active document. Name-only lookup rejects duplicates. Layer property values follow native Krita conventions, e.g., blend mode identifiers instead of UI translated strings.

### Layer edits and preview

```json
{"name": "Line Art", "new_name": "Final Line Art"}
```

Example above is for `layer.rename`. For `layer.set`:

```json
{"name": "Final Line Art", "properties": {"opacity": 0.65, "visible": true}}
```

Preview example:

```json
{"x": 100, "y": 120, "width": 640, "height": 480, "filename": "previews/region-001.png"}
```

For direct pixel modifications:

```json
{"name": "Highlights", "x": 30, "y": 30, "width": 100, "height": 50,
 "color": "#ffcc88", "confirm": true}
```

Do not treat pixel replacement as an undoable native brush stroke without actual testing.

## Drawing and workflows

```powershell
krita-agent draw stroke --file ".\examples\stroke-control.json" --spline --smooth --spacing 3
krita-agent workflow --file ".\examples\round2-edit-workflow.json" --wait
krita-agent workflow --file ".\examples\round2-edit-workflow.json" --archive-dir ".\output\plans"
```

`workflow` accepts an object with an array of `steps`, each a whitelisted `command` and `parameters` pair. Draw stroke step parameters can include `spline`, `samples_per_segment`, `smooth`, `spacing`, etc. The planner produces bounded points before transport.

For older canvas-first JSON jobs, `krita-agent job run --file ...` continues to support the original format.

### Resume safety

```powershell
krita-agent job list
krita-agent job status YOUR_JOB_ID
krita-agent job history YOUR_JOB_ID
krita-agent job recover YOUR_JOB_ID
```

These last two commands report information only. They do not restart interrupted drawing. Running or paused jobs can resume within the *same* live session. Restarted jobs are labelled interrupted and require human inspection.

## Offline preview feedback

```powershell
krita-agent feedback compare ".\output\previews\before.png" ".\output\previews\after.png" --region 100 100 400 400
```

SHA256 works without extra dependencies; pixel-difference metrics require `pip install -e ".[feedback]"`.

## Upstream tracker

```powershell
krita-agent upstream check --repo "D:\computer\Krita\Krita-upstream" --probe "Next=docs\acceptance-evidence\acceptance-next.json" --write-report ".cache\upstream-20261103.md"
```

Only saved symbol presence is imported. Neither this report nor source changes establish new drawing functionality. `--fetch` and baseline changes remain explicit actions.

## Optional Docker

Set `--dock` at launch to register the Qt Krita Agent status Docker. It provides status and checkpoint pause/resume/cancel for the active job. Qt5 and Qt6 compatibility remains unverified for the new Dock.
