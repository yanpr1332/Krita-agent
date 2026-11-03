# Round 3 API / CLI user guide (NEW CODE, NOT YET RUNTIME VERIFIED)

All commands require the opt-in Krita Bridge enabled and launched with a random token on local loopback. Run `krita-agent --help` **only during a later validation turn**.

## Example: safe resumable drawing

```powershell
krita-agent launch --krita "D:\computer\Krita\Krita_Next\bin\krita.exe" --output-dir "D:\drawings\agent-out" --input-dir "D:\drawings\references" --dock
krita-agent connect
krita-agent checkpoint create
krita-agent checkpoint list
krita-agent checkpoint inspect YOUR_CHECKPOINT_ID
krita-agent checkpoint restore YOUR_CHECKPOINT_ID --confirm
# Only if the job snapshot and suffix are trustworthy:
krita-agent checkpoint resume YOUR_CHECKPOINT_ID --confirm
```

A standalone checkpoint does not carry a job suffix. Jobs can include a `checkpoint.create` step; metadata records the exact step boundary and full step SHA256. An unclean shutdown marks unfinished jobs interrupted. **No automatic replay after restart.** Explicit resume opens a newly named KRA copy and submits only suffix steps; refusal is safer than guessing.

## Independent pixel transactions

Invoke Bridge commands using JSON from an explicit file (recommended on PowerShell):

- `pixel.transaction.fill`, `pixel.transaction.clear`, `pixel.transaction.patch`
- `pixel.transaction.inspect`, `pixel.transaction.undo`, `pixel.transaction.redo`
- `clipboard.save`, `clipboard.load`, `clipboard.inspect`

Example fill input:

```json
{"name":"Ink","x":40,"y":50,"width":90,"height":60,
 "color":"#ffddaa","confirm":true}
```

These edits are limited to RGBA U8 and up to 500000 pixels per transaction, with durable reversible before/after data and checksums. Undo/redo in the pixel transaction API is **NOT** the same as Krita's native Undo. A changed current buffer refuses unsafe undo.

Clipboard filename is relative to output/clips with extension `.kclip`, saving only compressed BGRA pixels with SHA256. It is not integrated with the system clipboard.

## Native non-destructive editing

- `mask.create`: `kind=transparency|selection`, name, parent_id or parent_name. Transparency mask requires an active selection by default.
- `mask.inspect`, `mask.selection.set`.
- `filter.list`, `filter.layer.create`, `filter.mask.create`, `filter.configure`: create filter layers/masks non-destructively with `confirm=true`.
- `selection.combine`: mode `replace/add/subtract/intersect/xor` plus rectangle; `selection.modify`: feather/grow/shrink/border/invert/smooth.
- `color.info`, `color.profiles`, `color.convert`: conversion first returns a dry-run plan; requires `confirm=true` and a matching verified current KRA checkpoint ID.
- `brush.profile`, `brush.presets`: metadata, no promise of pressure effectiveness.

All native APIs are version-dependent; these are **candidate implementations until actual build acceptance**.

## Structured painting

```powershell
krita-agent scene --file ".\examples\round3-scene.json" --output ".\output\scene-steps.json"
# User inspects JSON before requesting execution:
krita-agent scene --file ".\examples\round3-scene.json" --submit --wait
```

A scene contains explicit documents (optional), layers, brush metadata, geometric primitives, cubic Bézier and sensor-aware strokes, optional previews and checkpoints. It is not a free-text image model.

## Reference-guided local revisions

First obtain a full-resolution preflight Krita PNG and a target PNG of the same dimensions, and choose an unambiguous paint layer ID from `layer.tree`.

```powershell
krita-agent revision plan --before ".\out\previews\before.png" --target ".\references\goal.png" --layer-id "NATIVE-UUID" --output ".\plans\revision.json"
# Inspect the generated diff rectangle and restrictions first:
krita-agent revision apply --plan ".\plans\revision.json" --confirm
```

Safety restrictions: canvas area at most 2 million pixels; changed rectangle at most 500000 pixels; source must be the only visible paint layer, unlocked, normal blend, opacity 1.0; current projection must match the plan's RGBA hash; target reference must remain inside the input sandbox. Application creates an immutable checkpoint, duplicates the source layer, patches only the planned region, hides the original, exports a preview, and saves a **new** KRA. After-preview and target are compared. One explicit application only; no silent retries or arbitrary natural-language edits.

## Upstream / build evidence

```powershell
krita-agent upstream catalog --repo "D:\computer\Krita\Krita-upstream" --from-sha BEFORE_SHA --to-sha HEAD --write-report ".cache\round3-upstream.json"
krita-agent capability-registry list --file ".cache\build-evidence.json"
krita-agent capability-registry record --file ".cache\build-evidence.json" --build "Next-Qt6" --symbol "Document.createTransparencyMask" --state "tested_working" --evidence "path\to\actual-passing-evidence.json" --confirm-reviewed
```

Do not record `tested_working` until a *real* applicable passing test report exists. The sample registration command is illustrative only and **must not be run against an implementation-only report**. Source status never becomes working status automatically.

## Recording problems

The following are intentionally not claimed: general semantic AI image critiques, continuous automatic creative iteration, automatic lost-stroke recovery from unsaved images, native undo of all raw pixel operations, arbitrary multi-layer goal-image patching, or full ICC colorimetric accuracy.
