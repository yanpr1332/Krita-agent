# Round 6 — native brush flexibility and adaptive-detail planning

This round is a **controller-side source implementation**, extending the existing
ScenePlan v3 → ScenePlan v2 allowlist → authenticated localhost Krita Bridge.
It changes no on-device painter state until a planned run is explicitly approved.
Native acceptance and finished-artwork approval remain separate.

## What can vary and when

| Control | Resolution | How it reaches Krita |
| --- | --- | --- |
| Preset | Between individual strokes | `brush.configure` |
| Nominal size (0.1–1000 px) | Between individual strokes | `brush.configure` |
| Color (`#RRGGBB`) | Between individual strokes | `brush.configure` |
| Opacity (0–1) | Between individual strokes | `brush.configure` |
| Pressure (0–1) | At path samples within a continuous stroke | `draw.stroke` sensor points |
| Time, tilt, rotation, speed | At path samples | Existing native stroke-point protocol |
| Smoothing / spline / spacing | Stroke trajectory planning | Existing validated stroke engine |

No native interface here claims arbitrary color transitions or preset switches **inside**
a single continuous stroke. Krita preset response to pressure/tilt must be confirmed
on an installed build; supplying sensor values does not prove visible dynamics.

## ScenePlan v3 named styles and per-stroke overrides

```json
{
  "id": "clouds",
  "kind": "cloud",
  "name": "Volumetric cloud",
  "depth": 0.2,
  "bounds": [0, 0, 1600, 400],
  "brush": {"color": "#b0a0b7", "size": 50, "opacity": 0.6},
  "min_strokes": 3,
  "styles": {
    "wash": {
      "brush": {"size": 145, "opacity": 0.24, "color": "#ad9ab6"},
      "pressure_curve": [[0, 0.1], [0.25, 0.7], [0.65, 0.9], [1, 0.1]],
      "pressure_variation": 0.08,
      "variation_frequency": 4,
      "variation_seed": 17
    },
    "edge": {
      "brush": {"size": 7, "opacity": 0.82, "color": "#ffe8c2"},
      "pressure_curve": [[0, 0.04], [0.5, 0.9], [1, 0.07]]
    }
  },
  "elements": [
    {"kind": "stroke", "style": "wash", "points": [
      {"x": 100, "y": 180}, {"x": 400, "y": 140}, {"x": 800, "y": 170}
    ]},
    {"kind": "stroke", "style": "edge", "points": [
      {"x": 200, "y": 80}, {"x": 500, "y": 65}, {"x": 850, "y": 110}
    ]},
    {"kind": "stroke", "style": "wash", "brush": {"size": 48},
     "points": [{"x": 150, "y": 230}, {"x": 650, "y": 210}]}
  ]
}
```

The example is an **object excerpt**, not a complete scene file. See
[`examples/round6-multistyle-scene.json`](../examples/round6-multistyle-scene.json)
for a complete, reviewable ScenePlan v3.

`styles` accepts up to 24 aliases per object. Every stroke can select one
alias with `style` and override individual `brush` fields. Unspecified
brush values inherit from the object. The compiler validates complete effective
brush states, emits configuration changes only when necessary, and restores the
object baseline after a styled stroke. It refuses transitions where a previously
set field would otherwise be left stale without a known baseline.

A `brush_category` on a stroke requests an evidence-backed preset profile;
it **requires** an explicit calibrated profile directory and Krita build.
Unreviewed categories and ambiguous/missing profiles do not fall back silently.

## Pressure dynamics

`pressure_curve` has 2–24 strictly increasing `[position,pressure]` knots:
position starts at 0 and ends at 1; pressure stays within 0–1. The position
follows actual stroke **arc length**, not merely point index. Interpolation is
`smooth` by default or `linear` with `pressure_interpolation`.

Optional parameters:
- `pressure_variation`: bounded deterministic sensor modulation (0–0.3).
- `variation_frequency`: oscillations across the stroke (0.25–32).
- `variation_seed`: stable nonnegative integer.
- `speed_sensitivity`: reduce pressure based on explicitly supplied
  normalized point `speed` (0–1); defaulted speed is zero.

A supplied curve deliberately overrides raw point-pressure values; without a
curve, authored pressure is preserved and missing values use a smoother,
material-specific semantic envelope. Identical inputs produce identical output
and stable hashes. The controller changes pressure samples, not the installed
Krita brush engine or its calibration.

Both freehand strokes and cubic Bézier paths support these styles. Long native
strokes still honor the existing 2,048-point IPC bound; no silent stroke
segmentation or texture-seam regression is introduced.

## More strokes without relying on a few fixed passes

ScenePlan v3 now supports up to **900 drawing elements per semantic object**
(subject to the unchanged 6,000-element scene and 10,000-native-step limits).
A declared `min_strokes` budget is checked before compilation. The planner
prompt explicitly asks for broad wash, medium form, small details, and irregular
material-specific accents with distinct size/color/opacity/pressure choices.

The compiled plan contains `brush_diagnostics` with per-object stroke density,
distinct sizes/colors/opacity/presets, pressure spread, direction diversity and
repeated trajectory signatures. These are **diagnostics**, not proofs of artistic
quality. Sparse or repetitive areas yield warnings for planning/revision; no
metric is allowed to impersonate a visual reviewer.

Creative revisions also accept named styles and per-stroke brush overrides,
allow up to 400 bounded native strokes per approved ROI, and preserve the
existing new-layer, checkpoint, selection-clipping and no-auto-replay safeguards.

## Offline usage

```powershell
krita-agent creative init --directory artwork-results/round6-demo --brief-file brief.json
krita-agent creative plan --directory artwork-results/round6-demo --candidate examples/round6-multistyle-scene.json
# Inspect compiled-scene.json, brush_diagnostics and actual trajectories.
krita-agent creative approve --directory artwork-results/round6-demo --confirm
# Local native drawing is a SEPARATE, authorized acceptance step.
```

Actual Krita pressure response, texture transitions, cross-build continuity,
rendering quality and artist review are **not** certified by offline CI. Do not
treat a high stroke count, diverse parameters or a passed structural plan as
full-artwork acceptance.
