# Architecture and safety boundaries

All components below are planned and require prototyping and runtime verification.

- **Controller:** Windows Python CLI / SDK for task validation, scheduling, drawing plans, capability routing, and upstream analysis. The CLI framework and dependency versions are undecided.
- **Bridge:** a custom Krita Python Extension in the application process. Use the Krita API and the Qt / Python bindings supplied by the target build. Validate Qt5 first and test Qt6 later.
- **Transport:** controlled local IPC; select the transport after prototyping. Accept predefined commands only, with task IDs, timeouts, and structured errors. Do not execute arbitrary Python or shell input.
- **Drawing:** native brushes, editable layers, and structured stroke samples. Execute Krita GUI operations in the appropriate Qt / GUI context.
- **Upstream tracking:** use the official KDE Git repository as the baseline; retain commit-level evidence and distinguish source visibility, runtime availability, and successful real-world tests. Do not automatically upgrade Krita or execute upstream code.
- **Testing:** Python unit tests, protocol integration tests, and real Krita acceptance tests using isolated documents. Select concrete tools and versions during prototyping.

Restrict file operations to authorized locations and require explicit permission or backups before overwriting artwork. Pause and resume operate at stroke or task-step checkpoints; interrupting a stroke already in progress is not guaranteed. Stable and Next builds may share settings, plugins, and resources, so back up and check compatibility before deployment.
