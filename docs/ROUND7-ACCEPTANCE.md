# Round 7 acceptance — generalist scenes and staged native execution

> Status: **local technical fixtures exercised on three Krita builds; complete-artwork acceptance failed**. The [local report](ROUND7-LOCAL-ACCEPTANCE.md) records the scope and remaining work.

## What Round 7 delivers

- [x] Versioned `krita-agent-scene/4` with free-form subjects, parent relations, bounded geometry, per-subject materials and editable brush styles.
- [x] Separate sketch, color/form, detail stages and per-stage native command spans. Compilation targets editable Krita layers through existing whitelisted commands; their real rendering still needs native acceptance.
- [x] Deterministic intent expansion (`gesture`, `coverage`, `accents`), with bounded scanlines/stroke counts and existing ScenePlan v3/Bridge safety controls.
- [x] Optional, explicitly configured model JSON planning; all model suggestions must pass independent scene validation.
- [x] CLI plan review and **explicit separate approval before each native stage**. Unknown native effects stop the workflow; no automatic replay.
- [x] Source hashes, compiled step hashes, progress records, native `preview.canvas` stage snapshot **commands** and existing KRA/PNG archival and strict reopening pipeline.
- [x] ScenePlan v3 legacy path retained. Multi-subject scene specimen uses a figure, interior and ceramic still life without special-purpose landscape object kinds.
- [x] Offline regression tests added for normalized plans, determinism, restrictions, source tampering, per-stage approval, lost effect and legacy compatibility.

## Mandatory verification matrix

| Gate | Required action | This GitHub source branch |
| --- | --- | --- |
| Static syntax and all existing unit tests | GitHub Actions Windows Python 3.10 and 3.13 | **PASS:** [GitHub Actions #42771429702](https://github.com/yanpr1332/Krita-agent/actions/runs/42771429702), Python 3.10 and 3.13, 189 passed each |
| New deterministic ScenePlan v4 tests | Validate sample and negative cases | **PASS:** included in the same 189-case Windows CI run |
| Real Krita roundtrip | Stable, Next Qt5 and Next Qt6, whitelisted live bridge | **Passed for nine staged technical fixtures** |
| Intermediate real pixels | For sketch/color/detail, inspect actual Krita stage previews and editable layer contributions | **Recorded for the Qt6 fixtures** |
| Different subjects | Paint **three separate prompts**: landscape, single-object still life, and simple character, without hardcoded benchmark scripts | **Executed as three locally authored structural plans. All failed finished-artwork review** |
| Stop/recovery | Stop after stage 1; inspect live document/graph, restart workflow, continue only after manual approval; unknown effects must remain blocked | **Qt6 owned-process restart and executor-confirmed continuation passed. Independent human approval remains open** |
| KRA integrity | First PNG vs embedded `mergedimage.png`; reopened KRA export vs first PNG, record exact differences/ICC | **Passed for the nine fixtures** |
| Artwork quality | Independent full-image visual review and real human judgement | **Independent visual review failed all three Qt6 candidates. Human judgement pending** |
| Native process cost | Log high-level intent tokens/size, expanded strokes, steps and elapsed time | **Source bytes, expanded strokes, native steps and elapsed time recorded; model token usage not applicable** |

The [full-artwork attempts report](ROUND7-ARTWORK-ATTEMPTS.md) records two later three-subject attempts and their independent visual failures.

The current R7 stage workflow advances forward through approved phases; it does **not** yet offer a native automatic one-stage rewind/repaint or a dedicated v4 semantic anatomy critic. Those remain future development/acceptance work.

Do not turn a source or CI test success into “native accepted”; the high-level intent shapes currently remain simple geometric brush guides. They are not proof of natural human-like mark-making, anatomical correctness, reference copying or reliable multi-genre illustration. Material-aware direction fields, anti-repetition and independent blind art comparisons are prioritized for Round 8 onward.

## Suggested local acceptance workflow (no local action performed by this GitHub change)

1. Read `docs/ROUND7-API.md`. Keep an isolated creative run directory and save the brief.
2. Run `creative init`, `creative plan` with a human-created v4 candidate or the opt-in `--generalist --model` provider, inspect the normalized scene and stage plan, then `creative approve --confirm`.
3. Connect to the intended active Krita build and invoke `creative paint-stage --confirm` **once per stage**. After each stage, inspect the actual PNG preview and layer tree before authorizing the next stage.
4. After final stage, run `creative export` and strict native fresh-reopen checks. Preserve failures and their complete artifacts; repair only as a newly versioned KRA.
5. Supply authentic screenshots, KRA/PNG, logs and independent reviewers, including failed examples. Do not publish raw private run artifacts through the repository.

See also [existing whole-artwork acceptance](ARTWORK-ACCEPTANCE.md), [Round 6 native report](ROUND6-REACCEPTANCE.md), and the [Round 7–12 roadmap](ARTIST-ROADMAP-R7-R12.md).
