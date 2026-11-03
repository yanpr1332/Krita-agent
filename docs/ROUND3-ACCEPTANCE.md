# Round 3 complete acceptance checklist — NOT EXECUTED

**All items below are pending.** This is an execution plan, not a test result. Verify on a later authorized turn. Do not reuse user artwork or kill any Krita process that this test does not own.

## A. Safe environment and sources

- [ ] Record exact main commit, Round 3 branch/commit, Stable/Next binary versions, Python/Qt bindings and system paths.
- [ ] Back up shared Krita plugin resources, confirm the installer dry-run, then explicitly deploy the Round 3 plugin; use a disposable Krita profile if supported.
- [ ] Run isolated sessions **one build at a time** with unique temporary output directories and session tokens; use only disposable artwork and known test PIDs.
- [ ] Run lint/static syntax review and offline tests (including all pre-existing 34 tests); do not claim pass counts until actually run.
- [ ] Verify source tree has no real art, credentials, temporary caches or unreviewed binary test assets.

## B. Checkpoints and recovery (R3-A)

- [ ] Create a KRA checkpoint; assert ZIP archive includes maindoc.xml and SHA-256 matches manifest. Open it and verify pixel/layer equality.
- [ ] Confirm default no-overwrite and path-traversal/symlink escape refusal.
- [ ] Submit a 300–400-step job with checkpoint after a known step, observe journal after checkpoint, then **kill only test-owned process** at controlled points (before save, after save, during next stroke).
- [ ] Restart Bridge, verify interrupted state and *zero automatic playback*. Inspect checkpoint, recover into a distinctly named copy. Compare original KRA unchanged and recovered pixels to checkpoint.
- [ ] With explicit confirmation, resume suffix after checkpoint. Verify steps and terminal state, no duplicated old strokes, no unapproved file writes.
- [ ] Refuse mismatched SHA, manipulated manifest, missing KRA, changed original job fingerprint, running-job recovery, and forbidden suffix commands.
- [ ] Report actual system timings and storage size (without claiming atomic transactions across external effects).

## C. Reversible pixels and clipboard (R3-C)

- [ ] On RGBA U8 layer, fill/clear/patch a small region; compare pre/post BGRA pixel values and validate transaction manifest.
- [ ] Undo and redo via independent pixel history; require exact digest match; refuse if pixels were edited meanwhile or layer/document identity changed.
- [ ] Test malicious/oversize compression and invalid clipboard schemas (no unbounded decompression).
- [ ] Save a selection clipboard, stop/restart test Krita, load it from approved output/clips and paste source-over. Assert pixels/alpha and memory cap.
- [ ] Reject nonexistent/locked layers, invalid color, read outside input root, write outside output root and missing confirm flags.
- [ ] Verify direct pixel transactions are **not claimed to be native Krita undo**.

## D. Native masks, filters, advanced selection and color (R3-B/F)

- [ ] Create transparency mask and selection mask from nonempty selections; verify mask effect in PNG and retained KRA after reopen.
- [ ] Create non-destructive filter layer and mask using known installed filter; verify output while toggling filter visibility, then undo/reopen.
- [ ] Verify filter configuration with allowed scalar inputs, unknown/unavailable filter refusal and behavior on locked nodes.
- [ ] Feather, grow, shrink, invert, border, smooth and combine replace/add/subtract/intersect/xor; compare coverage and resulting pixel bounds.
- [ ] Query brush presets/profile and native capability flags in each Krita build; do not infer pressure mapping from resource names.
- [ ] Inspect RGBA U8, RGBA U16, grayscale, float depth/ICC profiles where installed. Verify unsupported byte writes are refused.
- [ ] Attempt color conversion **without** backup (must refuse) and with explicit current checkpoint (then verify profile, visually compare reference and KRA integrity). No blanket claim of full colorimetric correctness.

## E. Structured drawing, review and revision loop (R3-D/E/I)

- [ ] Compile scene JSON offline; verify layer order, stroke sample bounds, consistent pressure/tilt/time and deterministic output.
- [ ] Generate Krita live full-canvas preview, compare source/target alpha-aware RGBA; generate a bounded changed-region plan.
- [ ] Apply an approved revision on exactly one fully opaque visible normal paint layer, after a confirmed checkpoint. Confirm the old layer is untouched/hidden and new copy patch is on an editable layer.
- [ ] Compare target vs after-preview **pixel by pixel** within and outside the intended ROI; save/reopen resulting KRA and verify both layer structure and output.
- [ ] Refuse changed reference checksum, stale live preview, multiple visible layers, non-normal blend, large ROI, different canvas size, missing explicit confirmation, non-RGBA U8 image, and concurrent active job.
- [ ] Check no-change plans perform no mutation. Record recovery method after failure between duplicate/patch/hide steps.
- [ ] Do not claim open-ended semantic creative reasoning: structured scene planning and deterministic reference-image patching are the implemented scope.

## F. Upstream and capability evidence (R3-G)

- [ ] Compare two controlled Git SHAs with Python AST method add/remove/signature change and header heuristic examples.
- [ ] Check source URL and file scope; confirm source changes alone remain source_seen; no source code executes.
- [ ] Ingest real Stable/Next runtime probes and manually reviewed passing evidence; reject unsupported or fake evidence state promotion without confirmation.
- [ ] Check registry update for a second evidence record, duplicates, and atomic storage failure handling; baseline unchanged by failed fetch.

## G. Dock, regression and documentation (R3-H)

- [ ] Qt5/Qt6 Dock visually displays connection, 8 recent jobs, errors and preview without clipping at different DPI/scale.
- [ ] Actual UI click Pause/Resume/Cancel during 400-step job in three builds; inspect Bridge responses and job history.
- [ ] Run full Round 1 and 2 regression scripts and 34 previously passing offline tests, then new Round 3 tests; record **actual** totals.
- [ ] Confirm no new Qt/Krita plugin import error, deadlock, leaked socket/IPC thread or shared-resource overwrite.
- [ ] Verify README/README.zh-CN, ROADMAP and ARCHITECTURE agree with REPORT-008 and measured results; update support matrix with evidence.
- [ ] Commit an actual Round 3 acceptance report and sanitized evidence under docs/acceptance-evidence; do not commit real client artwork, tokens or temporary workspaces.

## Pass criteria

All safety gates must pass, even if a specific installed Krita build legitimately lacks an optional API; unsupported features must cleanly report an unsupported capability. Feature-specific acceptance requires both API response and pixel/KRA evidence. Any failures must be documented precisely, repaired in the branch and retested before marking complete. **No tests were launched in the Round 3 implementation task.**
