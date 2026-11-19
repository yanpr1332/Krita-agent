# Cloud Tier-2 expanded native acceptance — three-stage generalist fixture

> Actual executed evidence, not a proposal. Date: 2026-11-19. Source commit `8220bf4a54f45a84e1d10f60ef76793a102d1757` on `infra/cloud-tiered-acceptance`. This is a synthetic **engineering** fixture only, not a Round 8 material study, independent art review, Windows compatibility test or paid API result.

## 1. Proven real-cloud workflow

- [Successful Actions run #44485164168](https://github.com/yanpr1332/Krita-agent/actions/runs/44485164168), both source gate and real Krita AppImage job succeeded.
- Krita **5.3.4.1 (git bd6e8d0)**, official Linux AppImage in disposable Ubuntu 24.04/Xvfb. Isolated XDG Python Bridge, real GUI, ephemeral authentication, no connection to the user's workstation.
- Real `ScenePlan v4` compiled into **39 native commands**, with two free-form subjects (`vessel` / `water`) and three sequential phases (`sketch` → `block_in` → `detail`). The actual native Krita layer graph contained **six phase/subject paint layers**, plus background.
- **Six genuine Krita stage PNGs**: phase previews for each of the three stages plus `01-layout.png`, `02-color.png` and `03-final.png`. Each was 128×128. Pixel comparisons of successive main stage previews found **1,807** and **79** differing RGBA pixels; each stage genuinely changed the visible result.
- Final native PNG contained **1,635** reddish pixels in the bounded vessel region and **459** blue pixels in the bounded water region (deterministic channel thresholds, not semantic or aesthetic scores).
- Strict **Export Integrity: pass**, different RGBA pixels **0**. Strict **Reopen Stability: pass**, different RGBA pixels **0**, recorded PNG color metadata consistent. Freshly reopened a separately copied KRA, checked that the correct document was active, then exported again.
- The actual synthetic native outputs were downloaded and independently inspected: all four final KRA/PNG hashes match the JSON report, original KRA has native ZIP contents, all six real Krita stage PNGs exist at 128×128, and the original/reopened final PNG hashes match.

## 2. Independent hash evidence

| Artifact | SHA-256 |
| --- | --- |
| `native-staged.kra` | `de2024135f3fb67edfbe78cdf945056a10e7c9c7b60c68d0dd8468e324328de4` |
| `native-staged-copy.kra` | `de2024135f3fb67edfbe78cdf945056a10e7c9c7b60c68d0dd8468e324328de4` |
| `native-staged.png` | `06a4eeecd2870d7619b0349be35a7727ed88d08eedfe0c13698a7fe4f4914a61` |
| `native-staged-reopened.png` | `06a4eeecd2870d7619b0349be35a7727ed88d08eedfe0c13698a7fe4f4914a61` |

Source plan SHA-256: `b62e2639192dcda8e08e398490d131aadeaf3cdbbe52630ad68667b713874b2b`.

Compiled native steps SHA-256: `b5238554e38ca5fca778a6376f6a535d4ece891de25cffb2e5e68701aa69f554`.

Evidence: [Actions artifact #14510142011](https://github.com/yanpr1332/Krita-agent/actions/runs/44485164168/artifacts/14510142011), including the actual editable KRA, original/reopened PNGs, stage PNGs, JSON reports and Krita startup metadata. Its configured retention is **3 days**; the textual evidence remains in this document after expiration.

## 3. Offline CI and budget

- [Windows CI #44485164045](https://github.com/yanpr1332/Krita-agent/actions/runs/44485164045): Python 3.10 and 3.13 each **199 pytest cases passed**; two warnings were exclusively from deprecated Pillow `getdata` used by the new test helper. This helper was changed to `get_flattened_data` where available after that run; later CI must verify the fix.
- The cloud real-Krita job first runs cheap source and simulated-Bridge tests, then uses the **same Krita process** for basic native brushwork and the staged ScenePlan v4 fixture. It caches only the public 5.3.4.1 AppImage binary, never user data, credentials or execution session.
- Native fixture is deliberately tiny; the source keeps all native commands on the existing Bridge allowlist and limits each compiled test to at most 110 commands. Real native effects are never retried on ambiguous failures. The JSON report is preserved even on failure and does not turn simulated results into native acceptance.

## 4. Scope and limits

**Established:** `cloud_native_verified` for a real Linux Krita 5.3.4.1 brush/save/export/fresh-reopen workflow and a separate small generalist three-phase, six-layer native plan.

**Not established:** full Round 8 material rendering (that source lives on a separate feature branch), pressure sensitivity of installed presets, tablet input, Windows Stable/Next Qt5/Next Qt6 parity, the Qt6 five-pixel drift root cause, unknown-subject visual quality, reference repainting or any human/artwork acceptance.

The infrastructure branch remains **separate from `main` and Round 8**. To benefit future rounds, create and verify each new feature branch from an intentionally chosen integrated baseline after reviewing current branch histories; do not silently merge branches or write next-round work to the existing round. Native AppImage CI can only run against the code checked out in a branch that contains its workflow. Keep comprehensive local human acceptance deferred to the single consolidated campaign.

Related: [initial single-stroke acceptance](CLOUD-NATIVE-ACCEPTANCE.md), [cloud strategy](CLOUD-VALIDATION-STRATEGY.md), [AGENTS.md](../AGENTS.md), [R7–R12 roadmap](ARTIST-ROADMAP-R7-R12.md).
