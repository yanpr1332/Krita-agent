# R4.5 — Full-artwork acceptance standard

**Status:** benchmark/reference and acceptance procedure only. No Krita drawing acceptance is performed by adding these files. Historical functionality/long-job tests remain valid **only as technical validation**, not proof of aesthetically or semantically complete artwork.

## Why this exists

Earlier Round 4 tests executed 1,200 short strokes, simple rectangles and 32×32 pixel overlays on valid editable KRA documents. Those tests established real native painting, stability, pixels, layer preservation and recovery, **but did not test complete illustrative output**. From Round 5 onward every "full painting" claim requires separate artwork acceptance.

## Reference + contract (both mandatory input to the local visual model)

- Image: [sunset_alpine_lake.jpg](../benchmarks/artwork/reference/sunset_alpine_lake.jpg)
- Fixed JSON contract: [sunset_alpine_lake.v1.json](../benchmarks/artwork/contracts/sunset_alpine_lake.v1.json)
- Visual review prompt: [ARTWORK-VLM-REVIEW.md](ARTWORK-VLM-REVIEW.md)

The reference is an original, generated, illustrative **complexity / composition benchmark**, not a file the Agent can submit as its own output or a pixel-exact target to trace. The image has sky, sunset, clouds, layered mountains, forest, lake, reflections and foreground flora/rocks. The evaluator must see **actual image pixels**, not merely filenames, class tags, prompt text or layer names.

## Split acceptance into two distinct, non-interchangeable gates

1. **Technical:** authentic Krita command execution, KRA/PNG roundtrip, brush and layer operations, checkpoints, security, stress, regression and measured performance. Rectangles or line grids are legitimate here.
2. **Artwork:** a coherent finished image with visibly recognizable subject elements and spatial relationships, genuine painted content on meaningful editable layers, trustworthy KRA/PNG/screenshots and independent visual + human review. Grids, swatches and repeated short lines **must fail artwork acceptance**, even if 1,200 strokes and 8 layers pass technical tests.

Neither gate substitutes for the other. "Technically passed" and "Artwork passed" must be separate fields in future reports. An end-to-end autonomous-art milestone requires BOTH.

## Mandatory execution protocol for local acceptance

1. Lock and hash the benchmark image and JSON *before* execution. Use a fresh run directory under repository-local \`artwork-results/<run-id>/\`.
2. Give the painting Agent the natural-language task and benchmark. **Do not let the acceptance script itself synthesize a predetermined drawing via hardcoded rectangles.**
3. During the real Krita run, save scene plan, native command/step provenance, and three full-composition stage previews. Save screenshot(s) of the real Krita window with the artwork visible.
4. Save final \`artwork.kra\` and export \`artwork.png\` from **that same KRA**. Reopen the KRA in Krita and re-export, verifying meaningful visual/layer integrity. Never submit an image made separately by copying the benchmark.
5. Capture a real \`layer-graph.json\`; at least eight editable paint layers must **contribute visible content**. Layer names alone are not evidence.
6. Independently present the benchmark image, contract, actual final PNG, all three stage previews and KRA layer data to the visual model. Use schema krita-agent-artwork-vlm/2 from ARTWORK-VLM-REVIEW.md. Bind the review to the exact reference, final PNG, editable KRA and each stage-preview SHA-256. Include concrete visible evidence for every required object and spatial relation.
7. A human must see the rendered result (not merely a model-generated score), reopen and view the KRA, record schema krita-agent-artwork-human/2 in reviews/human.json, and explicitly accept or reject. Bind the human record to the exact PNG and KRA hashes, check every required object, and record a timestamp and concrete observations. A missing, ambiguous or negative review is failure / pending, not pass.
8. Record a layer-contributions.json file with a layers array of node_id, visible_contribution=true and a concrete description, based on actual layer inspection. Run python scripts/artwork_acceptance_audit.py --run-dir artwork-results/<run-id> only AFTER the local run and independent reviews. The R5 auditor validates artifact integrity, exact review-to-artifact hash binding, KRA/PNG consistency and recorded decisions, **not the truth of semantic artistic quality**; the human remains the final judge.

## Local output contract (cannot be omitted)

\`\`\`text
D:\computer\Krita\Krita-agent\artwork-results\<run-id>\
  artwork.kra                 real editable original painting
  artwork.png                 actual final KRA export
  reopened.png                real PNG exported after opening a fresh KRA copy
  reopen-evidence.json        two independent strict gates, hashes, ICC/color data and differences
  krita-screen.png            screenshot of actual Krita artwork window
  scene-plan.json             submitted scene plan / workflow stages
  execution.json              actual native operation log / provenance
  layer-graph.json            full final Krita layer hierarchy
  layer-contributions.json    independently reviewed evidence for 8+ substantive painted layers
  stages\01-layout.png        composition stage preview
  stages\02-color.png         color / objects stage preview
  stages\03-final.png         final painting stage preview
  reviews\visual-model.json  independent visual findings
  reviews\human.json         actual human review / accept or reject
  audit.json                  generated evidence-integrity audit
\`\`\`

These run directories remain locally accessible in the repository **even when ignored by Git**. The benchmark source/reference and acceptance code are committed to GitHub; output KRA, screenshots and PNGs are not silently deleted or renamed. Failed originals and repaired successors are separate retained versions.

## Publishing a curated cloud copy

The required local original remains untouched. For accepted runs, prepare a separate curated directory with:
- reduced-size PNG/JPG preview and optional stage contact sheet,
- review summary with provenance and sensitive fields removed,
- result SHA256 and pointers to local original,
- optionally full KRA via Git LFS or a GitHub Release asset, *only with explicit size/privacy review*.

Never automatically push raw KRA, local tokens, username-dependent absolute paths, temporary job logs, or private reference media to GitHub. Use \`scripts/prepare_artwork_publish.py\` to create a **staging directory** only; manually inspect and commit/push that subset if desired.

## Negative-control requirement

Before declaring the artwork evaluator reliable, deliberately present it with the earlier 8 rectangles / 1,200-line grid artifacts. It must reject them as lacking a coherent landscape. Also check false positives from an imported flattened reference image with misleading eight-layer names. Maintain the fixed benchmark contract regardless of those outputs.

No fourth-round or fifth-round drawing tests were run as part of this R4.5 repository change.


## Round 5 review-record schemas

The R5 review schemas are versioned and hash-bound. See ROUND5-API.md and ROUND5-ACCEPTANCE.md. The visual-model record requires object_evidence and per-relation evidence, plus hashes for the reference, final PNG, editable KRA and all three stage previews. The human record requires object-by-object checks and confirmation that the KRA was reopened and viewed. The audit remains an integrity check, not a semantic or aesthetic judge.
