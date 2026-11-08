# Round 5 acceptance checklist

Round 5 code changes are not a new native Krita acceptance report. Use three independent statuses: source authored, offline CI passed, and native/full-artwork accepted.

## R5-A — Explicit long-job continuation

- [ ] New ledger persists the workflow digest, batch size/count, completed prefix and verified checkpoint metadata.
- [ ] Resume requires explicit confirmation and a safe ledger state.
- [ ] Resume refuses changed source, non-contiguous batch history, missing/modified KRA checkpoint, and old ledger schema.
- [ ] Restore the latest checkpoint to a fresh KRA copy before submitting the suffix; verify returned file SHA and document identity.
- [ ] Inject a lost restore reply and verify the ledger becomes unknown_needs_review, with no suffix submission and no repeated restore.
- [ ] Inject a lost reply and verify zero automatic retry; unknown states remain blocked.
- [ ] Verify continuation submits only the first not-yet-completed batch.

## R5-B — ScenePlan preflight

- [ ] Validate through the same allowlisted ScenePlan v2 compiler used by compile/submit.
- [ ] Report layer, role, stroke, shape, point and command metrics deterministically.
- [ ] Block a plan with no drawing operations or fewer than the requested number of painted layers.
- [ ] Warn on empty layers and coordinates outside the declared canvas.
- [ ] Confirm validation performs no Krita connection or document mutation.
- [ ] Do not present structural preflight as visual or semantic artwork acceptance.

## R5-C — Review evidence v2

- [ ] Bind the visual review to the exact reference, final PNG, editable KRA and three stage-preview SHA-256 values.
- [ ] Require concrete evidence for every required object and spatial relation.
- [ ] Bind human review to the exact final PNG/KRA and require KRA reopen confirmation.
- [ ] Reject missing, malformed, stale, negative or incomplete reviews.
- [ ] Keep the auditor's role limited to artifact integrity; reviewers remain responsible for visual judgement.

## R5-D — Automated CI

- [ ] Run offline tests automatically on pushes to feature branches and pull requests to main.
- [ ] Cover Python 3.10 and 3.13 on Windows.
- [ ] Compile source, plugin, scripts and tests before running pytest.
- [ ] Keep native Krita acceptance separate; CI runners do not claim to host a supported interactive Krita session.

## R5-E — ScenePlan v3 and model provider

- [ ] Validate a human-authored ScenePlan v3: unique IDs, object hierarchy, bound regions, valid geometry and actual brush strokes.
- [ ] Run a real JSON-capable model to produce a new multi-object plan from a natural-language brief; record provider model and proposal hash without secrets.
- [ ] Compile through ScenePlan v2 and confirm no unvalidated IPC command escapes.
- [ ] Confirm distinct cloud/mountain/water/vegetation pressure dynamics; test manual reviewed preset selection and unknown preset refusal.
- [ ] Test unusable model output, invalid bounding boxes, unsupported object types and profile mismatch fail closed.

## R5-F — Multimodal critic, revisions and workflow integration

- [ ] Give the visual model the ACTUAL exported PNG bytes, optional benchmark and up to three actual on-canvas object crops; confirm it identifies localized real defects.
- [ ] Enforce one evidence-grounded object finding for EVERY planned object and refuse contradictory overall approval.
- [ ] Record actual PNG hash, model ID, observations, issue ROI, target object, finite round index and hashes of the cropped image regions.
- [ ] Verify a positive internal critic result never masquerades as independent artwork acceptance.
- [ ] Test revision proposal and user approval, bounded strokes, source hash and live-pixel re-export preflight.
- [ ] Verify revisions paint only on a NEW editable layer, with pre-revision KRA checkpoint.
- [ ] Inject lost reply during native painting, export and revision. No double submission or automatic replay.
- [ ] Run creative init → plan → approve → paint → export → critique → revise → export → deliver and retain every version of editable KRA and PNG.
- [ ] Check `creative status` and the escaped, read-only `creative dashboard` for current stage, retained PNG versions, actual native stage previews, history, missing/unknown state and security boundaries.
- [ ] No model credential or artwork data appears in committed GitHub evidence.

## R5-E — Native full-artwork milestone (pending)

- [ ] Run the immutable sunset-alpine-lake benchmark in an owned disposable Krita session.
- [ ] Save the real KRA, its matching PNG export, actual Krita screenshot, execution provenance and layer graph.
- [ ] Verify at least eight genuinely contributing editable paint layers.
- [ ] Save three real Krita full-canvas stage snapshots (layout/color/final) at object-group boundaries; verify their output SHA values and archive them under the run directory.
- [ ] Save independent visual-model and human reviews bound to real PNG/KRA/stage hashes.
- [ ] Reopen the KRA and rerun the artifact auditor.
- [ ] Retain failed runs and all forensic evidence. Do not create synthetic evidence or mark this gate passed from source/CI tests.

## Explicitly deferred

Open-ended natural-language image generation, generative inpainting, arbitrary multilayer reverse compositing, high-bit-depth pixel writes, general ICC correctness, unattended cloud model calls, and headless native painting remain deferred. These require separate design, dependency/security review and native evidence.
