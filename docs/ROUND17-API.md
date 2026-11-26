# Round 17 — coherent lighting and material-specific value layers

> **SOURCE IMPLEMENTED / REAL-ART QA DEFERRED.** R17 follows R14 semantic structure, R15 editable native region fills and R16 fine strokes. Real Windows Krita three-build painting, KRA/PNG fresh reopen, visual and human review, and formal artwork benchmarks are deferred to the consolidated campaign as directed in [CONSOLIDATED-ACCEPTANCE-POLICY.md](CONSOLIDATED-ACCEPTANCE-POLICY.md). A green CI run is **not** proof of photographic realism.

## 1. Motivation

Prior stages supplied one base color to each region; simply increasing per-stroke RGB variation never guaranteed coherent lighting or recognizability. R17 introduces **one shared scene light** and bounded per-subject value groups to prevent independent random palettes.

The new `lighting_v17.py` is a pure deterministic planning and native-region-geometry layer. It does not infer actual 3D surface normals, measured physically based reflectance, accurate real-life anatomy or post-render outcomes. It only makes the old simplified semantic objects visually more structured **when the native Krita build supports editable polygon fills**.

## 2. Semantic composition lighting contract

A `krita-agent-composition/1` proposal may add:

```json
{
  "lighting": {
    "direction": [-0.6, -0.8],
    "strength": 0.56,
    "warmth": 0.2,
    "shadow_fraction": 0.35,
    "highlight_fraction": 0.22
  }
}
```

All fields are optional; a deterministic light defaults to upper-left. `direction` points **toward the light** in canvas coordinates, normalized by Python. `strength` ranges 0–1, `warmth` –1..1, `shadow_fraction` 0.10–0.48, `highlight_fraction` 0.08–0.42; their combined coverage is capped at 0.85. Nonfinite numbers, zero vectors, unrecognized commands/keys, and unsupported schema IDs fail closed.

Validated compositions include the **canonical** light spec, so a saved and reloaded source produces the exact same geometry and SHA-bound PaintPlan. The model is never allowed to specify unverified native commands, arbitrary image files or unrestricted polygons.

## 3. Material-aware RGB value hierarchy

`material_palette(base, materials, lighting)` computes a deterministic `base`, `shadow`, `highlight` palette, selecting a bounded heuristic contrast response from declared labels:

- Higher edge/reflective contrast for metal, porcelain, ceramic, glass, water.
- Softer transitions for cloth/fabric, fur, skin, wood, foliage, stone, paint.
- Unknown labels use a safe generic profile rather than invented physics.

Colors mix toward a warm/neutral light tint or a cooler/darker shadow tint in **linear RGB**, then convert back to hexadecimal sRGB. The goal is a coherent value hierarchy and color-temperature decision across subjects, not arbitrarily changing RGB mid-stroke. The PaintPlan records `lighting` and `palette_by_subject`; no model secret/image is included.

## 4. Bounded native shapes and real editable layers

For each convex primitive silhouette supplied by the existing R14 geometry generator:

1. **Base** — fill the bounded original subject polygon in its approved base RGB.
2. **Shadow** — intersect that polygon with a half-plane on the side opposite the shared light.
3. **Highlight** — intersect with a half-plane toward the light, using the material-specific light color.

A deterministic Sutherland–Hodgman clipper removes duplicate/collinear vertices and refuses negligible polygons. Clipped polygons remain inside the original source primitive and are revalidated by the strict ScenePlan v4 polygon constraints and R15 native region area budgets.

These become three `kind=region` intents per drawable subject within the R14 `block_in` stage (at most 10 subjects = at most 30 intents, below the stage max 32). They compile to the **existing Krita Bridge allowlisted** `draw.shape` with `shape=polygon,fill=ForegroundColor`, and change the brush's current foreground RGB only **between** filled region operations.

Important safety modifications:

- V4 adds `fill_color: "#RRGGBB"` **only** on `kind=region`, never on a gesture/coverage/accents intent. No stroke-sensor, per-pixel, shell, model, arbitrary file or Krita command may enter through this field.
- V3 permits a single `brush: {color:"#RRGGBB"}` override **only** on an actual filled native polygon. Other shapes, unfilled polygons and attempts to alter preset/size/opacity/pressure through a shape-level override are refused.
- The existing compiler restores baseline brush settings when the next element changes. Color, polygon geometry, native commands and every stage remain tied to the original approved plan/file hashes.
- Each *subject* has its own editable paint layer; three regions can be filled into the same subject layer in stable order. These are real editable Krita paint operations, not generated raster images or pasted reference pixels.
- `creative native-preflight` (R13/R15) still guards required build symbols and continuous-stroke risks before native submission.

## 5. Development verification and explicit limitations

New deterministic offline tests verify:

- canonical lighting schemas, strict numeric/unknown-key validation, material-specific light/shadow/value ordering, repeatable color palettes;
- clipped shapes stay bounded and nondegenerate on rectangle/ellipse/diamond/triangle/capsule primitives;
- semantic model composition → full R17 light map → V4/V3 → Krita allowlist emits 15 editable filled shapes and per-region foreground RGB updates for the example's five subjects;
- no raster-paste commands or false native/human acceptance;
- unchanged legacy V3/V4 paths, approval/artifact hashes, invalid region color and shape brush parameters refused;
- Windows Python 3.10 / 3.13 offline GitHub Actions stay mandatory.

**Known limitations:** flat three-tone cells create hard bands rather than smooth photorealistic soft shadows; no true polygon holes or complex nonconvex silhouettes, cast-shadow geometry, depth/occlusion solver or normal-map/PBR shading; color accuracy still depends on actual Krita profile/alpha/preset. These are not features claimed by this PR.

The R18 lineart/visual reference geometry and R19 actual image-grounded revision are more important to recognizable subjects than simply increasing R17 color count. At R20 run real native strokes, image-grounded visual assessment, KRA reopen and the frozen artwork benchmarks. Until then `T2/T3/T4: NOT_RUN/DEFERRED`.

## 6. Integration dependency

R17 is developed on a fresh `feat/round17-lighting-material` branch based on the **clean R15–R16 integration PR** (not the out-of-date original R16 source branch). Merge the clean integration PR into main first, then retarget this R17 PR to main and review the delta. Do not silently merge into a predecessor feature branch or skip source CI.
