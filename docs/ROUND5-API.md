# Round 5 API — safe continuation and scene preflight

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

Continuation is refused unless all of these are true:

- `--confirm` is present.
- The ledger is in `prepared` or `ready_for_next_batch` state and has no current in-flight batch.
- The supplied workflow hash, batch size, batch count, completed-prefix indices and batch hashes match the ledger.
- The most recent completed KRA checkpoint exists and matches its SHA-256.

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
