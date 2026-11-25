# Round 16 — natural fine-stroke planning (deterministic, native-compatible source)

> **Development source, NOT real Krita visual acceptance.** This change is stacked after [R15 native regions](ROUND15-API.md) and [R14 semantic composition](ROUND14-API.md). The user explicitly requested that actual multi-build Krita drawing, visual comparison and human acceptance be conducted **once after core feature development**, not every round.
>
> R16 improves **how individual native brush strokes are planned**, while R15 retains responsibility for actual base area/shape fill. It does not claim to solve Stable's segmented stroke transparency overlap (R13), discover brush presets, or learn human pen data from static line-art.

## 1. Why the old strokes looked mechanical

Previous intent marks and simple constant-pressure paths often created rigid polygonal contours, large circular endpoints and repeated stroke geometry. Increasing density and stroke count did not make the R12 paintings recognizable. R16 introduces a bounded stroke sampling algorithm focused on **smooth paths, meaningful variation *within* one stroke, and deliberate fine-detail scale**. It does **not** add random jitter simply to increase a metric.

## 2. Validated ScenePlan v4 `gesture.natural` feature

An optional new field, only for a `kind=gesture` intent:

```json
{
  "id": "ink_leaf",
  "subject_id": "plant",
  "kind": "gesture",
  "purpose": "Follow the real intended leaf contour with fine taper",
  "path": [[30, 90], [38, 64], [52, 54], [75, 85]],
  "natural": {
    "purpose": "vegetation",
    "spacing": 3.0,
    "smoothing_passes": 1,
    "start_pressure": 0.20,
    "peak_pressure": 0.78,
    "end_pressure": 0.06,
    "corner_relief": 0.18
  }
}
```

- Supported purposes: `contour`, `fine_detail`, `fur`, `fold`, `vegetation`. These are validated profiles, **not** unverified brush presets.
- `spacing`: 0.75–24 px. `smoothing_passes`: 0–2. `start_pressure`, `peak_pressure`, `end_pressure`: 0.02–1.0 with peak >= endpoints. `corner_relief`: 0–0.4.
- Generates **2–2048 native points** only. Does not truncate an over-budget stroke silently; errors before native execution.
- Keeps guide endpoints, stroke order, subject bounding box and all numeric sensor bounds; smooths the path with convex-hull-preserving corner cuts, samples more densely at curvature, and applies arc-length-based pressure taper. No arbitrary color change inside a stroke or fake sensor support.
- `gesture.natural` cannot be combined with any other per-stroke pressure curve, pressure variation, speed sensitivity or old material `render` recipe; this rejects contradictory semantics rather than silently overriding a user-authored style.
- Existing `gesture` without `natural` still works exactly as before. Legacy v2/v3/v4 scene compatibility remains intact.

## 3. Compiler & Krita execution boundary

```
semantic geometry / R14 model object intent
   → bounded gesture.natural (R16)
   → src/krita_agent/natural_strokes_v16.py
   → [x,y,pressure,time_ms,speed] points
   → existing scene_v4 / v3 compiler + workflow
   → Krita Bridge allowlisted draw.stroke mode=auto
   → actual Krita installed brush preset on editable KRA layer
```

R16 automatically chooses a natural contour profile in R14's `sketch` stage and a fine detail/fur profile in `detail`; R15 `block_in` remains a filled native `region` polygon. For direct v4 users, `natural` is strictly opt-in. Each compiled stroke may adjust *pressure samples* inside a native stroke, while size/color/preset changes continue to occur between distinct strokes through existing reviewed brush configuration APIs.

**Important:** Stable versions without `paintPolylineStroke` may still fall back to multiple `paintLine` operations and exhibit opacity endpoint seams. R13's read-only `creative native-preflight` and optional `--reject-segmented-joins` continue to identify/block such risk. Pressure samples alone are not evidence that an installed brush uses pressure to vary size/opacity or that pen tablet hardware works.

## 4. Offline source tests and final acceptance deferral

New source-only tests check:

- pressure rising and falling naturally along arc length; non-flat values; endpoints and times unchanged; deterministic output and bounded sample count;
- curvature-aware resampling stays in subject ROI and cannot generate commands/files;
- invalid numeric settings, forbidden fields, malformed geometry, excessive density and conflicting existing pressure/brush recipes fail closed;
- R14 semantic → R15 region + R16 native stroke lowering remains deterministic and compiled into existing Krita allowlist;
- legacy v4 plans remain unaffected; R13 preflight accurately flags a multi-point `mode=auto` stroke on builds missing the continuous native API;
- full old Windows Python 3.10/3.13 CI is still mandatory.

**Deferred, not passed:** actual installed Krita Stable/Next Qt5/Next Qt6 path quality, brush preset reaction, 25%/50% join artifact, full KRA/PNG fresh reopen, blind visual A/B and independent human painting acceptance. These belong to the integrated final campaign.

## 5. Known visual limitations and next steps

- Shape guide geometry is still drawn from simplified primitive semantic subjects. R16 smooths a supplied guide; it cannot magically transform a rough ellipse into an accurate cat, hand or complex leaf contour.
- Pressure taper is only a native sensor proposal. Its visible size/opacity effect requires actual preset calibration. No physical stylus data is involved.
- The current path uses safe convex-hull smoothing, not a full curve-surface direction field, true ink flow, color smudge, or real learned artistic motor patterns.
- R17 should add coherent material/color/light/edge decisions; R18 line-art input and searchable technique library will improve the source guide quality; R19 actual-pixel feedback enables bounded correction. R20 verifies all of these in real KRA and with independent reviewers.

**Do not use native point counts, mathematical smoothness, or green offline CI as proof of human-like artwork.**
