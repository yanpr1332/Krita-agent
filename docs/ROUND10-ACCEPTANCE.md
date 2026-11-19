# Round 10 — cloud-first source and real Krita acceptance

Development only on `feat/round10-reference-technique` based on verified `main` that already includes R8/R9 and the native cloud pilot. Do not merge `main` or run local workstation/Krita tests without explicit user authorization.

## Tier 1 source / safety

- [ ] Windows Python 3.10 / 3.13 full suite passing at latest R10 source revision.
- [ ] 1–4 authorized sources; reject missing rights, absent file, symlink/traversal, unsupported format, oversized pixels/bytes, ambiguous global roles and malformed regions.
- [ ] Read-only analysis is deterministic, SHA-bound and never invents semantic subject/material detection or pastes raster pixels.
- [ ] Distinguish independent global composition/structure/palette roles from per-subject material contributions. Binding source/ROI/subject mismatches fail closed.
- [ ] External provider called only when the user requests the model, explicitly approves upload *and* each source's consent explicitly permits upload. Model output is validated as untrusted hypotheses and cannot submit native commands.
- [ ] Color-only proposals preserve original geometries, are immutable with source/pixel/hash checks, and re-measure actual sources when approved. Structure adaptation requires a separate human/model-authored candidate.
- [ ] Offline ROI technique extractor is deterministic, retains user-declared material and measured edge/palette proxies, outputs a hypothesis only, and works with native-rendering approval flow.
- [ ] Technique recipes are versioned, immutable, have explicit license/source SHA, confidence/limitation/build context and prevent overwrite; future re-use needs explicit approval and can't silently alter locked material/subject geometry.
- [ ] KRA/PNG comparison rejects Pillow-only fake files, reports strict embedded/export integrity, reopened PNG consistency, descriptive ROI metrics, and leaves artistic verdict pending.
- [ ] Existing R7/R8/R9 geometry/material workflows and stage approvals remain compatible.

## Tier 2 actual native Krita in GitHub Actions

- [ ] Fast protocol/rights tests before expensive Linux AppImage invocation.
- [ ] Read original synthetic test reference using Pillow **only as a source**, create rights manifest and hash-bound analysis.
- [ ] Generate manually preapproved v4 reference palette/material proposal plus a technique hypothesis; compile **only allowed native brush commands**.
- [ ] Under authentic Krita 5.3.4.1 Bridge draw a bounded staged study, save six actual phase previews, and verify meaningful pixel contribution from each phase.
- [ ] Save editable KRA, reopen a separate copy, verify native document identity, strict PNG export/reopen consistency and report provenance/ROI measurements.
- [ ] Archive sanitized JSON, source/plan hashes, real KRA/PNG/projection evidence and runner metadata. This is a CI fixture, not proof of resemblance to a reference.

## Tier 3 deferred final campaign

- [ ] Verify real user-authorized reference study in Windows Krita Stable, Next Qt5, Next Qt6.
- [ ] Held-out licensed references with distinct composition/color/material roles, complex subjects, multi-reference conflict tests and non-pasted native painting evidence.
- [ ] Compare reference/painting subject geometry, human perceptual quality, accurate details and credible material-specific techniques separately from color histograms; independent human review.
- [ ] Preserve failures and all iterations; no benchmark overfit or hidden repaint.
- [ ] Keep this consolidated with Round 11/12 integrated local campaign, except explicitly requested tiny native smoke checks.

**Truth rule:** `source implemented`, `offline tests passed`, `Linux cloud native tested`, `Windows local native tested`, `independent artwork accepted` are distinct levels. No conflation.
