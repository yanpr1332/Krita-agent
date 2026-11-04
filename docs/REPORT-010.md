# Round 4 implementation report (source only) — 2026-11-04

Repository: yanpr1332/Krita-agent
Branch: feat/round4-layer-aware-painting
Base main: 0e48612e2914723ce9710aa4478ab3f5a5ab24fc

## Implemented source

R4-A/B: Native document graph with hierarchy and stable-ID rebind proposals; bounded Krita projection tile snapshots; conservative opaque-only goal overlays on a NEW editable top-level layer. Live graph and tile hash preflight, safe output paths and confirmed KRA snapshot precede canvas mutations. Source nodes are left intact.

R4-C/E: Optional offline Pillow pyramid PNG generation supplements bounded previews. Long-workflow coordinator serializes up to 10,000 raw steps into bounded existing Bridge jobs, with a checkpoint at each batch boundary, atomic ledger writes and no retry on uncertain remote effects. 512–1024px ROI tiles and pyramid layout metadata support planning for 4096x4096 workloads without copying the entire image through the JSON IPC.

R4-D: Manual, build-specific, SHA-backed brush calibration record and preferred-preset selection (including optional ScenePlan v2 selection); plan generator only, never manufactured evidence. Long-stroke segmentation requires allow_seams=true and changes native stroke/Undo semantics.

R4-F/G: ScenePlan v2 semantic layer planning and deterministic sample compiler; local alpha-aware difference review with finite, explicitly approved revisions. No LLM, image generation, semantic critic or automatic multi-round actions are invoked.

R4-H/I: CLI entry points, editable project artifact manifests, GUI-thread step timing, Dock telemetry, typed SDK v2 protocol DTOs, compatibility evidence matrix and new offline regression test source.

## Important nonclaims and constraints

- All NEW Round 4 functions are **UNVERIFIED** on local Krita builds; Round 1/2/3 historical test evidence does not verify Round 4.
- Multi-layer overlays do not invert arbitrary blend modes, masks or semi-transparent target pixels. Only opaque changed regions are supported. Original editability is preserved via a separate overlay layer. Exact visual order is a native acceptance item.
- Existing v1 wire limits stay at 1MiB/400 steps/2048 native points. Long jobs are serial sub-jobs, not a new unlimited native stroke API; long strokes can still block the UI.
- A lost result is unknown. The scheduler stops, saves ledger and does NOT blindly retry; manually confirm job and checkpoint state.
- Pyramids describe tile layout; no new Qt multi-resolution renderer is claimed. Other color depths remain guarded for raw pixel edits.
- Brush dynamics require real test evidence; ScenePlan v2 uses deterministic JSON, not natural-language intelligence; feedback only proposes.
- No additional third-party Krita plugin was required. Optional Pillow is used offline.

## Validation state

The user requested CODE + checklists, not verification. No tests, installed Krita launch, plugin install, screenshots, Actions runs or manual acceptance were executed in this turn. Round 4 checkout must be independently verified against Stable Qt5, Next Qt5 and Next Qt6 using ROUND4-ACCEPTANCE.md; only then create REPORT-011.

Historical reports remain immutable. New source is committed on an isolated branch; main is untouched.
