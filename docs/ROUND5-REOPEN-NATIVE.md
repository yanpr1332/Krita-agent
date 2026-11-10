# Round 5 fresh-reopen native verification

The November 9, 2026 checks used the installed Stable 5.3.4.1, Next Qt5 5.4.0-prealpha and Next Qt6 6.1.0-prealpha builds. The checked source was `447e418` plus the document identity and view-activation fixes in this change. Each run used an isolated Bridge output directory and a 512 × 384 native three-object fixture.

| Build | Export integrity | Fresh reopen | Active original restored | Native stage previews |
| --- | --- | --- | --- | --- |
| Stable | pass | 0 differing pixels | yes | 3 |
| Next Qt5 | pass | 0 differing pixels | yes | 3 |
| Next Qt6 | pass | 0 differing pixels | yes | 3 |

Each reopen comparison checked RGBA and PNG color metadata. The Stable fixture had no embedded PNG ICC profile. The two Next fixtures had matching embedded profiles.

On Next Qt6 the known original KRA/PNG pair was submitted to the same gate. The KRA's embedded composite matched the PNG, but the fresh reopen differed at five pixels by at most one channel level. The gate blocked review and retained the original pair. The previously repaired KRA and original PNG were then registered as an explicitly approved second version. Its fresh reopen passed with zero differing pixels, and the rejected first KRA remained byte-identical. The controlled historical-pair check used a separate test workflow prepared at the archive boundary.

The first run on all three builds exposed a document identity bug. Krita returns separate Python wrappers for the same native document, so object identity did not identify the active document. After comparing underlying document equality, the next run exposed a call to the nonexistent `Window.activateView` API. The Bridge now uses Krita's `Window.showView` and recognizes equal document wrappers. Both failures and the final passing run remain in the local acceptance directory.

This establishes gate behavior for the tested fixtures. The original five-pixel rendering difference remains reproducible and its underlying Krita rendering cause remains unresolved. Real provider and independent human artwork acceptance remain separate.

[Sanitized results](acceptance-evidence/round5-reopen-native.json) · [Local native artifacts](../artwork-results/round5-reopen-native-20261109-175531/)
