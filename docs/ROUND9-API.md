# Round 9 — Generalist structure, composition and perspective API

**Status:** source development on the independent `feat/round9-multigenre-structure` branch. The code is an extension of ScenePlan v4, not an image generator, anatomical visual recognizer, automatic author of artistic strokes or evidence that artwork now looks human-painted. Round 8 material stroke source and merged cloud Tier-2 infrastructure were both included in this branch before this work.

## Scope

The optional `structure` field augments the existing `krita-agent-scene/4` scene. Existing scenes with no `structure` follow the original R7/R8 compiler path without added guide strokes. Material-specific optional `render` from R8 is still accepted by v4 intents.

A structure plan supports arbitrary **named subjects and parts**, with no special-case code drawing a fixed human or animal benchmark. `src/krita_agent/structure_v9.py` validates geometry and semantic relations; `subject_strategy_v9.py` suggests phase+material approaches without creating commands. `structure_revision_v9.py` offers bounded immutable repairs requiring explicit approval.

## Contract

Top-level optional property:

```json
{
  "structure": {
    "version": 1,
    "guide_mode": "paint",
    "subjects": [
      {
        "subject_id": "figure",
        "category": "human body proportions",
        "anchors": [
          {"id": "head", "xy": [110, 42], "role": "head center"},
          {"id": "neck", "xy": [110, 64]},
          {"id": "hip", "xy": [110, 124]}
        ],
        "parts": [
          {"id": "face", "tag": "head", "bounds": [95, 27, 30, 35], "anchor_id": "head"}
        ],
        "chains": [
          {"id": "spine", "anchors": ["head", "neck", "hip"], "purpose": "Locate the main spinal construction axis"}
        ],
        "expectations": [{"tag": "head", "min": 1, "max": 1}],
        "locked": false
      }
    ],
    "relations": [],
    "perspective": {
      "horizon_y": 70,
      "vanishing_points": [{"id": "main", "xy": [128, 70]}],
      "rays": []
    }
  }
}
```

The example is a `structure` field only; it must be embedded in a complete v4 scene with a matching `figure` subject and matching canvas, stages and brush. The source files [figure/room](../examples/round9-figure-and-room.json) and [perspective interior](../examples/round9-perspective-interior.json) provide complete fixtures.

- `guide_mode: audit_only` (default): validate structure and issue diagnostics, **never** draw hidden guides.
- `guide_mode: paint`: explicitly include each `render:true` chain as an additional **real native brush gesture in the sketch phase**. The compiler retains v3/v2 allowlist, stroke budgets, stage approval and hashing; it does not paste a raster image.
- `parts` have generic `tag`, `name`, `bounds`, optional parent and material. Expected tag counts can be declared by the author. A mismatch is a validation failure; this cannot magically detect real hands from an image.
- `anchors`, `parts`, `chains`: per-subject bounding, unique IDs, connected references, and acyclic hierarchy checked.
- `relations`: `front_of` (strict depth), `left_of`, `above`, `inside`, `attached` (named anchors+maximum gap), `width_ratio` (expected ratio+tolerance). Inconsistent geometry is refused; overlapping/occluded pixels are *not* automatically segmented or re-painted.
- `perspective`: optional horizon, up to four possibly off-canvas vanishing points, up to 32 guide rays with explicit convergence tolerance (0–30 degrees). Deviations outside tolerance fail the plan.
- `locked:true` on a structured subject, part or anchor protects against later structural change proposals. These locks are planning-level and do not themselves stop a user manually changing the Krita canvas.

## Bounded security and artifacts

- Up to 24 structured subjects, 192 parts total, 256 anchors, 64 chains, 96 intersubject relations and 24 additional sketch guide chains. An individual subject has at most 32 parts, 64 anchors, 8 chains and 24 expectations.
- `compile_scene_v4(scene)` returns `structure_diagnostics` and `subject_strategies` only when a structure exists. These are read-only and **never** indicate human artwork acceptance.
- Adding structure changes the source digest and compiled step digest. No accepted painting is silently overwritten. Native effects still require stage-level approval in real creative workflow.
- `propose_structure_fix(source, edits, rationale, expected_sha256=...)` accepts 1..8 corrections of named `anchor_xy` or `part_bounds` in **unlocked** geometry, validates the entire result and creates a source/candidate SHA-256-bound proposal. It performs **zero Krita commands**.
- `approve_structure_fix(source, proposal, confirm=True)` verifies both hashes and explicit approval before returning a future candidate ScenePlan v4. This is *not* an automatic undo/repaint of the old native document.

## Material + subject strategy

`subject_strategy_v9.subject_strategy(scene, subject_id)` considers declared material family (water/cloth/wood/skin/etc), number of structural parts, occlusion relations and perspective rays; it recommends a matching R8 technique and phase priorities. Unknown material families fall back to conservative generic suggestions rather than being forced into a landscape-centric object list. The model/user remains responsible for choosing actual composition and final native brush configuration.

## Tests and exact limitations

- Deterministic synthetic cross-genre tests: figure, animal, still life, architecture, vehicle and comic. Additional explicit signed-off examples: a figure in an interior and a one-point-perspective door. These are *compiler fixtures*, not full multi-genre image acceptance.
- Must reject invalid anatomy counts **when the expected counts were explicitly supplied**, conflicting occlusion/depth, inconsistent perspective, invalid hierarchy, out-of-subject parts, locked edit attempts, tampered proposal hashes.
- Cloud Tier 1: full Windows 3.10 and 3.13 tests; Tier 2: a bounded **real Krita Linux 5.3.4.1** staged fixture including structural sketch guides; Tier 3: cross-version Windows and independent actual multi-genre artistic review deferred to consolidated R9–R12 acceptance.
- This module does **not** infer keypoints from input photos, validate visual anatomy in painted PNG pixels, recognize true poses, or automatically fix a hand based on the image. R10 reference vision and R11 multimodal critique address those later, subject to user authorization. A syntactically complete sculpture-like silhouette still may be artistically poor.
