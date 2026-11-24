# Round 12 — integrated workflow observability and effort profiles

**Status:** source implementation on `feat/round12-generalist-acceptance`. This is an operational integration milestone, not a claim that the multi-genre artwork benchmark has passed.

## User-controlled effort profiles

Briefs accept `complexity` (`quick_sketch`, `standard`, `detailed`), `max_native_steps` (100–10,000) and optional `time_budget_minutes` (1–480). Default step ceilings are 2,500 / 6,000 / 10,000. An explicit step ceiling overrides the profile default. The ceiling is checked after compilation and before plan archival/approval; over-budget plans fail rather than silently dropping strokes. The time budget is advisory, not a hard timeout.

Example JSON brief:

    {
      "prompt": "Paint a ceramic teapot on a wooden table in morning light.",
      "width": 1600,
      "height": 900,
      "style": "painterly illustration",
      "complexity": "detailed",
      "max_native_steps": 8500,
      "time_budget_minutes": 35
    }

## Operation telemetry

The CreativeWorkflow records duration and before/after state for plan, approval, paint/stages, export, KRA recording/reopen, visual review, revisions and delivery.

- File: `operation-metrics-v12.jsonl` in the run directory.
- Integrity: append-only SHA-256 chain, bounded to 8 MiB / 50,000 events.
- Privacy: no prompts, model responses, image bytes, API keys, local paths or exception messages; failures store only the exception class.
- The workflow remains single-writer. Telemetry is best-effort and cannot change the result of a native operation.
- Corrupt chains are reported as `integrity: corrupt`; no new event is appended to an invalid chain.

Inspect metrics with `krita-agent creative metrics --directory ./artwork-results/run-1`; regenerate the read-only dashboard with `creative dashboard --directory ... --replace`. Timings can be nested (export may call record and reopen); do not sum them as wall-clock run time.

The dashboard reports compiled brush/pressure diversity only when the compiled plan hash matches the manifest. These are **planned values**, not proof that Krita executed the plan or that an installed preset visibly responds to pressure.

## Reopen drift diagnostics

Pixel comparisons now report per-channel changed-pixel counts and absolute-delta sums, mean absolute channel difference, and half-open difference bounds `[x_min,y_min,x_max,y_max]`. Strict RGBA equality remains the only pass condition. Diagnostics help localize drift; they do not identify its cause or waive delivery integrity.

No Windows build, cloud-native performance, multi-genre artwork or human acceptance is claimed by this source milestone.
