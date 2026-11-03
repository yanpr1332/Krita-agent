# Round 3 development report — source completion (2026-11-03)

**Status: committed source, NOT runtime accepted.** Round 1 and Round 2 acceptance remain recorded in REPORT-004, REPORT-006 and REPORT-007; they do not verify any new Round 3 code. No installation, Krita launch, test execution, verification workflow, screenshot inspection or GUI acceptance was performed in Round 3, by request.

## Delivered stages

1. **Checkpoint/recovery:** KRA saveAs snapshots under the authorized output root with SHA-256 manifests, saved job step boundaries, optional explicit restore to a *fresh KRA copy*, and opt-in suffix replay after the saved boundary. The suffix is refused if the prior job is not stopped/interrupted, task fingerprints differ, or the steps contain forbidden commands. The original document is never overwritten or automatically replayed on startup.
2. **Reversible native pixel work:** separate, persisted before/after RGBA U8 pixel transaction records; guarded undo/redo validates exact current buffer digest before writing. This history is distinct from the Krita native undo stack. Patch source files are limited to the authorized input directory; per-edit area is capped.
3. **Cross-session clipboard:** optional file-backed, bounded compressed RGBA U8 selection clipboard. Clipboard archives contain only pixel data and integrity metadata, not process credentials. No system clipboard integration is implied.
4. **Non-destructive editing:** Transparency and selection masks, filter layers and filter masks, filter configuration, selection feather/grow/shrink/combine, brush resource inspection, guarded colorspace conversion after a verified KRA checkpoint.
5. **Structured creativity:** explicit scene compiler for layers, geometric shapes, Bézier or sensor-aware strokes. This is *not* a natural-language or generative image model.
6. **Image-target feedback:** offline RGBA difference analysis, bounded changed-region plans, live projection preflight, immutable backup KRA, source-layer duplication and transactional region patch, followed by a new KRA and preview. The planner requires exactly one visible normal/opaque paint layer, so composited multi-layer revision is not yet generalized. No silent iterative retries.
7. **Upstream tracking:** bounded local Git SHA-level API inventory, Python AST and heuristic C++ header signature comparison, and explicit manual registration of build capability evidence. A source diff cannot automatically elevate a capability to tested_working.
8. **UI and engineering:** expanded optional Dock job/history/error/preview display, CLI and workflow integration, documentation synchronization, example jobs and offline test source, explicit manual test workflow retained.

## Implementation and verification boundary

- Only **Round 1 and Round 2** have documented native acceptance as of this report.
- Round 3 commands are new and **unverified on all Krita builds**. Some native APIs for masks, color conversion, selection operations and filters are build- and profile-specific. Results and compatibility must be established by the new acceptance checklist.
- Checkpoint recovery is not a transaction across arbitrary external resources or steps. A native stroke in flight at crash time may be partially applied in the abandoned document. The restore mechanism starts with a saved KRA copy, never the abandoned in-memory canvas.
- A new revision is supported only with strict source isolation, explicit user approval and a changed rectangle within the size cap. General automatic semantic critique, arbitrary multilayer compositing, mask-aware paint strokes, and unlimited image-size revision are not claimed.
- The new pixel-history undo is independent of Krita's native undo stack; mixing the two should be tested and avoided unless carefully reconciled.
- ICC profile conversion is gated by a checkpoint and has not been validated for colorimetric fidelity. RGBA U8 byte operations are refused on unsupported color spaces.
- No CI workflow was triggered by this task; repository tests are merely added as code.

## Engineering management

Current README files, ROADMAP, ARCHITECTURE, CONTRIBUTING and the Round 2 API header were brought into alignment: Round 2 is accepted per REPORT-007; Round 3 is implementation only. Historic reports remain immutable and are not retroactively reworded.

## Next milestone

Run the complete [Round 3 Acceptance Checklist](ROUND3-ACCEPTANCE.md) in isolated sessions against Stable 5.3.4.1, Next Qt5 5.4.0-prealpha, Next Qt6 6.1.0-prealpha. Record API availability and *pixel-visible* behavior. Fix issues in the same Round 3 branch before PR merge. Do not promote status to tested_working based on merely importing a Python symbol.
