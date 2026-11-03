# Development report 003 — first implementation round (2026-11-03)

## Scope

Code authored for external Python Controller, authenticated loopback IPC, Krita Extension dispatch, native canvas/layers/brush/shape/stroke operations, continuous StrokePoint adaptation and segmented fallback, safe output path policy, JSON tasks and job state control, install helper, geometry demos, upstream Git diff classification and Markdown/JSON reports, and offline test suites.

## Existing work preserved

Continued the partially implemented doctor, Bridge, client, upstream and test foundation. This round replaces and extends those modules rather than discarding the earlier architecture. A separate local backup of touched pre-existing files can be retained under ignored .cache, not staged in Git.

## Verification status

**NOT RUN by explicit user instruction.** No claim of successful Krita startup, plugin import, actual brush stroke, export, KRA file, automated tests, API signature compatibility or full completion of acceptance. The only intended terminal operation in this round is a local Git commit of authored source. The next step, after user permission, is isolated execution and bug-fixing based on real results.

## Compatibility notes

Krita official Node API describes paintLine, paintPath, paintEllipse, paintPolygon, paintRectangle. The October 2026 Krita Next upstream sources describe Node.paintPolylineStroke and StrokePoint, with Qt5/Qt6 bindings to be checked on installed builds. Source availability is not runtime evidence.

## Security notes

The Bridge binds to 127.0.0.1, requires a random token injected by explicit launch, accepts an allowlist, validates dimensions and paths, and refuses output overwrite by default. Token remains in a session file under user profile; protect that file and do not share it. Krita plugin installation requires an explicit --apply operation with backup and attention to shared Stable/Next resources.

## Later rounds

Actual test/repair, isolated profile integration, brush preset dynamics and automated image comparison, live preview, reference images and local editing, improved idempotency/durable job recovery, deeper source change parsing, opt-in monitoring, and optional agentic planning. None of these later-stage capabilities is represented as verified here.
