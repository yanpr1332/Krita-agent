# Development report 001: environment discovery foundation

The first increment adds an experimental `doctor` command that checks an explicitly supplied executable and runs its `--version` command with a timeout, returning JSON. A separate `scripts/probe_krita_api.py` is intended to be run manually in Krita's Scripter; it prints symbol presence only and does not draw or install a plugin. No bridge or automated discovery of running instances is implemented.

Validation: Python 3.14 ran the two standard-library unit tests successfully, covering missing paths, version output, failure, and timeout. On the development machine the stable executable existed, but `--version` timed out after 10 seconds. The Next QT5 and QT6 executable paths were found; neither their versions nor their runtime APIs were verified. The in-Krita script has not yet been run in either build, so its compatibility and actual API availability remain unknown. File and folder names are not evidence of runtime capability.

Next: run the probe in isolated stable and Next environments, capture actual results, investigate Windows GUI executable version reporting, detect plugin status and instances safely, and build a capability matrix. P0-A remains incomplete.

## Subsequent upstream snapshot prototype

A read-only `upstream --repo PATH` prototype reports the local Git checkout's commit, branch, and dirty status without fetching or altering the checkout. It does not yet persist baselines or compute API differences. Its fixture tests pass. The local Krita checkout could not be inspected by the sandboxed process because Git rejected its ownership; no global trust exception was added. The real Bridge, drawing, runtime capability matrix, and end-to-end acceptance remain outstanding.
