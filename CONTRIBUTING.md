# Contributing to Krita Agent

Krita Agent has verified Round 1/2 core capabilities and **installed-build Round 3 acceptance**. This is not a planning-only repository. For active status see [ROADMAP](docs/ROADMAP.md) and [REPORT-009](docs/REPORT-009.md).

Develop in a named topic branch from current main and open a PR for review. Do not merge a feature that only has authored source if the PR claims runtime compatibility. Include actual support matrix and limit statements after verification.

## Language policy

`README.md` is the default English introduction; `README.zh-CN.md` is the corresponding Simplified Chinese guide. Both must be updated in the same change when status, install instructions or API names change. Other durable documentation is English except previously archived validation reports, which are historical artifacts.

## Safety and quality

- Keep the IPC limited to localhost, authenticated, and allowlisted. Do not add code execution, shell forwarding, remote listener binding, or file operations outside authorized roots.
- Preserve the user's existing artwork: never silently overwrite KRA/PNG; copy and back up shared user plugin resources before changing installations.
- Avoid automatic replay after a crash. An interrupted native brush command may have partially applied; verified KRA state is the recovery boundary.
- Raw RGBA U8 pixel edits are not native undo steps. Any independent transaction store must verify before/after bytes and deny unsafe replay.
- `source_seen` is a candidate, not a proven runtime capability; `tested_working` requires an actual passing build-specific test and reviewer-confirmed provenance.
- Tests in `tests/` are offline; real GUI integration scripts use disposable work and only test-owned process PIDs. Record exact build/Qt/Python versions and sanitized evidence; never commit tokens, client artwork or generated caches.
- Do not turn on automatic CI triggers during an implementation-only task when the user explicitly prohibits validation.
- Respect MIT license for original project code and separate licensing of Krita/Qt/third-party dependencies.
