# Krita Agent — Drawing Automation Design

> Historical architecture and feature design, not a current implementation checklist. See [ROADMAP](ROADMAP.md), [REPORT-004](REPORT-004.md), [REPORT-007](REPORT-007.md) and [REPORT-008](REPORT-008.md) for verified Round 1/2 behavior and unverified Round 3 source.
>
> Original planning statement: Planning and technical design draft, not a list of implemented features. Target: Windows 11 x64, with stable Krita and Krita Next builds. All APIs, commands, and behaviors must be validated in the actual target build.

## 1. Purpose and scope

Krita Agent is a planned programmable Windows drawing control system. An external Python CLI and other agents communicate with an in-process Krita plugin to create canvases, plan layers, simulate pressure-sensitive strokes, draw, save, and export.

The project aims to use Krita's native brush engine, represent artwork as reproducible drawing commands, retain editable `.kra` layers, adapt to available stable and Next capabilities, and keep code separate from generated artwork. It is an automation framework, not a finished model that can automatically turn arbitrary text into professional illustrations. Natural-language understanding, composition, and visual iteration follow after the core drawing pipeline is validated.

## 2. Decisions and architecture

The controller runs in native Windows Python, independently of Krita's installation directory. The execution side is a custom Python plugin inside Windows Krita. The proposed transport is a controlled loopback or local IPC channel; a local task queue is an alternative to evaluate. Stable Krita is intended for ordinary use and compatibility tests, Next for new interface research. WSL2 is not required initially.

```text
User / external automation
          ↓
Windows Python CLI / SDK
  command parsing and validation; task queue and status
  geometry, pressure planning, capability routing
  upstream tracking, previews, logs, checkpoints
          ↓ controlled local protocol
Krita Agent Bridge (custom Python Extension)
  validate and schedule whitelisted commands
  use Krita APIs in the correct Qt / GUI context
  operate documents, layers, brushes, and strokes
  return progress, results, and errors
          ↓
Krita native painting engine → layered KRA / exported images
```

The `krita` module belongs to Krita's own scripting environment. An ordinary external Python interpreter cannot control another process simply by importing it. The Bridge is a planned component, not an existing official plugin. Arbitrary remote code execution is not an acceptable protocol.

## 3. Planned features

P0 means initial viability, P1 a fuller creative workflow, and P2 later enhancements. None is implemented yet.

| Area | Planned behavior | Priority and validation |
| --- | --- | --- |
| Discovery | Detect target process, version, plugin and API capabilities | P0; inspect actual runtime, including symbol presence |
| CLI and transport | Start or connect to a selected instance, submit tasks, query, cancel, and return errors | P0; distinguish starting from connecting; choose CLI and IPC implementation later |
| Canvas and layers | Create, open and activate documents; create, name, order, select and hide layers; import references | P0–P1; test `Krita`, `Document`, and `Node` capabilities individually |
| Basic painting | Points, lines, polylines, curves, ellipses, polygons, and pixel data when available | P0–P1; assess `paintLine`, `paintPath`, `paintEllipse`, `paintPolygon`, and `setPixelData` per build |
| Pressure and brushes | Pressure trajectories, brush preset, color, size, opacity, and dynamic response | P0–P1; separately test input values and actual brush response |
| Saving and protocol | Layered `.kra`, PNG / JPEG export, validated JSON tasks and task IDs | P0; verify save / export and idempotency behavior |
| Geometry | Bézier sampling, smoothing, equal-distance resampling, pressure interpolation, optional speed and tilt | P1; determine supported sensors at runtime |
| Creative workflow | Sketch, line art, base color, shadow, highlight; batch jobs and recovery | P1; retain editable layers and task logs |
| Execution control | Progress, safe checkpoint pause / resume, stop, undo / redo, live preview | P1; a stroke already executing may not be interruptible |
| Upstream tracking | Detect relevant API, brush engine and compatibility changes; produce evidence and candidate tests | P1–P2; source visibility is not runtime validation |
| Feedback and revisions | Preview, image analysis, targeted layer or region edits | P1–P2; depends on verified APIs and document snapshots |
| Natural language and styles | Optional model converts a description into a structured plan; brush-driven styles | P2; outcomes are not guaranteed |
| Krita panel | Optional DockWidget for connection, tasks, progress, and logs | P2; Qt and plugin compatibility must be tested |

Brush parameters, filters, selections, and local editing differ by build. Investigate documented actions, Qt interfaces, or other controlled approaches when an API is absent; do not label a theoretical possibility as an implemented capability.

## 4. Pressure-sensitive strokes

The objective is a thin start, thicker middle, and thin end, with potential opacity, tilt, speed, or texture variation. A pressure value is input to a brush, not a guarantee of a visual effect: the chosen preset must map pressure to size, opacity, or another parameter. Test pressure-to-size and pressure-to-opacity separately.

A proposed sample point contains canvas pixel coordinates `x` and `y`, normalized `pressure` in 0–1, and relative `time_ms`; optional speed, x/y tilt, rotation, and other sensor values depend on the API. An example pressure sequence is 0.10, 0.35, 0.90, 0.50, 0.05.

### Stable-build candidate

Investigate `Node.paintLine(pointOne, pointTwo, pressureOne, pressureTwo, ...)` and sample a curve into adjacent segments. Multiple calls are not necessarily equivalent to one continuous freehand stroke: brush spacing, random textures, seams, and undo behavior require real tests. `paintPath` must not be assumed to provide per-point pressure.

### Next candidate

Krita's October 2026 development report describes `StrokePoint` and `Node.paintPolylineStroke(...)`, plus `View.brushPosition`. The source report describes development builds; it does not establish availability in any particular installed version. Inspect the actual runtime and signatures, then draw and compare real continuous strokes. Even if input succeeds, the brush preset determines the pressure response.

Proposed algorithm: construct a Bézier or freehand path; resample by distance and curvature; generate a smooth pressure curve; add supported time, speed, or tilt; use a verified continuous path where available, otherwise a verified segmented fallback; compare width, seams, texture, undo, and performance; retain reproducible parameters and acceptance images.

## 5. Technology and plugin

| Component | Planned choice | Purpose |
| --- | --- | --- |
| Operating environment | Windows 11 x64, Python 3 | Controller, planning, task scheduling |
| Painting application | Stable Krita and optionally Next | Compatibility and new capability validation |
| In-process API | Krita Python Extension and LibKis | Document, layer, brush, drawing, export |
| UI and event loop | Qt / PyQt supplied by the actual Krita build | Safe GUI scheduling; optional dock |
| Communication | Localhost / protected local IPC | Controller–Bridge messages; transport undecided |
| Data | JSON plus schema | Tasks, parameters, results; schema undecided |
| Development | Git, virtual environments, pytest | Version control and tests; versions undecided |
| Research | KDE Invent upstream repository | API implementation and changes |
| Optional future components | LLM and image analysis | Task planning and visual feedback, not required for basic operation |

The Bridge should eventually support lifecycle and status, command allowlisting and validation, error isolation, correct GUI-thread dispatch, feature detection, task progress and cancellation, and optionally a dock. Krita's Scripter and plugin manager may help experiments and deployment. No extra Linux installation or third-party Krita plugin is required by the initial design.

## 6. Draft protocol and CLI

The following are design sketches, not working commands or Krita built-ins:

```powershell
krita-agent doctor
krita-agent connect --target next
krita-agent new --width 2048 --height 2048
krita-agent layer add "Line Art"
krita-agent brush select "configured-ink-brush"
krita-agent brush size 24
krita-agent brush opacity 0.75
krita-agent draw ".\examples\pressure-stroke.json"
krita-agent job status job_001
krita-agent job pause job_001
krita-agent job resume job_001
krita-agent undo
krita-agent preview ".\output\preview.png"
krita-agent save ".\output\artwork.kra"
krita-agent export ".\output\artwork.png"
krita-agent upstream check
```

A possible task shape, subject to schema design and validation:

```json
{
  "schema_version": "0.1-draft",
  "document": {"width": 2048, "height": 2048},
  "layer": "Line Art",
  "brush": {"preset": "configured-ink-brush", "size": 24},
  "strokes": [{"points": [
    {"x": 100, "y": 180, "pressure": 0.10, "time_ms": 0},
    {"x": 220, "y": 140, "pressure": 0.35, "time_ms": 60},
    {"x": 360, "y": 160, "pressure": 0.90, "time_ms": 120},
    {"x": 500, "y": 230, "pressure": 0.50, "time_ms": 180},
    {"x": 650, "y": 250, "pressure": 0.05, "time_ms": 250}
  ]}],
  "output": {"kra": "output/artwork.kra", "preview": "output/artwork.png"}
}
```

The preset is a placeholder identifier. Switching presets and setting brush properties must be verified. The protocol should allow future color, tilt, speed, pressure mapping, undo, retry, and task status data. Pause / resume is designed around safe stroke or task-step checkpoints, not interruption of an in-flight stroke.

## 7. Proposed end-to-end workflow

1. Discover or start the selected Krita instance; identify the real build, Bridge, document state, and callable capabilities.
2. Accept a structured task, or eventually a natural-language description, and plan canvas, layers, brushes, strokes, and pressure.
3. Validate dimensions, pressure, paths, permissions, and task IDs; import a reference when requested.
4. Submit a task over controlled local IPC; create the canvas and editable layers.
5. Prepare the selected layer, preset, color, size, opacity, and pressure mappings only where supported.
6. Execute the verified continuous or fallback drawing path; report progress and use safe checkpoints.
7. Inspect previews, width, opacity, seams, texture, and layer structure; undo, retry, or revise where supported.
8. Save layered `.kra`, export images, retain task parameters and concise logs, and clean temporary data without deleting artwork.
9. In a separate compatibility workflow, inspect upstream changes and propose tests or updates for developer review.

A later optional visual loop may turn a description into a structured plan, render, inspect a preview, and revise part of the work. Basic drawing must remain testable without a cloud vision model.

## 8. Planned layout and data management

```text
src/krita_agent/cli/             CLI
src/krita_agent/bridge/          IPC client and protocol
src/krita_agent/drawing/         geometry, pressure, stroke planning
src/krita_agent/jobs/            queue, state, retries
src/krita_agent/compatibility/   capability adapters
src/krita_agent/upstream/        upstream analysis
plugin/krita_agent_bridge/       in-process plugin and manifest
presets/  resources/  examples/  tests/  scripts/  docs/
```

This is a future layout, not a claim that modules exist. Keep source, plugin, tests, scripts, and curated small examples in Git. Ignore caches, logs, virtual environments, and bulk `output/` artwork; use separate storage or Git LFS if large artwork must be versioned. Do not include Krita installations or the separate upstream clone in this repository.

## 9. Coexistence and safety

Stable and Next installations may share configuration, brushes, and Python plugins despite separate executable directories. Back up user resources, check both versions and deployment compatibility, and do not blindly overwrite shared plugins or alter official installation files. Deploy the project plugin to the appropriate user `pykrita` resource location only after the installation approach is verified.

Bind only to loopback or use operating-system-protected local IPC; never expose the control endpoint to the LAN by default. Allow predefined commands only, validate inputs, restrict file access to authorized locations, and require permission or backups before overwriting important work. Use IDs, timeouts, errors, and duplicate handling to avoid unintended repeated drawing. Dispatch Krita and Qt GUI operations in the proper context. Keep important artwork backed up and test development builds using isolated documents.

## 10. Milestones and acceptance

See [ROADMAP.md](ROADMAP.md) for the current checklist. The intended progression is environment discovery, minimal bridge, layered canvas and basic strokes, pressure comparison, reproducible installation and tests, structured creative workflows, upstream tracking, then optional intelligent iteration. Record the actual build and evidence for every capability; only a real execution test can establish that it works in a particular build.

Initial drawing acceptance creates a 2048 × 2048 document with at least three layers, draws constant, increasing and thin–thick–thin pressure paths with suitable native brushes, independently checks size and opacity mappings, and compares stable and Next results. Inspect width, seams, antialiasing, texture, performance and undo; save PNG and KRA, reopen the latter and verify its layers. Repeat safely without overwriting existing artwork.

## 11. Upstream feature tracker

The [official KDE Invent repository](https://invent.kde.org/graphics/krita) is the primary source; the [GitHub mirror](https://github.com/KDE/krita) is an alternative. Keep a separate reference clone, outside this project's history. A shallow clone reduces the initial download but cannot provide complete history or comparisons with older tags without fetching more history. Updating source does not upgrade an installed Krita build.

Track Python / LibKis classes, signatures, return values and deprecations; brush engines, pressure and sensor inputs; layers, import, saving and export; plugin and Qt compatibility; and relevant reliability, undo, or performance changes. Filter unrelated changes. Use official release notes, development reports, API docs, tests, commits, and merge requests as supporting evidence.

Record the installed stable and Next build identifiers and upstream branch, tag, and commit SHA. Preserve the last successful snapshot; the first check establishes a baseline and later checks compare increments. Do not assume a fixed default branch name. On network failure retain the previous successful baseline and report the failure.

### Proposed tracking workflow

```text
Manual check / explicitly enabled schedule
  → read previous snapshot and local build information
  → fetch upstream and compare commits, source, tests, and API documentation
  → classify changes and link commits / merge requests
  → assess impact and evidence for each target build
  → produce Markdown and machine-readable reports plus candidate tests
  → run approved tests in isolation and update the capability matrix
  → developer reviews any proposed changes
```

Classify additions, signature changes, deprecations, removals, fixes, performance changes, plugin risks, inaccessible functionality, and irrelevant changes. Record affected components, priority and risk. Proposed evidence states: `source_seen`, `documented`, `present_in_build`, `tested_working`, and `not_supported`. Only a successful actual test supports a claim that a feature works in a given build.

Potential submodules include fetcher, diff analyzer, classifier, capability matrix, test suggester, reporter, and an optional scheduler. Candidate commands such as `krita-agent upstream init`, `check`, `diff`, `report`, `probe`, and `test` are proposals only. Each report should include time, baseline and target SHA, branch / tag, source links, files, summary, signature, affected components, target builds, evidence, suggested tests, risk, and status.

Initial acceptance should identify a simulated or real added method and signature or behavior change in a controlled commit range, provide traceable links, distinguish source from runtime availability, and produce safe candidate tests. Manual execution comes first; scheduling must be explicitly enabled. The tracker must not silently upgrade Krita, merge upstream code, execute upstream scripts, overwrite artwork, or modify the agent without review.

## 12. References

- [Krita Python scripting introduction](https://docs.krita.org/en/user_manual/python_scripting/introduction_to_python_scripting.html)
- [Writing a Krita Python plugin](https://docs.krita.org/en/user_manual/python_scripting/krita_python_plugin_howto.html)
- [Installing custom Python plugins](https://docs.krita.org/en/user_manual/python_scripting/install_custom_python_plugin.html)
- [Krita October 2026 development report](https://krita.org/en/posts/2026/monthly-report-2610/)
- [Krita source on KDE Invent](https://invent.kde.org/graphics/krita)
- [Krita GitHub mirror](https://github.com/KDE/krita)
- [Krita Node API reference](https://api.kde.org/legacy/krita/html/classNode.html)
