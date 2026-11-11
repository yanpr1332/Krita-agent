# Round 8 API — material-aware native brushwork and stage diagnostics

> **Source implementation, not artwork acceptance.** This is an opt-in extension to R7's `krita-agent-scene/4`. No installed-Krita brush quality or finished illustration is inferred from passing offline tests. Every native stage requires separate user approval. Real model-based independent artistic evaluation remains a later milestone.

## Architecture

A ScenePlan v4 `subject` still describes **what** and **where**, while an optional `render` recipe on `gesture`, `coverage` or `accents` says **how this material should be painted**. The existing `purpose`, subject material, named style, pressure and other source constraints stay mandatory.

When `render` is omitted, Round 7 validation/lowering/execution is unchanged. When present, `material_rendering.py` deterministically emits validated ScenePlan v3 `stroke` elements; the existing scheduler then sends only allowlisted native Krita brush commands. These original native strokes remain editable in real Krita layers. No reference image is pasted or synthesized.

## Material recipe (opt-in)

Example on a named polygon coverage intent:

```json
{
  "id": "cup_volume",
  "subject_id": "cup",
  "kind": "coverage",
  "purpose": "Build curved ceramic volume and a clear glossy rim",
  "material": "porcelain",
  "polygon": [[205, 172], [310, 172], [310, 270], [205, 270]],
  "spacing": 15,
  "angle": 0,
  "seed": 32,
  "render": {
    "technique": "contour",
    "flow": "tangential",
    "angle": 0,
    "spacing": 16,
    "length": 39,
    "curvature": 0.22,
    "light_angle": -45,
    "light_strength": 0.6,
    "irregularity": 0.14,
    "layers": 2,
    "edge_mode": "stitch",
    "edge_inset": 1.5,
    "palette": ["#56666F", "#A0ADB3", "#E9E8DF"],
    "seed": 500,
    "placement": "blue_noise"
  }
}
```

Supported `technique` names:

| Technique | Typical goal | Typical materials |
| --- | --- | --- |
| `wash` | Layered broad-value brush marks | sky, plaster, backdrop |
| `wisps` | Curving soft masses | cloud, haze |
| `ripples` | Long horizontal reflected forms | lake, water |
| `facets` | Broken angular planes | rock, cut wood |
| `growth` | Radiating/tapered growth marks | leaves, grasses |
| `contour` | Curved surface-following marks | ceramic, round objects |
| `folds` | Curved directional folds | cloth |
| `strands` | Narrow curving strokes | hair, fur |
| `planes` | Gentle volume shading | skin, rounded forms |
| `specular` | Sharp localized glints | glazed ceramic, metal |

These are parameterizable brush strategies, **not** a guarantee of physical material rendering or trained image understanding. A subject name does not force a technique; material, style and technique can be combined independently.

Fields and limits:

- `flow`: `linear`, `radial`, `tangential`, `perspective` or `growth`. Bounds are derived from the approved subject. `angle`: −180..180°.
- `spacing`: 3..100 pixels; `length`: 4..240 pixels. `light_angle`: −180..180°; `light_strength`: 0..1. Lighting influences palette selection, not a claim of physically correct light transport.
- `curvature`: 0..0.6; `irregularity`: 0..0.4. Randomness is deterministic from the plan and recipe seeds, and follows directional geometry rather than random image pixels.
- `layers`: 1..3 per intent; repeated color/opacity/brush marks are generated as native strokes. Multiple purpose-specific intents may be composed across 3..6 R7 stages.
- `edge_mode`: `none` or `stitch`; `edge_inset`: 0..14 pixels. Paths are clipped to the polygon **by centerline**; installed brush footprints can still extend beyond, so native pixel checks are required.
- `palette`: up to 8 `#RRGGBB` colors, selected by position/pass. The original R6 per-stroke brush preset, nominal size, opacity, color and pressure system remains effective. No unsupported in-stroke preset/color changes are claimed.
- `placement`: `staggered` for overlapping broad blocks or seeded, bounded `blue_noise` spacing for less mechanical localized marks. Neither method guarantees human quality.
- `seed`: a nonnegative 32-bit integer. Up to 400 native marks per rendered intent, 900 per StagePlan subject group, 6000 overall and 10000 native steps. Unsafe/oversize render plans fail validation instead of silently truncating.
- Unknown fields, unsupported techniques, untrusted code/paths, invalid colors and invalid budgets are rejected. No arbitrary plugin/API command is accepted.

**Known constraints:** The current R8 renderer does not guarantee gap-free pixel coverage, perfect clipped anti-aliased edges, realistic anatomy or physically correct color mixing. It makes individual material stroke patterns meaningfully different, but real-art evidence is still necessary to judge naturalness.

## Use via the existing CreativeWorkflow

The repository's [Round 8 material-study fixture](../examples/round8-material-study.json) combines an interior, a figure and a ceramic vessel. It is a **technical test plan**, not a finished illustration or guaranteed accepted artwork.

```powershell
krita-agent creative init --directory artwork-results/round8-study --brief-file brief.json
krita-agent creative plan --directory artwork-results/round8-study --candidate examples/round8-material-study.json
krita-agent creative approve --directory artwork-results/round8-study --confirm

# After each ACTUAL native stage preview, operator approves one separate phase.
krita-agent creative paint-stage --directory artwork-results/round8-study --session session.json --confirm
krita-agent creative paint-stage --directory artwork-results/round8-study --session session.json --confirm
krita-agent creative paint-stage --directory artwork-results/round8-study --session session.json --confirm
krita-agent creative export --directory artwork-results/round8-study --session session.json
```

For an explicitly configured HTTPS JSON model provider, `creative plan --generalist --model ...` now documents optional `render` recipes in its prompt. Model proposals are untrusted and go through the same strict validator. This source change makes **no API calls itself**.

## Read-only material diagnostics

```powershell
krita-agent creative diagnose --directory artwork-results/round8-study
```

The diagnostics report two independent evidence types:

1. **Plan geometry:** per-object coarse repeated path shapes, dominant orientation, stroke-length variability and contextual warnings. These never prove rendered pixel appearance.
2. **Real stage pixels (only after native preview archive):** for consecutive actual Krita `stage-XX-phase.png` files, SHA-256 integrity, exact differing RGBA and alpha pixels, maximum channel delta, stage contribution fraction, **per-subject ROI change fractions** (overlapping ROIs are not layer attribution), and color-mode/ICC metadata changes. Insufficient detail changes (for instance less than 0.1% of the canvas) produce an **inspect** note, never automatic failure or acceptance.

The diagnostics read existing hashes and PNGs without altering any drawing, document, run state, or prior failed version. They do not make visual-semantic judgements. An agent/human must still inspect actual pictures and record independent review.

## Acceptance and future scope

- [Round 8 acceptance matrix](ROUND8-ACCEPTANCE.md)
- [Round 8 development brief](ROUND8-DEVELOPMENT-PLAN.md)
- [R7 failed whole-art evidence](ROUND7-ARTWORK-ATTEMPTS.md)
- [Full artwork acceptance](ARTWORK-ACCEPTANCE.md)

Round 9 takes on deep subject structure, perspective and anatomy. Round 10 handles authorized reference repainting and reusable technique provenance. Full opt-in multimodal API automatic critique remains planned for Round 11.
