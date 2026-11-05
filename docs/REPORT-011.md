# REPORT-011 — Round 4 acceptance

Local Windows acceptance on 2026-11-05, on `feat/round4-layer-aware-painting` from `e0935910fe8b0b5643be0499cc4230265584ec42` plus the fixes accompanying this report. The local `main` baseline was `f60aef990573ee34b65e49138a3517e362fb9d42`. REPORT-010 records the earlier implementation milestone.

| Installed build | Qt binding | Native trajectory |
| --- | --- | --- |
| Stable 5.3.4.1, bd6e8d0 | PyQt5 | Explicit segmentation, 4,097 samples |
| Next Qt5 5.4.0-prealpha, 2687e5d4 | PyQt5 | Continuous 2,048 samples and explicit segmentation, 4,097 samples |
| Next Qt6 6.1.0-prealpha, 2687e5d4 | PyQt6 | Continuous 2,048 samples and explicit segmentation, 4,097 samples |

Exact Qt and Python versions and native symbols are recorded in the runtime rows. Stable lacks the continuous polyline API. The segmented route requires approval for possible seams and exposes multiple Undo steps. The Next continuous route restored the pre-stroke image in one Undo.

## Results and evidence

- The offline suite passed 82 tests. Source compilation and whitespace checks passed. The installed regression matrix covers 53 legacy commands and eight pixel groups per build. [Offline results](acceptance-evidence/round4-offline.xml)
- The disposable 4096 × 4096 document contains paint layers, nested groups, transparency and filter masks, and a file layer. All three calibrated presets were used. Original native layer payloads and hierarchy were preserved through two individually approved revisions. Full exported RGBA matched both targets, including untouched areas, after KRA reopen. [Stable native results](acceptance-evidence/round4-native-stable.json) · [Next Qt5 native results](acceptance-evidence/round4-native-qt5.json) · [Next Qt6 native results](acceptance-evidence/round4-native-qt6.json)
- Each native run exercised 64 previews at 512 × 512 and 85 pyramid tiles. The pyramid comparison covers PNG hashes, dimensions, RGBA and ICC bytes when embedded. A separate embedded-profile fixture and the 32 MP cap were exercised. The probe also covers high-bit-depth refusal and the wire-size limit. [Pyramid evidence](acceptance-evidence/round4-pyramid-color-budget.json) · [IPC and format guards](acceptance-evidence/round4-final-guards-stable.json)
- Each long run executed 1,200 paint operations through 11 bounded batches and checkpoints. The saved KRA projection was sampled at each of the 1,200 distinct brush footprints, with white separator checks. Timings, throughput and checkpoint storage are single-session observations. Memory and status latency are sampled separately. [Milestone pixel and throughput evidence](acceptance-evidence/round4-milestone-pixels.json) · [Stable metrics](acceptance-evidence/round4-metrics-stable.json) · [Qt5 metrics](acceptance-evidence/round4-metrics-qt5.json) · [Qt6 metrics](acceptance-evidence/round4-metrics-qt6.json)
- Fault injection covered a dropped reply after real native acceptance, disk-full before submission, and a journal failure after submission. Two controlled exits per build were induced after overlay creation and after the first patch. Explicit checkpoint recovery restored the same pixels and kept the original checkpoint bytes. Submission count stayed at one for the dropped-reply case. [Stable recovery](acceptance-evidence/round4-faults-stable.json) · [Qt5 recovery](acceptance-evidence/round4-faults-qt5.json) · [Qt6 recovery](acceptance-evidence/round4-faults-qt6.json)
- The supplemental runs cover stale revisions, native layer bytes, long strokes and Undo, and ScenePlan v2 compilation/submission with eight editable roles. Project manifests were audited against the integrated checkpoint and a deliberate tamper. Feedback handled alpha-only differences with finite, local proposals. [Stable supplement](acceptance-evidence/round4-supplement-stable.json) · [Qt5 supplement](acceptance-evidence/round4-supplement-qt5.json) · [Qt6 supplement](acceptance-evidence/round4-supplement-qt6.json) · [Project provenance](acceptance-evidence/round4-projects-provenance.json) · [Feedback](acceptance-evidence/round4-feedback.json)
- Dock Pause, Resume and Cancel were exercised by actual clicks on all three builds. Recent jobs and diagnostics were inspected, with a complete visible thumbnail recorded on Qt6. The tested scale configurations were Stable default, Next Qt5 1.25 and Next Qt6 1.5. [Stable Dock](acceptance-evidence/round4-dock-stable.json) · [Qt5 Dock](acceptance-evidence/round4-dock-qt5.json) · [Qt6 Dock](acceptance-evidence/round4-dock-qt6.json)
- The live shared plugin directory was backed up before deployment. The installer replacement and rollback were exercised in a disposable resource directory. KRA, PNG and credentials stayed in local test roots. Remote GitHub Actions was outside this local run. [Installer evidence](acceptance-evidence/round4-install-rollback.json) · [Capability matrix](acceptance-evidence/round4-capability-matrix.json) · [CLI smoke](acceptance-evidence/round4-cli.json)

## Integrated run measurements

| Build | 1,200 strokes, seconds | Strokes/sec | KRA checkpoints, MiB | Mean status, ms | Working set / process peak, MiB | Fixture storage, MiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| stable | 74.60 | 16.08 | 4.96 | 44.28 | 1111 / 1255 | 16.59 |
| qt5 | 78.80 | 15.23 | 5.06 | 45.30 | 1094 / 1242 | 17.68 |
| qt6 | 78.96 | 15.20 | 5.06 | 46.47 | 1192 / 1340 | 18.00 |

The memory and status samples were taken after recovery. Checkpoint and fixture storage are measured separately.

## Defects found and repaired

- Native overlay insertion now checks the correct end of Krita's bottom-to-top child list. A pre-existing output path or oversized job is refused before creating an overlay. [Output collision evidence](acceptance-evidence/round4-overwrite-preflight.json)
- Selection clear removes the global selection. The earlier scheduler run reached completed while an empty active selection suppressed painting. Those results were replaced with KRA pixel evidence.
- Root-level file and paint imports choose a root child as insertion anchor when the selected node is nested.
- Completed scheduler batches record digest, elapsed time and step count. Atomic ledger updates tolerate short Windows sharing violations, and an ambiguous accepted submission is recorded for review.
- Structural rebinding refuses ambiguous keys. Capability promotion and calibrated brush selection are bound to reviewed evidence and its digest.
- Native job metrics are dispatched before the generic legacy job handler. The pyramid test now derives the expected count from the geometry and verifies edge tiles.

## Reproducing the native checks

Run the scripts from the repository root with Pillow available. Start one owned Krita test session with the Bridge on port 47721, using disposable input and output directories. The runners read local session metadata from `.cache/round2/current.json` with the build alias, process ID, output directory and IPC token. Keep that file local. Run the main script first, followed by the supplement, controlled fault and metrics scripts. The fault script terminates and restarts the process from that metadata, so the PID must belong to the test session. Use the final-guard and IPC scripts against an isolated fixture.
