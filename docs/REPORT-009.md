# Round 3 acceptance — 2026-11-03

## Result and evidence scope

Round 3 was tested on the three installed Windows Krita builds. The original source-completion report REPORT-008 remains historical; this report records executed acceptance and repairs. The checklist is tracked in ROUND3-ACCEPTANCE.md. Tests use disposable documents and repository-local output roots, never user artwork.

Tested base: `2a900627a1087cdba22ddd523d6f744e6868e8ad`, branch `feat/round3-reliable-creative-automation`; local main was `f60aef990573ee34b65e49138a3517e362fb9d42`. Acceptance fixes are included in this commit and identified by source hashes in the artifact manifest.

| Build | Qt / Python | Native | Crash phases | Old commands / pixels | Final supplements |
| --- | --- | --- | --- | --- | --- |
| 5.3.4.1 (git bd6e8d0) | PyQt5 5.15.7 / 3.13.5 | 13/13 | 3/3 | 53/53 + 8/8 | 3/3 |
| 5.4.0-prealpha (git 2687e5d) | PyQt5 5.15.7 / 3.13.5 | 13/13 | 3/3 | 53/53 + 8/8 | 3/3 |
| 6.1.0-prealpha (git 2687e5d) | PyQt6 6.11.0 / 3.13.5 | 13/13 | 3/3 | 53/53 + 8/8 | 3/3 |

## Repairs found by acceptance

- Internal checkpoint, recovered-copy, pixel-history and clipboard directories now resolve against the authorized output root. Windows junction escapes are refused before writes. Metadata reads and decompression are bounded, pixel journal payload hashes and saved-document rectangle limits are verified before restoration.
- Checkpoint suffix boundaries must actually follow a checkpoint step; stopped-job state, complete task fingerprint and forbidden suffix checks remain enforced.
- Selection masks now receive the current nonempty selection at creation. Selection algebra/modification operates on a detached duplicate after waiting for native work, fixing an observed Next Qt5 GUI stall during repeated combination operations.
- Revision application rejects malformed identities/rectangles before contacting Krita. A no-change plan returns without mutation. Live projection, unique source layer, source visibility/opacity/blend, reference hash and confirmation gates remain active.
- Dock content is scrollable while Pause/Resume/Cancel remain outside the scrolling content. Preview height is bounded so history/errors/previews remain reachable in constrained layouts.
- Native undo/redo drains already-posted Qt events around the operation, fixing intermittent pixel regression. Ten consecutive Stable undo/redo pixel roundtrips passed before the complete build matrix.
- Atomic metadata replacement retries transient Windows sharing locks up to eight attempts, with a maximum 350 ms added delay; permanent failures still raise. This fixes an observed WinError 5 during a 399-step resumed job. Only the file replacement is retried, never the drawing step.
- The scene example now names the installed resource `b) Basic-5 Size`, verified by live resource enumeration.

## Executed suites

- Offline: 57 tests passed, including all original 34. Syntax compilation and `git diff --check` passed. The host anyio pytest plug-in emits one deprecation warning; it does not change results.
- Native Round 3: 13 assertion groups per build, including transaction fill/clear/patch, exact undo/redo, integrity rejection, checkpoint ZIP/SHA/copy restore, masks/filters and KRA reopening, eleven selection operations, RGBA U16/GRAYA/F32 inspection/conversion, brush metadata, approved revision and safety denials, malicious archives and junctions, real filter configuration pixels, and partial-revision failure recovery.
- Existing-function regression: 53 Round 2 command/protection records and eight pixel groups per build. Scene compilation is deterministic; actual scene and first-round pressure jobs completed, produced nonempty pixels and valid KRA/PNG, and retained layer order on reopening.
- CLI: eight smoke checks passed for help, checkpoint list/inspect, scene compilation, revision planning, missing-confirmation refusal, upstream catalog and registry listing (round3-cli.json).
- Restart: real owned processes were terminated and restarted. Saved jobs became interrupted with no document opening or automatic replay. Explicit recovery used a new verified KRA copy; checkpoint bytes stayed unchanged. Suffix jobs completed from the recorded boundary. File-backed clips loaded across the restart and pasted the expected pixels. Independent pixel transactions also undid/redid the saved pixels after reopening the same KRA in a new process.
- Controlled crash phases: before checkpoint save, after the durable KRA/manifest but before journal progress, and after ten completed native segmented-stroke calls. A temporary instrumented copy of the plugin gates at these locations; production code has no gates. Each phase checks interrupted status and zero automatic replay. Where a checkpoint exists, restored RGBA matches the checkpoint merged image and explicit suffix completion preserves the original KRA. The pre-save phase correctly has no recoverable checkpoint. Test-owned listeners disappear on process exit. The temporary plugin is removed by reinstalling repository source in `finally`.
- Final supplements: filter insertion native undo/redo is compared pixel-for-pixel, selection-mask retention is checked in a reopened KRA, and final storage/recovery-directory protections are retested.
- IPC: wrong token and arbitrary exec are rejected, duplicate authenticated request IDs create one layer, the listener belongs to the recorded test PID and binds only 127.0.0.1, and non-loopback interface connections are refused.
- Dock: actual computer-use UI clicks on Pause/Resume/Cancel in all three builds, with independent Bridge progress/status checks. Eight recent jobs, a deliberate missing-layer error and a preview are inspected; scrolling makes content reachable while controls remain available. UI observations and scale settings are recorded separately from API results.

## Pixel and failure evidence

Selection replace/add/subtract/intersect/xor yield expected coverage; feather has partial alpha, grow/shrink change coverage in the expected direction, border clears the interior, invert covers the canvas complement, smooth retains nonempty coverage. Transparency masks affect exported alpha and survive KRA roundtrip. Local selection masks store selections; they are not described as automatically changing image opacity.

Invert filter masks/layers turn the red fixture cyan, toggling visibility restores original pixels, and changing desaturation configuration changes the reference pixel to white. Native undo/redo and reopened KRA preserve the tested result. RGBA U16 conversion retains the tested primary reference pixel within a four-level tolerance; unsupported raw byte writes are refused after depth/model conversion.

Approved revisions match the target RGBA both inside and outside the intended rectangle; the source layer remains as a hidden editable original, and the resulting KRA reopens with matching pixels. Deliberate failures after duplicate, patch and hide are recorded as failed jobs; explicit checkpoint restoration returns the baseline pixels without changing the checkpoint file. Rejected cases include changed target bytes, stale projection, extra visible layers, non-normal blend, oversized/malformed ROI, wrong dimensions, missing confirmation and concurrent jobs. No-change plans do not contact the Bridge or alter layers.

Compressed clipboard bombs, trailing/truncated streams, schema/digest changes and forged pixel payloads/rectangles are refused. Prepared pixel records are reconciled against actual before/after digests without writing pixels. These integrity checks do not claim cryptographic authentication of all metadata against a same-user attacker who rewrites every field.

## Upstream provenance

Controlled local Python AST and C++ header fixtures detect add/remove/signature changes with scoped paths and source URL shapes. Synthetic SHAs are fixture commits, not published KDE commits; no upstream source executes. All candidates remain source_seen. The manual capability registry records 42 real build/symbol entries: only reviewed, applicable passing native evidence is marked tested_working. Absent symbols remain not_supported and mere presence remains present_in_build. Missing confirmation and duplicate registration are rejected; injected atomic-storage failure preserves the previous registry. Existing failed-fetch baseline tests passed without a network fetch.

## Test operation and limits

The installer dry run was reviewed; every deployment used timestamped backups of the shared pykrita directory. A distinct executable and random-token output root were used one build at a time. Shared resources were backed up rather than claiming a fully isolated user profile. Generated PNG/KRA/clip payloads and private session tokens stay under ignored .cache paths; only sanitized JSON/XML and hashes are committed. No CI run, push or merge was triggered.

The old Round 2 command script initially selected a prior test document by index when run after recovery; orchestration was corrected to run it first in an empty session. A long 2,000-point segmented stroke also exceeded the ordinary query timeout in the crash fixture; the deterministic mid-stroke gate uses 64 points and an explicit 60-second query timeout. Neither harness failure is counted as a passing feature test. A standalone storage fixture initially lacked its recovered directory and was corrected before passing. The CLI synthetic Git check was run under the account that created the fixture after Git correctly refused cross-account ownership; no global safe.directory exception was added.

No claim is made for arbitrary future builds, ICC colorimetric accuracy, every brush's pressure response, general semantic image generation, multilayer reference patching, or native Krita undo for independent raw pixel transactions. A long native stroke remains non-interruptible until its checkpoint; crash recovery starts from a saved KRA copy, never abandoned in-memory artwork.

## Reproduction

The acceptance scripts require an explicitly launched disposable Bridge. The private session JSON contains pid/token/out/build and is not committed. The native scripts use test port 47721; controlled crash tests use 47731, launch their own processes, and restore the production plugin in finally. `prepare_round3_crash_fixture.py` builds only an ignored temporary plugin copy. Never point these scripts at a user's working document/session. Evidence filenames start with round3- under acceptance-evidence; artifact hashes identify the local generated files without adding artwork to Git.
