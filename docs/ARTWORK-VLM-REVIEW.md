# Independent artwork visual-model review — evaluator instruction (v2)

**Assess the rendered artwork, not the number of Krita commands.** The review must be performed against the exact local run and must describe visible evidence for every required object and spatial relationship.

## Images and source data to open

Load these files as actual images, not as filenames or metadata:

1. The locked benchmark reference at `benchmarks/artwork/reference/sunset_alpine_lake.jpg`.
2. The final exported `artwork-results/<run-id>/artwork.png`.
3. All three stage previews: `stages/01-layout.png`, `stages/02-color.png`, and `stages/03-final.png`.
4. The Krita screenshot, when useful for verifying the actual application context.

Read the immutable scene contract and inspect the KRA layer graph and execution provenance separately. If an image is missing, cannot be opened, or is not actually visible to the reviewer, do not infer its contents: return `fail` or `insufficient_evidence`.

## Required visual questions

- Is the final result a cohesive landscape illustration rather than a grid of rectangles, short strokes, or arbitrary patches?
- Are sky, sun, volumetric clouds, mountains with distinct depth, forest, lake, reflection, and foreground elements recognizable?
- Do all six spatial relationships in the contract hold in the actual image?
- Are there unfinished blank regions, repeated test marks, clipping defects, abrupt pasted-reference artifacts, or incoherent proportions?
- Is the result broadly comparable to the reference in compositional complexity? Do not require pixel identity, photorealism, or tracing.
- Do the three stages show a plausible progression toward the final composition?

A model score, object name, layer name, prompt, or execution log is never visual evidence by itself.

## Required output: `reviews/visual-model.json`

Use schema `krita-agent-artwork-vlm/2`:

```json
{
  "schema": "krita-agent-artwork-vlm/2",
  "model": "ACTUAL_MODEL_IDENTIFIER",
  "reviewed_at": "ISO_8601_TIME",
  "reference_sha256": "EXACT_LOCKED_REFERENCE_SHA256",
  "artwork_png_sha256": "EXACT_FINAL_PNG_SHA256",
  "reviewed_inputs": {
    "artwork_kra_sha256": "EXACT_EDITABLE_KRA_SHA256",
    "stage_previews": {
      "stages/01-layout.png": "EXACT_SHA256",
      "stages/02-color.png": "EXACT_SHA256",
      "stages/03-final.png": "EXACT_SHA256"
    }
  },
  "decision": "pass_or_fail",
  "coherent_full_scene": false,
  "objects": {
    "sky": false,
    "sun": false,
    "clouds": false,
    "mountains": false,
    "forest": false,
    "lake": false,
    "reflection": false,
    "foreground": false
  },
  "object_evidence": {
    "sky": "Describe the visible sky evidence.",
    "sun": "Describe the visible sun evidence.",
    "clouds": "Describe the visible cloud evidence.",
    "mountains": "Describe the visible mountain evidence.",
    "forest": "Describe the visible forest evidence.",
    "lake": "Describe the visible lake evidence.",
    "reflection": "Describe the visible reflection evidence.",
    "foreground": "Describe the visible foreground evidence."
  },
  "relations": [
    {
      "description": "sun visible in sky above distant ridge",
      "passes": false,
      "evidence": "Describe what is directly visible."
    }
  ],
  "failure_modes": [],
  "notes": "Concrete observations about the actual final image and stage progression."
}
```

Include one relation row for every required relation in the fixed contract. Each required object and relation needs a concrete visual observation; a boolean alone is insufficient. A passing review must have no unresolved failure modes. Record the actual image hashes from the local files, not values copied from another run.

The artifact auditor checks that this review is bound to the exact reference, KRA, final PNG, and stage-preview hashes. It cannot verify that the model truly saw the images or that its visual judgement is correct. A separate human reviewer must still inspect the result and approve it.
