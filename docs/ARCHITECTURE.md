# Architecture and safety boundaries

## Established baseline

The first-round controller, localhost socket Bridge, JSON task transport, Krita native paint operations and Qt GUI-thread dispatch were exercised on Stable 5.3.4.1, Next Qt5 5.4.0-prealpha and Next Qt6 6.1.0-prealpha. See [REPORT-004](REPORT-004.md) for exact scope and preserved limitations.

## Second-round extension architecture (not yet runtime verified)

```text
Windows CLI / SDK
├── client.py + session.py            explicit launch / token / 127.0.0.1
├── protocol.py + workflow.py          allowlisted task compilation
├── stroke_engine.py                  offline curves and sensors
├── feedback.py + task_store.py        local image comparisons / archived plans
└── upstream.py + upstream_semantics.py  source change candidates / evidence
              ↓ authenticated JSON
Krita Python Extension / Qt GUI thread
├── __init__.py                        existing P0 dispatch / job queue
├── advanced.py                        specialized command router
├── advanced_utils.py                  validation and node-ID selection
├── advanced_layers.py                 editable layers and groups
├── advanced_documents.py              documents and selection
├── advanced_media.py                  brush discovery, imports, previews, pixels
├── advanced_transforms.py             transforms and undo/redo
├── job_journal.py                     atomic state snapshots, no auto replay
└── docker.py                          optional Docker, enabled at launch
              ↓
Krita LibKis / native painting and editable KRA
```

## Safety rules

1. All IPC access is loopback and token-authenticated. Only predetermined command names are accepted; no external Python or shell evaluation.
2. Inputs are restricted to `KRITA_AGENT_INPUT_DIR` and outputs to `KRITA_AGENT_OUTPUT_DIR` after resolving filesystem paths, including symlinks.
3. The workflow compiler disallows selected dangerous actions such as deletion, arbitrary code, and silent overwrites. Direct actions require explicit confirmation for destructive changes.
4. Job snapshots contain step metadata and no credentials; written atomically below the authorized output root. Interrupted brush strokes are never automatically replayed.
5. Qt/Krita objects are dispatched on the Krita GUI thread. Native strokes are potentially blocking until completion; cancellation is cooperative between steps.
6. Existing artwork remains protected by opt-in overwrite and no automatic install or configuration replacement. Stable and Next may share plugin resource folders.
7. Git source evidence is not runtime support evidence. CI is manually dispatched only; no checks are automatically run as part of this requested source-only round.

## Compatibility caveat

Only first-round features are verified. Every newly introduced LibKis method, Qt Docker registration, selection method, pixel buffer operation and transform must be tested separately for Stable Qt5, Next Qt5 and Next Qt6 before claiming support. This round deliberately performs no validation.
