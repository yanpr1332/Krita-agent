# Independent artwork visual-model review — evaluator instruction

**You are assessing a finished, coherent illustration — NOT measuring the number of Krita commands.**

Required image inputs to load *as images*:
1. the original benchmark reference image in \`benchmarks/artwork/reference/sunset_alpine_lake.jpg\`,
2. the actual complete \`artwork-results/<run-id>/artwork.png\`,
3. the three actual stage previews and optional Krita screenshot.
Also read the fixed JSON contract. If any image is missing or cannot be opened visually, return \`fail\` or \`insufficient_evidence\`. Never infer image content from file names, logs, or layer names.

Ask:
- Is this an actual cohesive landscape illustration, not a grid of rectangles, short strokes, or arbitrary patches?
- Are sky, sun, volumetric clouds, mountains with distinct depth, forest, lake, sunset reflections and foreground flowers/rocks each *recognizable* in the finished actual PNG?
- Do the listed spatial relations make sense? Are the scene's major regions meaningfully composed, rather than icons scattered independently?
- Are there obvious unfinished/blank regions, generic repeated test strokes, clipping defects, abrupt pasted reference artifacts, or incoherent proportions?
- Are visual quality and style at least broadly comparable in **complexity** to the supplied benchmark? Do not require photorealism, the exact pixels, identical painterly style, or direct tracing.
- Do stages show progression toward the final scene? Visual progress alone does not establish authenticity; verify execution logs, Krita screenshot and editable-layer evidence separately.

Output a JSON object \`reviews/visual-model.json\` with:
\`\`\`json
{
  "schema": "krita-agent-artwork-vlm/1",
  "model": "ACTUAL_MODEL_IDENTIFIER",
  "reviewed_at": "ISO_8601_TIME",
  "reference_sha256": "EXACT_REFERENCE_FILE_SHA256",
  "artwork_png_sha256": "EXACT_FINAL_PNG_SHA256",
  "decision": "pass_or_fail",
  "coherent_full_scene": false,
  "objects": {
    "sky": false, "sun": false, "clouds": false, "mountains": false,
    "forest": false, "lake": false, "reflection": false, "foreground": false
  },
  "relations": [
    {"description": "one contract relationship", "passes": false, "evidence": "what is actually visible"}
  ],
  "failure_modes": [],
  "notes": "concrete observations about the ACTUAL painting"
}
\`\`\`

For an artwork \`pass\`, every required object and relation must be supported by directly visible evidence and \`coherent_full_scene\` must be true. Do not award points for eight names in a layer tree. If unsure, set \`decision\` to \`fail\` and explain. A separate human reviewer must still approve the actual image; the model's verdict alone is insufficient.
