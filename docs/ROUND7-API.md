# Round 7 — generalist staged ScenePlan v4 API

**Source implementation only.** This round introduces a generalist, reviewable, intent-to-native-stroke controller. GitHub offline CI is not installed-Krita acceptance and does not prove that its output resembles human painting. Natural material mark-making, anatomy, reference learning and independent API art evaluation remain Round 8–11 goals.

## What changed and why

Round 6 could vary parameters on thousands of strokes but its object ontology favored landscapes. Round 7 separates an arbitrary **subject** ("human figure", "ceramic cup", "room", "dog", "bicycle") from materials and brush styles. The model describes a drawing *purpose*, spatial guide and stage; the safe local compiler expands that into bounded, deterministic original Krita brush strokes. The model does not need to output thousands of native pen coordinates.

This design reuses existing trusted components: ScenePlan v3 validation, v2/workflow allowlist, scheduler checkpoints, native Bridge, KRA/PNG archival, strict Export Integrity and Reopen Stability, revision/critique bindings and human review gates.

## ScenePlan v4 source contract

- `schema`: `krita-agent-scene/4`.
- `document`: width and height each 1..8192, area at most 32M pixels, name.
- `subjects`: 1..24, each has unique lowercase ID, descriptive free-form `kind`, name, `materials` list, `bounds` on canvas, optional parent/depth and an explicit baseline brush with `color` and `size`.
- `styles` on each subject: up to 24 validated named palette entries with brush overrides/pressure dynamics from Round 6.
- `stages`: 3..6 strictly increasing phases selected from `sketch`, `block_in`, `form`, `material`, `detail`, `polish`. First must be sketch; last detail or polish. Each phase has unique ID, goal and 1..32 paint intents.
- `intents`: each references an existing subject ID, declares a material from that subject, includes an explicit `purpose` and a bounded kind-specific guide. Optional brush/style and pressure settings are validated through Round 6.
- All geometry must lie within the subject's bounds; subjects can be parented but may not be cyclic. Unknown keys, untrusted commands, degenerate guides, self-intersecting polygon coverage and invalid styles are refused.

Three initial high-level intent kinds:

| Kind | Geometry | Native effect | Bound |
| --- | --- | --- | --- |
| `gesture` | Guide path with 2..128 `[x,y]` points | One native brush stroke for gesture/contour | 1 stroke |
| `coverage` | Simple polygon, spacing, angle, seeded slight jitter | Polygon-clipped scanline brush strokes | Up to 240 |
| `accents` | Guide path, count, length, seed | Short strokes along arc length/tangent | 1..64 |

`coverage` is a **deliberately basic structural color block-in**, not physically realistic pigment spreading. More natural brush engines are assigned to Round 8. No benchmark-specific imagery, raster copy, shell/API command or hidden file write can come from the model's plan.

Lowering constraints: at most 192 high-level intents, 32 subject/stage layer groups, 900 elements in each group, 6000 total v3 elements, 10000 native allowlisted steps. Large or ambiguous geometry fails closed. Stage plan digest and native step SHA-256 are deterministic for identical input, with fixed seeds.

Complete example: [round7-generalist-scene.json](../examples/round7-generalist-scene.json). It combines a generic human figure, interior and ceramic still life; the example is a structural pipeline fixture, **not** a finished or native-verified painting.

## Deterministic lowering and staged native previews

`validate_scene_v4(candidate)` returns an immutable normalized v4 plan.
`lower_scene_v4(candidate)` returns a validated ScenePlan v3 plus stage/layer mapping.
`compile_scene_v4(candidate, profile_directory=None, build=None, preview_prefix=None)` emits the actual validated native steps, source v3/v4 hashes, `stage_spans`, brush diagnostics and stage preview paths.

A generic subject is no longer restricted to the v3 landscape kind enumeration. Its stage/subject paint group becomes a v3 `custom` layer with all actual marks computed before approval. Thus the existing Bridge and user-protection boundaries stay unchanged.

For each native stage, a real `preview.canvas` action captures the stage, and three milestone previews (`01-layout.png`, `02-color.png`, `03-final.png`) are also generated at phase boundaries. No offline image is substituted for a real Krita stage preview.

## Run a manually authored generalist plan

The command below is for a separately authorized **local** run, not an operation performed during GitHub development.

```powershell
krita-agent creative init --directory artwork-results/round7-demo --brief-file brief.json
krita-agent creative plan --directory artwork-results/round7-demo --candidate examples/round7-generalist-scene.json
krita-agent creative approve --directory artwork-results/round7-demo --confirm
# User inspects each actual phase and explicitly approves every subsequent one:
krita-agent creative paint-stage --directory artwork-results/round7-demo --session session.json --confirm
krita-agent creative status --directory artwork-results/round7-demo
krita-agent creative paint-stage --directory artwork-results/round7-demo --session session.json --confirm
krita-agent creative paint-stage --directory artwork-results/round7-demo --session session.json --confirm
krita-agent creative export --directory artwork-results/round7-demo --session session.json
```

For natural-language planning, the model provider is **opt-in**, not mandatory:

```powershell
krita-agent creative plan --directory artwork-results/round7-demo --generalist --model YOUR_CONFIGURED_MODEL
```

This uses the existing HTTPS JSON adapter and configured environment credentials. No model is invoked when `--candidate` is supplied. Legacy `creative plan` without `--generalist` still uses ScenePlan v3.

## Immutable stage approval and failure policy

- The user first approves the complete staged plan, then separately invokes `paint-stage --confirm` for **one stage at a time**. Legacy `creative paint` explicitly refuses a v4 plan; no quiet all-stage execution.
- The run stores normalized `scene-plan-v4.json` and `scene-plan-v3.json`, their proposal files, compiled commands, phase spans/hashes, history and stage cursor. All artifacts must still match before next-stage native execution.
- After each completed stage, a confirmed native scheduler checkpoint exists in its batch ledger. The controller captures active Krita document identity and layer graph fingerprint, and refuses the next stage if the currently active document/graph changed.
- The fingerprint is conservative **metadata**, not an exhaustive pixel-hash proof. Do not claim manual pixel edits are definitely detected. Complete native KRA export and fresh reopen remain independent strict delivery checks.
- A failed, interrupted, lost-response or uncertain native stage remains **unknown_needs_review**. No automatic retry or replay. Operators inspect the saved ledger/checkpoints and original Krita document before planning any new action.
- The v4 proposal is also lowered to v3 only for compatibility with the existing critique/revision contract; it is *not* evidence that a v4-specific anatomy/material critic already exists.

## What Round 7 does not establish

- No guaranteed visual quality or human-like brushwork; Round 8 addresses material grammar and anti-repetition.
- No genuine general human/animal structural knowledge; Round 9 addresses anatomy/perspective and multi-genre hidden benchmarks.
- No reference-image technique learning or network scraping; Round 10 handles authorized references with provenance.
- No autonomous, unbounded API feedback loop; Round 11 handles opt-in independent multimodal evaluation and finite revisions.
- No native-installed acceptance from source or unit tests. See [ROUND7-ACCEPTANCE](ROUND7-ACCEPTANCE.md).

## Source references

- [Generalist artist roadmap](ARTIST-ROADMAP-R7-R12.md)
- [Project roadmap](ROADMAP.md)
- [Full artwork acceptance](ARTWORK-ACCEPTANCE.md)
- [Agent branch/acceptance rules](../AGENTS.md)
