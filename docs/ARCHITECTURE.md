# Krita Agent architecture and safety policy

## Runtime-proven foundation

**Round 1 and Round 2 are verified** by real build-specific acceptance: see REPORT-004, REPORT-006 and REPORT-007. Stable 5.3.4.1 / Next Qt5 5.4.0-prealpha / Next Qt6 6.1.0-prealpha are the three documented environments. Round 3 installed-build acceptance and repairs are recorded in REPORT-009. A feature's availability always refers to a concrete build and test.

```text
CLI / SDK (Windows Python)
  cli.py                explicit user commands; no invisible agent actions
  protocol/workflow     bounded, schema-constrained drawing steps
  creative_plans        deterministic geometry/layer planner
  revisions             target-image diff, approval and live projection preflight
  feedback              local PNG comparisons and SHA256
  task_store            archived execution plan; no token storage
  upstream/upstream3     Git SHA source inventory, reviewed capability evidence
           |
     authenticated 127.0.0.1 newline JSON (token, request ID, limits)
           |
Krita Plugin, in-process Qt GUI context
  __init__.py           main Bridge server, dispatcher, task queue
  advanced.py           explicit allowlisted command routing
  advanced_documents    selection and multi-document management
  advanced_layers       native node operations
  advanced_media        RGBA U8 import, previews
  advanced_transforms   native transform/undo controls
  advanced_checkpoint   safe action router
  checkpoints           immutable KRA + manifest; manual fresh-copy recovery
  pixel_history         independent reversible BGRA U8 transaction journal
  clipboard_store       opt-in compressed RGBA clipboard artifacts
  advanced_round3       mask/filter/selection/color/brush router
  advanced_masks        non-destructive filter and mask nodes
  advanced_selection    selection algebra and feather/grow/shrink
  advanced_color        model/depth/profile inspection, checkpoint-gated conversion
  advanced_brushes      resource metadata only
  docker.py             opt-in local job/history/error/preview panel
           |
     Krita LibKis + native editable KRA documents
```

## Fundamental operational boundaries

- **Ownership:** never modify unrelated Krita instances or user artwork. The launch process is explicit, and ordinary Krita launches leave Bridge inert.
- **IPC:** localhost-only listener, randomized token, command allowlist; no remote shell, eval or arbitrary Python is accepted. Real byte bounds and GUI timeout are enforced.
- **GUI thread:** Krita and Qt API operations execute on Krita's GUI thread. One long native stroke cannot be interrupted mid-call. Pause and cancel operate between steps.
- **Files:** root-resolved output/input sandboxes with no silent overwrite; symlink traversal is refused. A snapshot always saves to a new KRA filename.
- **Recovery:** job journal writes to disk; interrupted means *unknown for the in-flight step*. Explicit recovery copies verified checkpoint KRA and only then optionally submits steps after the checkpoint, never automatically reusing damaged memory artwork.
- **Reversible pixels:** before and after bytes are saved independently of Krita's Undo. A mismatching current layer buffer is a hard refusal, not an invitation to overwrite.
- **Selection clips:** clipboard artifacts are bounded, checksummed and opt-in; they are not the system clipboard.
- **Non-destructive masks:** use real Krita nodes; never quietly replace paint layer pixel data when requesting a filter mask.
- **Color:** RGBA U8 raw pixel operations remain gated; other colorspaces can be inspected but only explicitly converted after a trusted KRA snapshot.
- **Revision:** deterministic target reference diff, explicitly approved bounded rectangle, verified live projection, one visible fully opaque normal paint layer. General multilayer semantic image edits are deferred.
- **Upstream:** read-only local Git inventory and reviewed runtime evidence. Source_seen never silently becomes tested_working.

## Status maintenance

Roadmap/README references must distinguish implementation versus actually verified capabilities. Reports are immutable historical milestones. Only an actual native acceptance report, with sanitized reproducible evidence, may advance Round 3 status. Manual-only GitHub workflow remains opt-in; no CI or desktop test was launched while authoring this round.

Round 3 acceptance completed with 57 offline tests and native, pixel, controlled-crash and actual Dock evidence; see REPORT-009. Atomic metadata replacement has bounded Windows sharing-lock retries; integrity and root bounds are checked before recovery writes.
