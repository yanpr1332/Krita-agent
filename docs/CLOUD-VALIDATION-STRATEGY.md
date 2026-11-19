# Krita Agent — cloud-first development and cost-aware three-tier acceptance

> Proposal recorded 2026-11-19. Infrastructure lives on `infra/cloud-tiered-acceptance` branched from verified `main` SHA `5eb948ba10f96771da32ea003261a32292c72a05`. Not merged. Tier-2 real Linux Krita 5.3.4.1 is now verified for a bounded native smoke only; see [execution report](CLOUD-NATIVE-ACCEPTANCE.md).

## Decision

Develop independent Round 9, 10, 11 and 12 feature branches, integrating API contracts and cloud tests continuously. Defer repeated **full local artwork acceptance** until an integrated, deliberately bounded campaign. Fix source/geometry and protocol flaws in the cloud rather than spending local model tokens to rediscover them.

Two key boundaries: (a) source/contract simulation never proves what Krita actually painted; (b) cloud Krita on a Linux virtual display does not reproduce Windows Krita Stable/Next Qt5/Next Qt6.

## Tier matrix

| Tier | Environment | Required hard evidence | Allowed claim |
| --- | --- | --- | --- |
| T1 — offline | Windows 3.10/3.13 GitHub CI, deterministic tests and fake loopback Bridge | Schema and compiler tests, no-remote-command, timeout/ambiguous-effect behavior, SHA-based fixture results, all test statuses | `offline_passed` |
| T2 — cloud native | Disposable Ubuntu runner + Xvfb + **installed Krita + actual Bridge** | Real Krita version/Qt, active Bridge, real paint layer/stroke, editable real KRA, visible non-empty exported PNG, fresh-copy reopened PNG, Export Integrity and Reopen Stability reports; hashed artifacts | `cloud_native_verified` **only for the actual build** |
| T3 — local integrated | User-authorized Windows Krita Stable, Next Qt5, Next Qt6 | Native regressions, KRA reopen, multi-genre held-out images, real stage/layer provenance, independent VLM and human separate verdicts, failures retained | `local_native_verified` and separate `artwork_human_accepted` |

**Important:** A green T1 job cannot upgrade T2 or T3. A genuine T2 run fails when there is no Bridge, when PNG is empty, KRA isn't a valid editable Krita archive, or either strict integrity/reopen metric fails. Reports must preserve exact pixel deltas and metadata; small tolerated differences remain *informational only*.

## Cloud native pilot design

The independent [cloud smoke workflow](../.github/workflows/cloud-krita-smoke.yml) starts via push on its `infra/cloud-tiered-acceptance` experiment branch or explicit manual dispatch; it does **not** make expensive drawing automatic on every feature push. It downloads the official versioned Krita 5.3.4.1 Linux AppImage into an isolated Ubuntu runner and uses Xvfb as a virtual display. Plugin files go to an isolated `XDG_DATA_HOME`, and `kritarc` enables only this plugin; secrets are ephemeral per job, confined to loopback, and never printed.

The probe checks that the actual process can answer `status`, then creates a tiny native canvas, adds an editable paint layer, configures a brush, paints a genuine stroke, exports PNG, saves KRA, freshly reopens a separate copy, re-exports PNG and checks pixels/ICC. Collect a manifest and small non-private smoke artifacts even if the job fails. Fail closed on any unknown native effect. If Xvfb or packaged Krita cannot load our plugin, mark T2 **not established** and document runner logs rather than silently substituting a mock.

This experiment does not validate the Windows-specific `.exe` launcher, user-installed presets, actual tablet pressure, Windows color management or Qt6 five-pixel drift.

## Keeping local cost low

1. **Feature PR gates:** T1 on every commit (syntax, compilation, stub Bridge, deterministic plans, security, integration); T2 only when the native pipeline is proven, with a bounded fixed smoke set and no paid model API.
2. **Deferred full artwork:** Hold back full user-workstation art batches until the combined R9–R12 baseline stabilizes. Each feature round still records source status and pending native/visual tests accurately.
3. **Final acceptance campaign:** First a single short Windows connectivity/native-stroke/KRA-open smoke per targeted Krita build; then a fixed small A/B material set; then held-out multi-genre artwork and reference studies (per the R7–R12 roadmap); finally optional explicitly authorized visual-model evaluation plus separate human review. Abort expensive downstream stages on failed foundations.
4. **Integrity, provenance and privacy:** Retain original failure artifacts, use new versions for repairs, hash every source/painted/reopened file, never replay ambiguous commands, don't push raw private artwork. Cloud artifacts are synthetic tiny canvases only.

## Costs, limits and unknowns

- GitHub-hosted runner minutes, apt package downloads, Xvfb startup and artifact storage incur costs/time; bound the pilot to 15 minutes and avoid large canvases.
- The Ubuntu distro Krita 5.2.2 can connect to the real Bridge but lacks required native painting APIs. The official Krita 5.3.4.1 AppImage is now confirmed to run inside Xvfb once its APPDIR/APPIMAGE and Python environment are correct. [Observed run #44482971863](https://github.com/yanpr1332/Krita-agent/actions/runs/44482971863) passed the bounded native stroke, original PNG, fresh reopened PNG and strict integrity/reopen gates. This does not establish full material or finished-artwork ability; see [verified report](CLOUD-NATIVE-ACCEPTANCE.md).
- Windows build compatibility and aesthetic acceptance always require T3; one Linux build does not generalize.
- Current R8 rendering improvements have offline evidence but native artwork outcomes remain unverified.

## Result ledger (update only from observed runs)

| Gate | Status |
| --- | --- |
| New independent infrastructure branch | Verified |
| T1 Windows 3.10/3.13 regression | **199 passed each** on [run #44485164045](https://github.com/yanpr1332/Krita-agent/actions/runs/44485164045) (latest expanded fixture; Pillow warnings subsequently fixed) |
| T1 fake Bridge and fault injection | Included in 196 passing tests on both Python versions |
| T2 basic native Krita 5.3.4.1 | **Passed**, [run #44482971863](https://github.com/yanpr1332/Krita-agent/actions/runs/44482971863), strict 0-pixel export/reopen differences; [report](CLOUD-NATIVE-ACCEPTANCE.md) |
| T2 three-stage generalist native | **Passed**, [run #44485164168](https://github.com/yanpr1332/Krita-agent/actions/runs/44485164168), 39 native commands, six paint layers, real stage previews, strict 0-pixel export/reopen; [report](CLOUD-STAGED-ACCEPTANCE.md) |
| T3 consolidated local Windows acceptance | Deferred until integration |

See [AGENTS.md](../AGENTS.md), [ROADMAP.md](ROADMAP.md), [ARTIST-ROADMAP-R7-R12.md](ARTIST-ROADMAP-R7-R12.md) and [ARTWORK-ACCEPTANCE.md](ARTWORK-ACCEPTANCE.md).


## Bounded multi-stage Tier-2 extension (cloud CI fixture)

Following the basic native success, the same real Krita AppImage job also attempts a separate **pre-reviewed synthetic ScenePlan v4** fixture: two arbitrary subjects (ceramic vessel and water stripe), three ordered phases (sketch / block-in / detail), and only a small fixed number of validated native commands. Its actual per-stage Krita preview.canvas PNGs, layer inventory, colored pixel changes, editable KRA, fresh reopened PNG, hashes and strict RGBA/ICC comparisons form an independent cloud-staged-report.json. No model API is called; this is not a natural artwork or human approval.

The fixture is source-controlled in scripts/cloud_staged_probe.py and its deterministic compiler/unknown-effect tests are in tests/test_cloud_staged_probe.py. The AppImage binary alone is cached between runs when available; no user artwork, token or session is cached. A success does not establish Round 8 materials, Windows builds or finished-artwork aesthetics. A failed staged test does not undo the earlier verified single-stroke evidence: report each gate separately. **Execution confirmed:** [run #44485164168](https://github.com/yanpr1332/Krita-agent/actions/runs/44485164168) successfully completed this extension; verified hashes and scope in [CLOUD-STAGED-ACCEPTANCE.md](CLOUD-STAGED-ACCEPTANCE.md).
