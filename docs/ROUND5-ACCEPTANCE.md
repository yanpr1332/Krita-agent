# Round 5 acceptance checklist

The [local acceptance report](ROUND5-LOCAL-ACCEPTANCE.md) records the November 9 offline and installed-build results. Items still requiring a real provider or final artwork approval remain open.

## R5-A — Explicit long-job continuation

- [x] New ledger persists the workflow digest, batch size/count, completed prefix and verified checkpoint metadata.
- [x] Resume requires explicit confirmation and a safe ledger state.
- [x] Resume refuses changed source, non-contiguous batch history, missing/modified KRA checkpoint, and old ledger schema.
- [x] Restore the latest checkpoint to a fresh KRA copy before submitting the suffix; verify returned file SHA and document identity.
- [x] Inject a lost restore reply and verify the ledger becomes unknown_needs_review, with no suffix submission and no repeated restore.
- [x] Inject a lost reply and verify zero automatic retry; unknown states remain blocked.
- [x] Verify continuation submits only the first not-yet-completed batch.

## R5-B — ScenePlan preflight

- [x] Validate through the same allowlisted ScenePlan v2 compiler used by compile/submit.
- [x] Report layer, role, stroke, shape, point and command metrics deterministically.
- [x] Block a plan with no drawing operations or fewer than the requested number of painted layers.
- [x] Warn on empty layers and coordinates outside the declared canvas.
- [x] Confirm validation performs no Krita connection or document mutation.
- [x] Do not present structural preflight as visual or semantic artwork acceptance.

## R5-C — Review evidence v2

- [x] Bind the visual review to the exact reference, final PNG, editable KRA and three stage-preview SHA-256 values.
- [x] Require concrete evidence for every required object and spatial relation.
- [x] Bind human review to the exact final PNG/KRA and require KRA reopen confirmation.
- [x] Reject missing, malformed, stale, negative or incomplete reviews.
- [x] Keep the auditor's role limited to artifact integrity; reviewers remain responsible for visual judgement.

## R5-D — Automated CI

- [x] Run offline tests automatically on pushes to feature branches and pull requests to main.
- [x] Cover Python 3.10 and 3.13 on Windows.
- [x] Compile source, plugin, scripts and tests before running pytest.
- [x] Keep native Krita acceptance separate; CI runners do not claim to host a supported interactive Krita session.

Cloud evidence: [GitHub Actions run 42468603707](https://github.com/yanpr1332/Krita-agent/actions/runs/42468603707), code revision `689535a`: 129 pytest cases and compileall on each of Windows Python 3.10 and 3.13. The local checks below were run separately from this CI job.

## R5-E — ScenePlan v3 and model provider

- [x] Validate a human-authored ScenePlan v3: unique IDs, object hierarchy, bound regions, valid geometry and actual brush strokes.
- [ ] Run a real JSON-capable model to produce a new multi-object plan from a natural-language brief; record provider model and proposal hash without secrets.
- [x] Compile through ScenePlan v2 and confirm no unvalidated IPC command escapes.
- [ ] Confirm distinct cloud/mountain/water/vegetation pressure dynamics; test manual reviewed preset selection and unknown preset refusal.
- [ ] Test unusable model output, invalid bounding boxes, unsupported object types and profile mismatch fail closed.

## R5-F — Multimodal critic, revisions and workflow integration

- [ ] Give the visual model the ACTUAL exported PNG bytes, optional benchmark and up to three actual on-canvas object crops; confirm it identifies localized real defects.
- [ ] Enforce one evidence-grounded object finding for EVERY planned object and refuse contradictory overall approval.
- [ ] Record actual PNG hash, model ID, observations, issue ROI, target object, finite round index and hashes of the cropped image regions.
- [x] Verify a positive internal critic result never masquerades as independent artwork acceptance.
- [x] Test revision proposal and user approval, bounded strokes, source hash and live-pixel re-export preflight.
- [x] Verify revisions paint only on a NEW editable layer, with pre-revision KRA checkpoint.
- [x] Inject lost reply during native painting, export and revision. No double submission or automatic replay.
- [x] Exercise the full local lifecycle with real Stable Krita, a supplied plan and an explicitly identified technical provider double. Both KRA/PNG versions are retained.
- [ ] Repeat the full lifecycle using the real configured model provider.
- [x] Check `creative status` and the escaped, read-only `creative dashboard` for current stage, retained PNG versions, actual native stage previews, history, missing/unknown state and security boundaries.
- [x] No model credential or artwork data appears in committed GitHub evidence.

## R5-E — Native full-artwork milestone (pending)

- [x] Run the immutable sunset-alpine-lake benchmark in an owned disposable Krita session.
- [x] Save the real KRA, its matching initial PNG export, actual Krita screenshot, execution provenance and layer graph.
- [x] Verify at least eight genuinely contributing editable paint layers. Next Qt6 had 29 in the first run and 30 in the retest by native per-layer hide and pixel comparison.
- [x] Save three real Krita full-canvas stage snapshots (layout/color/final) at object-group boundaries; verify their output SHA values and archive them under the run directory.
- [x] Record the independent visual-model verdict bound to real PNG/KRA/stage hashes. The first retest verdict was fail. The final visually refined KRA and PNG passed independent review.
- [ ] Record an independent human review for the same artifact.
- [x] Reopen the KRA and record the pixel comparison. The original and visually refined Qt6 KRA copies were each repaired with an editable five-pixel layer. Three fresh reopen exports per repaired KRA matched their respective original PNG at every RGBA pixel.
- [ ] Run the formal artifact auditor after both independent reviews.
- [x] Retain failed runs and all forensic evidence. Do not create synthetic evidence or mark this gate passed from source/CI tests.

## Explicitly deferred

Open-ended natural-language image generation, generative inpainting, arbitrary multilayer reverse compositing, high-bit-depth pixel writes, general ICC correctness, unattended cloud model calls, and headless native painting remain deferred. These require separate design, dependency/security review and native evidence.

## R5-G — Export Integrity and fresh-reopen default gate

- [x] Source path archives real original KRA/PNG before any comparison, including failures, without overwrite.
- [x] Source path separates embedded-composite Export Integrity from fresh-Krita Reopen Stability; records pixel/alpha maxima, counts and profile data.
- [x] Source path blocks critique/delivery on strict mismatch while reporting explicit minor RGB tolerance separately.
- [x] Source path supports an explicitly approved repaired candidate as a new preserved version.
- [x] Offline test doubles cover exact reopening, five-pixel drift, export mismatch, immutable repair version and lost Bridge reply.
- [ ] Re-run on real Stable, Next Qt5 and Next Qt6 Krita installations with fresh copies and inspect output evidence.
- [ ] Isolate and fix the original Qt6 five-pixel rendering difference at its actual root cause; a correction layer is not a root-cause fix.
