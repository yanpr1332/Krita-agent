# Round 14 — semantic composition and deterministic paint-plan lowering

> **SOURCE IMPLEMENTATION ONLY** on `feat/round14-semantic-planning`. This is the first high-level planning interface: model-generated or manually supplied `CompositionGraph` → trusted geometry/paint-intent compiler → **existing** ScenePlan v4/v3 native approval path. It is a structural scaffold, not accepted visual drawing quality, anatomical reconstruction or advanced native region filling.

[General roadmap](ARTIST-ROADMAP-R13-R20.md) · [Target architecture](ARTIST-ARCHITECTURE-R13-R20.md) · [User-approved consolidated-acceptance policy](ROUND14-DEVELOPMENT-POLICY.md).

## 1. Why this exists

Round 12 showed that a model emitting complete v4 plans often fails strict geometric, material or budget constraints before reaching Krita. For R14 the model is only asked for **small normalized object declarations**: subject/part identity, rectangle, color, primitive silhouette, semantic materials, depth, and declared relations. Python owns pixel placement, valid primitive polygons, phase intents and the downstream reviewed ScenePlan. No model-generated paths, command strings, absolute local filenames, arbitrary APIs, raster pastes or tool calls are accepted.

A composition `/1` is **not** a finished painting: parts drawn as ellipses/rectangles/triangles/diamonds/capsules are merely bounded hypotheses. It does not infer accurate anatomy, reference silhouettes, perspective, photorealistic fill or material properties.

## 2. Model-independent, versioned contracts

### Composition proposal

```json
{
  "schema": "krita-agent-composition/1",
  "style": "fine line illustration",
  "notes": "A cat beside the cup, in front of the room",
  "subjects": [
    {
      "id": "cat",
      "name": "Sitting cat",
      "kind": "animal",
      "bbox": [0.22, 0.21, 0.40, 0.65],
      "color": "#af9075",
      "detail_color": "#393437",
      "depth": 0.7,
      "outline": "ellipse",
      "materials": ["fur"],
      "parts": [
        {"id": "head", "name": "Head", "bbox": [0.23, 0.02, 0.50, 0.32],
         "outline": "ellipse", "color": "#bd9c7c"}
      ]
    }
  ],
  "relations": []
}
```

- `bbox` is **[x,y,width,height] in 0..1**; subject positions are relative to the canvas; part positions are relative to the parent subject.
- `id` lower-case safe 1–20 characters; nested part IDs join as `parent_part` and must also fit 20 characters. No duplicate semantic IDs.
- Supported primitive silhouettes: `ellipse`, `rectangle`, `diamond`, `triangle`, `capsule`.
- Optional relations `left_of`, `above`, `inside`, `front_of` are **checked**, not silently solved or forced by moving objects. Invalid relations yield actionable `TaskError`. This avoids visually destructive automatic coordinates repair.
- 1–10 total subjects **including expanded parts**; max 4 parts per subject; max 30 relations. Geometry remains bounded on the user-approved canvas.
- RGB hex colors and declared material tags only. Unknown keys, bool/nonfinite numbers, bad IDs, out-of-range boxes, incomplete relationships or untrusted commands fail closed.
- Normalized archive form flattens parts, stores absolute normalized coordinates + parent relation, and is round-trip validated. Plan hash and provenance are bound to approvals.

### Derived PaintPlan `/1`

The compiler generates an inspectable intermediary with `sketch`, `block_in`, `detail` stage goals and subject-specific `contour`, `region_blockin`, `detail_line` semantic tasks.

It also emits a validated ScenePlan v4 with matching native pen intents; the **existing v4 → v3 → whitelisted native** compiler is authoritative. For now, `region_blockin` still lowers to the existing bounded native coverage strokes; proper area/fill engine is **planned R15**, not implemented by this change.

The paint plan explicitly sets:

- `status: structural_scaffold_only`
- `requires_native_approval: true`
- `artwork_accepted: false`
- source composition SHA256 and generated scene v4 SHA256.

No reference-image pixels are pasted into a paint layer. `PaintPlan` output is conceptual; existing Krita Bridge keeps sole control over actual native drawing.

## 3. CLI — zero model cost/manual and opt-in model

### Manual semantic scene (no key/no external call)

```powershell
krita-agent creative init --directory artwork-results/r14-cat --brief-file examples/round14-brief.json
krita-agent creative plan --directory artwork-results/r14-cat --candidate examples/round14-semantic-composition.json
```

The brief file must specify a valid prompt, canvas size and title using the existing `creative init` format (the semantic candidate intentionally has no pixel document fields). You can also write any legal brief JSON; the above brief path is illustrative and may be created by the user.

### Optional model-based semantics (one API request, no retry loop)

```powershell
krita-agent creative plan --directory artwork-results/r14-cat --model YOUR_MODEL_ID --semantic
```

- Uses the existing explicit `ChatJSONProvider` and its locally configured environment key/endpoint (never commit secrets).
- Model returns a short `CompositionGraph`, **not v4 with thousands of absolute coordinates**.
- One call only by default; no automatic costly corrective calls or hidden model fallback. Invalid proposals return a task error and remain unapproved.
- The existing explicit `--reference` parameter may send the image to the configured model, so use it **only when the image owner has authorized sending that specific file to that provider**. Data rights/consent policy is unchanged.

`--semantic` and `--generalist` are mutually exclusive planner routes. Manual composition files are detected by the `schema` field; the flag is not required. Existing v3/v4 candidates and `--generalist` model planning remain untouched.

### Approvals and native side-effects

```powershell
krita-agent creative approve --directory artwork-results/r14-cat --confirm
# On a separately authorized, authenticated Krita session, per-stage:
krita-agent creative paint-stage --directory artwork-results/r14-cat --session .cache/session.json --confirm
```

Planning and approval are local files only. Painting is **never** implicit; all v4 stage approvals remain mandatory; a disconnected/uncertain Krita native effect is never automatically replayed.

## 4. Immutable planning evidence

After a validated `creative plan`, the run directory contains:

- `composition-v14.json`: strict normalized source graph, including parent/part links.
- `paint-plan-v14.json`: inspectable operation scaffold and source SHA bindings.
- `scene-plan-v4.json`, `scene-plan-v3.json`: validated compatibility lowering.
- `generalist-proposal.json`, `creative-proposal.json`, `compiled-scene.json`: existing approval and native stage signatures.
- `creative-workflow.json`: manifest with each source file SHA256.

The first overall `approve` and every subsequent `paint-stage` recompute and cross-check the semantic source, paint plan and generated v4 against their archived hashes. Editing any file after planning fails closed. This preserves existing KRA/staged export and other creative workflow safety contracts.

## 5. Tests and deferred native acceptance

Fast source tests cover schema rejection, invalid spatial relations, part containment, deterministic output, no image-paste steps, candidate/model path and model call count, stage-only approval and hash tampering. Full repository Windows Python 3.10/3.13 CI is the minimum development safety gate.

Under the user's explicit November 2026 **consolidated final acceptance** direction, there is **no R14 real Krita three-build painting campaign or 24-task human/artwork judgment**. Those are deferred until the main feature work is complete. This is **deferral of execution**, not a claim that artifacts were already accepted or a lowering of the final artwork acceptance contract.

## 6. Known limitations and R15–R20 handoff

1. Bounding primitives are not traced outlines or evidence of perspective/anatomy.
2. The block-in stage still uses native brush coverage from old v4. A dedicated geometry-safe region fill/selection engine belongs in R15.
3. `detail_line` is a bounded visual-direction hint, not trained pen pressure or natural photorealistic stroke work. Natural brush sampling and calibrated presets belong in R16.
4. The semantic JSON contains colors and material tags, not coherent lighting inference. R17 will own physically plausible value/color and material directions.
5. Reference/lineart recognition and retrieval are not trained by invoking an API. R18 adds rights-aware data and techniques.
6. Real pixel diagnosis and bounded paint revisions are R19. Full native/independent-human acceptance is R20.
