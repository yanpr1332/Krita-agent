# Round 15 — native editable region-fill foundation

> **SOURCE IMPLEMENTED; FINAL NATIVE/ARTWORK ACCEPTANCE DEFERRED BY USER REQUEST.** R15 is stacked on [R14 semantic composition](ROUND14-API.md). It upgrades the semantic block-in path from hundreds of broad brush scanline strokes to **one bounded native filled polygon per semantic subject**. This is a deterministic, editable Krita shape operation, not an external generated image/paste.
>
> Branch: `feat/round15-native-regions` → PR target `feat/round14-semantic-planning` until R14 is merged. Do not merge R15 into main before R14. Offline tests are mandatory; real three-build Krita and whole-artwork assessment are consolidated later.

## 1. Why this change

R12's material A/B raised coverage but produced largely unrecognizable incomplete objects. Large areas should be established by stable shape/region primitives, not filled using many thick and repeated line segments.

R14 generated `sketch` / `block_in` / `detail` v4 stages, but `block_in` still used `kind=coverage` with scanline brush strokes. R15 introduces `kind=region` as an **opt-in ScenePlan v4 paint intent** and uses it by default for R14's semantic-composition block-in stage.

## 2. New native ScenePlan v4 region intent

A validated v4 stage may contain:

```json
{
  "id": "fill_cup",
  "subject_id": "cup",
  "kind": "region",
  "purpose": "Establish the actual bounded base color of the cup",
  "polygon": [[300, 180], [370, 180], [365, 260], [310, 260]]
}
```

Important:
- All points must stay **inside the declared subject bounds and document canvas**.
- Polygon must have 3–32 vertices, non-zero area and no self-intersections/touching edges under the existing v4 polygon validator.
- Max native filled region area is 12 million canvas pixels; total native region area for one stage ≤32 million pixels. Invalid or expensive plans fail **before Krita side effects**.
- `region` deliberately forbids brush overrides, random seed/jitter, material-render patterns, spacing/angle, pressure curves and stroke-only fields. Its color is inherited from the **subject's reviewed baseline foreground color**. R17 may add correctly scoped region-specific shadow/highlight colors through explicit validated commands.
- A `region` is different from legacy `coverage`: legacy remains accepted for deliberate brush-based texture or older scenes. Existing v2/v3/v4 paint plans continue to compile.

## 3. End-to-end compiler path

```
semantic composition /1 (R14)
      |
      | deterministic outline polygon & strict budget
      v
ScenePlan v4: stage block_in intent kind=region
      |
      | validate_scene_v4 polygon + subject bounds
      v
ScenePlan v3 object: kind=polygon, fill=ForegroundColor
      |
      | min_strokes=0 allowed ONLY when a genuine native filled polygon exists
      v
Allowed compiled native command: draw.shape
   params: {shape:"polygon", points:[{x,y},...], fill:"ForegroundColor"}
      |
      | existing Krita Bridge -> Node.paintPolygon(...)
      v
editable native Krita paint layer (not raster pasted)
```

R15 modifies `min_strokes` lower bound to 0 only when the object contains genuine `polygon` `ForegroundColor` native fill. Blank objects and unfilled rectangles continue to be rejected; the stage validity check now accepts an actual filled native shape instead of requiring a decorative brush stroke to satisfy its bookkeeping.

The `draw.shape` command is **already in the Bridge allowlist** and is not a new unbounded native IPC entrypoint. It paints into a real selected editable layer. Actual Krita build support and real output pixels are separately checked later.

## 4. Build-capability fail-closed behavior

R15 adds `src/krita_agent/native_regions_v15.py` with read-only `inspect_native_regions` and execution gate `require_supported_regions`.

- `creative native-preflight` on an approved plan/next stage now reports both the R13 segmented stroke join risk and `native_region_preflight`.
- Before submitting a stage containing `draw.shape` `polygon` `ForegroundColor`, the workflow queries the authenticated Krita `capabilities` once and checks `Node.paintPolygon` is reported present.
- When missing, execution fails **before** saving any `painting_unknown` intent or dispatching native work.
- Preflight reports `symbol_present_in_build`, not visual/physical-tool acceptance. The native API may be present but still not draw correctly for some Krita builds, and that remains to be tested.
- Legacy stages with no new filled polygon do not incur this extra preflight requirement. R13 optional `--reject-segmented-joins` is untouched.

## 5. Lightweight development verification and deferred acceptance

Offline tests cover:

- R14 semantic compositions now produce one native filled editable polygon per subject in the `block_in` stage and **no simulated scanline strokes** there.
- V4 validation/normalization remains idempotent; legacy v4, v3 and native Bridge behavior remain compatible.
- Wrong region settings, huge fills and geometry violations fail closed.
- AST-extracted real Bridge dispatch issues `paintPolygon` (mock node); no image.import or external raster result.
- Read-only/native preflight checks missing capabilities before job submission and leaves the approved stage unchanged.
- All repository Python 3.10/3.13 Windows offline tests and compile checks stay required during development.

**Not run now (deferred):** actual Windows Stable/Next Qt5/Next Qt6 region rendering, changed-pixel mask/anti-alias bounds, real KRA reopen, human appraisal, or 24-task campaign. There is no fabricated image evidence. If `Node.paintPolygon` is absent or differently implemented in a real build, adapt the supported native interface before claiming it works.

## 6. Known limitations and next modules

- The source graph still uses simple primitive silhouettes and cannot reliably trace an apple, cat anatomy or complex human pose from a bbox. R18 reference lineart/geometry extraction is needed for true contours.
- Region fills are flat solid colors only; holes, compound masks, true soft-edge blends, selection-based multi-material shadows, inter-part occlusion and lighting will need more R15/R17 work. A primitive polygon is not a perfectly filled real subject silhouette.
- R16 will improve actual continuous fine brushwork, brush preset calibration, nonmechanical marks and pressure.
- R17 color/material decisions must be structure-conditioned; merely adding colors or opaque flat shapes cannot establish finished artwork quality.
- R19 real-pixel critic + revision remains opt-in and bounded; R20 final consolidated native/human evaluation stays separate.

**This slice improves the execution representation, not completed artwork quality.**
