# Cloud native Krita acceptance — first successful Tier-2 smoke

> **Executed evidence; limited to one Linux build.** Date 2026-11-19. Infrastructure branch `infra/cloud-tiered-acceptance`, source commit `2a2b111e8595d0bde576665d69cbba1018167558`. This is not a Round 8 material benchmark, Windows compatibility result, or independent artwork acceptance.

## 1. Proven result

- **Successful GitHub Actions run:** [#44482971863](https://github.com/yanpr1332/Krita-agent/actions/runs/44482971863), native job success, preceding source-protocol gate success.
- **Official Krita build:** Linux 5.3.4.1 (git bd6e8d0), extracted official KDE AppImage, inside disposable Ubuntu 24.04 GitHub Actions runner with Xvfb, an isolated XDG Krita plugin directory and authentic authenticated localhost Python Bridge.
- **Real native commands:** `canvas.create`, `layer.create`, `brush.configure`, `draw.stroke` (segmented, four control points), `document.info`, `layer.list`, `document.save`, `document.export`, `document.open` (fresh independent KRA copy), `document.info`, `document.export`.
- **Painted pixels:** 1,941 pixels with the specified native red brushwork on a 128×128 RGBA U8 canvas. Genuine Krita layers `Background` and `Cloud CI Ink` are present, with paint-layer evidence retained in the KRA ZIP.
- **Output sizes independently inspected:** original KRA 39,300 bytes; first PNG and reopened PNG each 2,494 bytes. Both are valid files. KRA ZIP CRC checks passed and contains `maindoc.xml` plus `mergedimage.png`; real PNG contains 137 distinct RGBA colors.
- **Export Integrity:** `pass`, 0 differing RGBA pixels, 0 RGB differences, 0 alpha differences, max channel difference 0.
- **Reopen Stability:** `pass`, 0 differing RGBA pixels, 0 RGB differences, 0 alpha differences, max channel difference 0, original/reopened PNG color metadata consistent. KRA reports sRGB-elle-V2-srgbtrc.icc; neither exported PNG embeds an ICC profile. This consistency result is *not* a guarantee for other ICC configurations.

| File | SHA-256 |
| --- | --- |
| `native-smoke.kra` | `30f98e9dd853fa01f88fadeb4d6b7c82bf018bdbca5d403639ffbd1830acfc3a` |
| `native-smoke.png` | `f060bf7be471556ce5ac8a874595d77f32d4d8d33831e35666ae6950c42d1fe4` |
| `native-smoke-reopened.png` | `f060bf7be471556ce5ac8a874595d77f32d4d8d33831e35666ae6950c42d1fe4` |

Real, synthetic test artifacts, runtime logs and the SHA-bound JSON proof were uploaded to [GitHub Actions artifact #14509516380](https://github.com/yanpr1332/Krita-agent/actions/runs/44482971863/artifacts/14509516380) (configured retention: 3 days). The files and report were also downloaded for independent verification: ZIP metadata, hashes, KRA contents and original/reopened PNG size and pixel data were checked outside the CI job. The artifact may expire; this report preserves the values and run link.

**Allowed new claim:** `cloud_native_verified` for the described Linux Krita 5.3.4.1 segmented-brush/save/export/fresh-open/reexport workflow. A green GitHub CI check alone was not relied upon.

## 2. Why earlier pilots failed and what was learned

| Run | Build | Observed outcome | Remedy/status |
| --- | --- | --- | --- |
| [#44478492130](https://github.com/yanpr1332/Krita-agent/actions/runs/44478492130) | Ubuntu Krita 5.2.2 | Bridge not available; embedded Python could not import PyQt5 when GitHub setup-python's library paths interfered | Start the Krita process with isolated loader and Python paths |
| [#44479260869](https://github.com/yanpr1332/Krita-agent/actions/runs/44479260869) | Ubuntu Krita 5.2.2 | Real Bridge connected, canvas and layer created; `View.setDisablePressure` absent | Do not request an unavailable pressure toggle in the minimal smoke |
| [#44481186381](https://github.com/yanpr1332/Krita-agent/actions/runs/44481186381) | Ubuntu Krita 5.2.2 | Embedded Python search path was missing, no Bridge | Isolated wrapper restored system PyQt5 paths |
| [#44481618910](https://github.com/yanpr1332/Krita-agent/actions/runs/44481618910) | Ubuntu Krita 5.2.2 | Real Bridge and brush configuration worked, but `Node.paintLine` did not exist | **Known unsupported native drawing API**; do not claim Tier 2 on this build |
| [#44479965422](https://github.com/yanpr1332/Krita-agent/actions/runs/44479965422) | Intended 5.3.4.1 AppImage | Hosted apt update stalled until job timeout, before Krita download | Reuse preinstalled Xvfb/Xauth and skip unnecessary apt update |
| [#44482325317](https://github.com/yanpr1332/Krita-agent/actions/runs/44482325317) | Official Krita 5.3.4.1 AppImage | Krita started, but embedded Python could not locate `encodings` | Pass `APPDIR` and `APPIMAGE` to extracted `AppRun` |
| **[#44482971863](https://github.com/yanpr1332/Krita-agent/actions/runs/44482971863)** | **Official Krita 5.3.4.1 AppImage** | **Genuine Bridge stroke, KRA and PNG output and strict fresh-reopen consistency all passed** | **Tier 2 established, scoped to this build and fixture** |

The failed pilots were preserved as separate workflow histories, never relabeled as successful. The final successful pilot uses a fresh isolated cloud canvas and a synthetic brush stroke; it does not access the user's workstation, private image files, or paid model APIs.

## 3. Cloud test architecture

- The economical [Windows Python CI](../.github/workflows/python-ci.yml) runs on every `main`, `feat/**` and `infra/**` push. Source revision `2a2b111e` passed **196 pytest cases each** on Windows Python 3.10 and 3.13 in [run #44482971886](https://github.com/yanpr1332/Krita-agent/actions/runs/44482971886).
- The [native AppImage workflow](../.github/workflows/cloud-krita-smoke.yml) currently triggers on changes to the infrastructure experiment and select related code paths; it has a fast offline protocol gate, then a bounded real Krita runner; a future migration into the default branch needs explicit branch/PR integration and is not automatic.
- [Real native probe](../scripts/cloud_native_probe.py) fails closed on unknown responses, retains a report even on failure, validates KRA/PNG hashes, paint pixels and strict export + reopen differences.
- [Mock Bridge tests](../tests/test_cloud_contract_bridge.py) remain **Tier 1 only** (token refusal, response ID, lost mutation response, frame bounds and non-false native acceptance).
- The [5.2.2 distro fallback workflow](../.github/workflows/cloud-krita-distro-smoke.yml) remains a diagnostic/compatibility branch fixture, not a substitute for 5.3.4.1.

## 4. Not proven; future steps

1. This proves a **single basic segmented stroke and archive/reopen** using real Krita; it does not verify continuously varying pressure, all installed preset families, broad multi-material native painting, mask behavior or Round 8's complete art workflow.
2. **Not tested on the user's Windows builds**: Windows Stable, Next Qt5 and Next Qt6 retain their own explicit local/native acceptance requirements. The old Qt6 rare five-pixel reopening defect is not resolved by a Linux success.
3. Neither a visually natural illustration nor reference-based repainting was generated or judged. **Artistic/semantic/human acceptance remains pending.**
4. To extend Tier 2 during R9–R12: add small predefined native fixture jobs (for paint-layer metadata, material variation, masks, pressure, palette and stage snapshots), always cap commands/canvas/time and preserve strict versioned artifacts; only run full-artwork tests after integrated cloud development. Avoid default frequent downloads until costs are measured.
5. Bring this dedicated `infra/*` branch into a feature branch via an explicitly reviewed PR or equivalent approved integration. **Do not merge to `main` without authorization.**

See [cloud validation strategy](CLOUD-VALIDATION-STRATEGY.md), [AGENTS.md](../AGENTS.md), [Roadmap](ROADMAP.md), and [full-artwork acceptance rules](ARTWORK-ACCEPTANCE.md).
