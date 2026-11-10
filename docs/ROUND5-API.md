# Round 5 API — autonomous creative workflow, safety and evidence

Round 5 adds offline controller-side capabilities. It does not add remote execution, cloud image generation, or new Krita-native drawing APIs. The current Bridge remains authenticated localhost IPC.

## 1. Explicit long-job continuation

A long job writes a durable ledger and a KRA checkpoint after every bounded batch. New ledgers record the original workflow digest, batch size, completed batch digests, checkpoint path/hash, and resume count.

```powershell
# Plan and start a new job
krita-agent longjob plan --file ".\examples\round4-longjob.json" --batch-size 120
krita-agent longjob run --file ".\examples\round4-longjob.json" --ledger-dir ".\logs"

# Inspect the ledger returned by the run
krita-agent longjob inspect --file ".\logs\long-job-LEDGER_ID.json"

# Continue only from a known, verified batch boundary
krita-agent longjob resume --file ".\examples\round4-longjob.json" --ledger ".\logs\long-job-LEDGER_ID.json" --confirm
```

Before the next batch is submitted, the scheduler sends an explicit checkpoint.restore request. Krita opens a new recovery copy; the returned file hash and document identity are verified. The restore intent is persisted before the request, so a lost restore reply becomes unknown_needs_review and is never repeated automatically. A prepared ledger with no completed checkpoint is not resumable.

Continuation is refused unless all of these are true:

- `--confirm` is present.
- The ledger is in `ready_for_next_batch` state, contains at least one completed batch, and has no current in-flight batch.
- The supplied workflow hash, batch size, batch count, completed-prefix indices and batch hashes match the ledger.
- The most recent completed KRA checkpoint exists and matches its SHA-256, including its checkpoint ID and document identity.
- Krita confirms a fresh recovery copy was opened and its file hash/document identity match before any remaining batch is submitted.

Ledgers in `submitting`, `running`, or `unknown_needs_review` are not resumable. A missing job ID, lost response, ambiguous native effect, old ledger without batch metadata, or modified checkpoint is a hard refusal. Inspect the artwork and recover manually using the existing checkpoint workflow; never rerun the uncertain batch.

## 2. ScenePlan v2 structural preflight

```powershell
krita-agent scene-v2 validate --file ".\examples\round4-scene-v2.json"
krita-agent scene-v2 validate --file ".\plans\landscape.json" --min-painted-layers 8
krita-agent scene-v2 compile --file ".\plans\landscape.json" --output ".\plans\compiled.json"
krita-agent scene-v2 submit --file ".\plans\landscape.json" --ledger-dir ".\logs"
```

Validation compiles through the existing allowlist without connecting to Krita or creating a document. It reports native drawing operations, painted-layer candidates, strokes, shapes, points, semantic layer roles, and coordinates outside the declared canvas. Empty layers and off-canvas coordinates are warnings; insufficient painted layers or no drawing operations block the plan.

A `ready` result means only that the structured plan passes these deterministic checks. It does not prove that the output will be recognizable, coherent, or artistically complete. Use the independent full-artwork acceptance process for that claim.

## 3. Evidence-bound artwork review v2

The local artwork auditor now requires review records bound to the exact final PNG, editable KRA, locked reference, and three stage previews. The visual-model review must provide a concrete observation for each required object and relation. The human review must confirm that the KRA was reopened and all required objects were recognized.

```powershell
python scripts\artwork_acceptance_audit.py --run-dir artwork-results\<run-id>
```

The audit checks files, hashes, KRA/PNG consistency, image readability, editable layer evidence and review-record integrity. It cannot prove that a reviewer actually inspected the images, cannot judge artistic quality, and cannot substitute for a human decision.

## Compatibility

- Python package version: `0.6.0.dev0`.
- Existing Krita Bridge IPC remains v1.
- Round 4 commands and ledger files are not silently replayed or migrated.
- Old ledgers without `batch_steps` metadata are inspection-only.

## 4. Full Creative Workflow CLI (R5-A through R5-F)

The Round 5 engine composes existing Krita native commands; the model cannot write arbitrary IPC commands. A model provider is **optional**: user-supplied ScenePlan v3 JSON can be compiled offline. A model-enabled run requires an explicitly configured OpenAI-compatible HTTPS chat-completions endpoint and a JSON-capable model. Model compatibility must be checked against your chosen provider.

Install optional image support: `python -m pip install -e ".[feedback]"`.

A creative brief can be a UTF-8 text file or JSON:
```json
{
  "prompt": "Draw an evening mountain lake with varied clouds and snow peaks, reflections, pine forest and detailed foreground.",
  "width": 1600,
  "height": 900,
  "title": "Evening Alpine Lake",
  "style": "layered painterly illustration"
}
```

Start with `krita-agent creative init --directory artwork-results/run-001 --brief-file brief.json`.
For a model-enabled run set the environment variable `KRITA_AGENT_MODEL_API_KEY` locally (never commit credentials). `KRITA_AGENT_CHAT_COMPLETIONS_URL` optionally specifies an HTTPS endpoint; the default adapter uses `https://api.openai.com/v1/chat/completions`. The model receives the user brief, and a reference image **only when you explicitly pass `--reference`**.

```powershell
# Plan from a JSON-producing model (requires explicit external model credentials)
krita-agent creative plan --directory artwork-results/run-001 --model YOUR_JSON_MODEL --reference benchmarks/artwork/reference/sunset_alpine_lake.jpg

# Or plan entirely offline from a human-authored ScenePlan v3 JSON
krita-agent creative plan --directory artwork-results/run-001 --candidate proposed-scene-v3.json

# Inspect creative-proposal.json and compiled-scene.json BEFORE approving
krita-agent creative approve --directory artwork-results/run-001 --confirm

# Run against an explicit already-authorized local Krita Bridge session
krita-agent creative paint --directory artwork-results/run-001 --session SESSION.json
krita-agent creative export --directory artwork-results/run-001 --session SESSION.json

# Model sees the actual PNG bytes, not the filename or object labels alone
krita-agent creative critique --directory artwork-results/run-001 --model YOUR_VISION_MODEL --reference benchmarks/artwork/reference/sunset_alpine_lake.jpg

# When Critic reports a problem, plan and approve localized native strokes
krita-agent creative revision-plan --directory artwork-results/run-001 --object-id clouds --model YOUR_VISION_MODEL
krita-agent creative revision-approve --directory artwork-results/run-001 --confirm
krita-agent creative revise --directory artwork-results/run-001 --session SESSION.json --confirm
krita-agent creative export --directory artwork-results/run-001 --session SESSION.json
krita-agent creative critique --directory artwork-results/run-001 --model YOUR_VISION_MODEL

# Only after internal critique has no unresolved issue
krita-agent creative deliver --directory artwork-results/run-001
krita-agent creative status --directory artwork-results/run-001
```

At each step inspect the actual JSON reports. You can give `creative revision-plan` a reviewed `--candidate PATCH.json --issue-id issue-1` instead of contacting a model. Revising always paints into an additional editable layer. Never delete or overwrite previous versions. The final `artwork.kra` and `artwork.png` are prepared for independent human and model acceptance; `deliver` **does not** mark artwork accepted.

State flow: initialized → planned → plan_approved → painting_unknown (while submitting) → awaiting_export → awaiting_critique → ready_for_delivery, or awaiting_revision_proposal → revision_proposed → revision_approved → revision_unknown → awaiting_export → critique again. Unknown reply states cannot be automatically replayed. Images and intermediate plans reside inside the supplied run directory.

**Current limits:** Planner quality depends on the configured model producing meaningful object-specific brush trajectories; Krita native brush availability depends on each installed build; tests do not guarantee attractive output. The vision and revision models require user-supplied credentials and send selected actual artwork pixels off-device. Do not send confidential artwork without review. The code does not run an unattended infinite AI loop and does not install any third-party Krita painting plugin.


### Stronger object-by-object visual critique

The critic sends the actual complete exported PNG and up to three bounded real-pixel crops for the most relevant semantic regions (for example clouds, mountain faces and water). The optional benchmark is sent only when explicitly selected. The model must return a separate `object_findings` entry for **every** scene object, with `recognizable`, `quality` and at least one concrete pixel-grounded `evidence` string. A missing object finding or a contradictory overall pass is a hard failure. The response records crop SHA-256 hashes, the actual full-artwork PNG SHA-256 and the model ID. It still cannot establish that the external model actually observed images or replace independent visual and human acceptance.


## 5. Native stage evidence and read-only dashboard

When a creative run compiles a ScenePlan v3 with at least three separately painted objects, the controller schedules three real Krita `preview.canvas` commands at early, middle and final layer boundaries. Preview dimensions are aspect-preserving and limited to Krita's 2-megapixel snapshot budget (up to 2048 px per side). Their output paths are namespaced under `r5-runs/<run-id>/stages/` to avoid collisions. `creative export` collects actual PNG files from the authorized Bridge output directory, verifies their hashes and saves them in `artwork-results/<run-id>/stages/`. These are real native previews, not an invented testing montage. Runs with too few painted objects do not claim to provide three meaningful stages.

A readable local dashboard can be generated with:

```powershell
krita-agent creative dashboard --directory artwork-results/run-001
# To refresh after stages change:
krita-agent creative dashboard --directory artwork-results/run-001 --replace
```

The static `dashboard.html` shows current stage, actual archived artwork PNG, native stage previews and history events. It uses escaped text, no JavaScript, no cloud access and no direct Krita control. This is not a live Krita Dock widget. Final human and independent VLM review still occur separately.

## 6. Export Integrity and Reopen Stability (post-acceptance correction)

Every `creative export` now first archives the original native KRA/PNG to unique immutable `versions/vNN.*` paths, **including failing versions**. It calculates:

- **Export Integrity:** exact RGBA comparison of embedded `mergedimage.png` against the first exported PNG.
- **Reopen Stability:** copy the archived KRA to a unique path in the authorized Bridge output sandbox, open that copy in Krita, export a new PNG, close the copy, restore the original document, then compare the new PNG against the first. A lost Bridge reply leaves `unknown_needs_review` and is never replayed automatically.

Each comparison records changed pixel count, max RGB and channel differences, alpha-changed pixel count/max delta, image dimensions, and color configuration (KRA profile/model/depth and PNG ICC hashes, gamma, sRGB intent, mode). **Only pixel-exact results pass.** Diagnostic tolerance is separately shown: RGB delta at most 1, changed-pixel ratio at most 0.0001, and no alpha differences. Matching pixels with mismatched PNG color profiles also fails Reopen Stability.

Both reports and the actual reopened PNG are archived per version (`vNN-integrity.json`, `vNN-integrity-verified.json`, `vNN-reopened.png`). Failed versions enter `review_blocked`, preventing critique and delivery. Successful versions enter `awaiting_critique`. Missing/lost native results enter `unknown_needs_review`. The final delivery includes `reopened.png` and `reopen-evidence.json` as well as the KRA/PNG pair; the artwork auditor requires those files and recomputes both strict comparisons.

```powershell
# Native export now performs both verifications by default:
krita-agent creative export --directory artwork-results/run-001 --session SESSION.json

# Manual artifact import also reopens by default; explicit opt-out blocks progression:
krita-agent creative record --directory artwork-results/run-001 --kra ORIGINAL.kra --png ORIGINAL.png --session SESSION.json
krita-agent creative record --directory artwork-results/run-001 --kra ORIGINAL.kra --png ORIGINAL.png --defer-reopen
krita-agent creative verify-reopen --directory artwork-results/run-001 --session SESSION.json

# To archive a separately repaired candidate AFTER a rejected version:
krita-agent creative record --directory artwork-results/run-001 --kra REPAIRED.kra --png REPAIRED.png --new-version --confirm --session SESSION.json
```

Never modify `v01` in place or reinterpret its failed report as a pass. Historical native Qt6 five-pixel differences remain an unresolved root-cause investigation: an exact-pixel correction layer can preserve a deliverable but does **not** explain why a fresh reopen rendered differently. Source implementation and synthetic tests are **not** native-build acceptance.
