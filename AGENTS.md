# Local agent instructions: Krita Agent and its acceptance process

These rules apply to coding/testing agents and the local human-run acceptance workflow. Follow them before claiming a feature or end-to-end painting workflow is accepted.

## Distinguish acceptance types

- TECHNICAL acceptance checks Krita API behavior, native strokes, KRA/pixel operations, performance and safety. Simple boxes and repeated lines are allowed for only these tests.
- FULL-ARTWORK acceptance checks whether the actual Krita Agent has generated an entire coherent, recognizable, editable illustration. A grid of 1,200 strokes, eight empty/named layers, or several rectangles is never a passing artwork.
- A milestone described as "can paint a finished illustration" requires BOTH technical and full-artwork acceptance. Do not backfill earlier technical reports as artwork validation.

## Mandatory full-artwork inputs

Read docs/ARTWORK-ACCEPTANCE.md, docs/ARTWORK-VLM-REVIEW.md and the immutable scene contract in benchmarks/artwork/contracts/sunset_alpine_lake.v1.json. **Open the pixels** of benchmarks/artwork/reference/sunset_alpine_lake.jpg and show them to the visual evaluator. Do not let a VLM infer visual complexity from captions, filenames, labels or logs only.

The illustration reference is a complexity target, not an image to paste into Krita as the final artifact. The benchmark must be locked before running. Do not edit it to make an inferior output pass.

## Mandatory local run outputs

Create a unique directory under artwork-results/<run-id>/ **inside this repository**. Preserve final artwork.kra, artwork.png, actual Krita screenshot, scene plan, native execution history, layer graph, evidence of 8 or more genuinely contributing paint layers, three full-scene stage previews, and two independent reviews. Keep failure runs, too. Do not delete, overwrite or mislabel them after inspection.

Never claim the finished artwork exists unless the PNG is visibly shown and the KRA can be reopened with editable painted content. Counts of tools, steps or layers prove nothing about picture coherence.

## Separation of duties and fail-closed rules

- The executor must not generate a fake "finished picture" via the evaluator/test script or paste the benchmark JPEG as a flattened outcome.
- The VLM must receive the actual benchmark AND the actual finished exported artwork as images, check every object and spatial relation, and reject abstract tests masquerading as a landscape.
- The person running the executor may generate machine-readable logs, but must not impersonate an independent human reviewer or fill human approval as if it already happened.
- Missing human review, VLM review, final PNG, real KRA or meaningful layer evidence means NOT ACCEPTED. Report what is pending instead.
- Technical safety remains mandatory: do not reuse uncertain native strokes, overwrite personal art, kill unrelated Krita PIDs or publish sensitive files.

## Publishing

Raw acceptance runs stay under artwork-results and are ignored by Git to prevent accidental leaks and massive commits; they are STILL present locally. Only after real visual and human acceptance, run scripts/prepare_artwork_publish.py to stage a small curated preview and public metadata. That script never performs git push. Review privacy/licenses, then explicitly commit curated files if authorized. Full KRA needs separate LFS/Release approval.
