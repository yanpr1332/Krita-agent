# Consolidated final acceptance — development-phase cost policy

> **User direction, 2026-11-24:** Continue substantial R14+ feature development, avoiding unnecessary repeated real-Krita / visual model / full-artwork test cycles. **Perform one integrated native/visual/human acceptance campaign after the main development work is completed**, instead of requiring a whole-artwork acceptance campaign for every feature PR.
>
> **Important distinction:** This policy **defers expensive acceptance execution**. It does **not** waive code-safety tests, user authorization, real native evidence requirements for claims of verified functionality, or the frozen criteria for the eventual artwork campaign. Feature code can be reviewed and merged while listed as `SOURCE_IMPLEMENTED / FINAL_NATIVE_NOT_RUN`, not as artistically accepted.

## 1. What future coding agents must do on every R14+ development PR

- Create **one fresh, verified GitHub feature branch for each new numbered Round**; do not write directly to `main`, locally or by RDC without user permission. Stack a later Round on an unmerged predecessor branch only with an explicit dependency PR base and merge order; do not misrepresent it as independently merged.
- Produce substantial related source functionality, deterministic unit tests, negative/security test cases, compatibility checks and updated documentation.
- Run the **cheap offline Python 3.10 and 3.13 GitHub CI** checks on the actual PR head; fix any failures. Source compilation, API/geometry, path/authorization/hash and no-unreviewed-native-side-effects guards remain mandatory.
- For code changes that require a Krita API symbol, document the supported symbol and add an offline/native capability preflight; this can be reviewed without performing three Windows Krita builds immediately.
- Avoid repeated paid API calls, huge image generation, repeated finished-artwork trials or native Windows three-build campaigns merely to demonstrate a new module. Never perform an unbounded external upload or model call automatically.
- For each PR, explicitly list the source implementation, current CI evidence and **T2 native / T3 Windows / T4 artwork-human acceptance NOT_RUN** (or the exact observed result if a tiny focused native test was separately approved).
- Keep a truthful known-limitations/remaining-dependencies section. Do not characterize improved compiler shapes, strokes, materials, planned diversity or abstract output as completed professional artwork.

## 2. What is deferred, and when to run it

**Deferred until the main development integration is stable:**

- Three-build real Windows Krita smoke matrix (Stable, Next Qt5, Next Qt6).
- Detailed native brush pressure, multiple-opacity joint pixels and editable KRA export/reopen across all affected renderers.
- Repeated costly multi-genre full-scene native paintings, material A/B blind reviews and paid/authorized VLM evaluations.
- User-provided independent human review and the frozen full 24-task acceptance campaign.

**Exceptions:** If a new feature has a high-risk native side effect that cannot be reasonably reviewed offline, a small *separately authorized* targeted smoke test may be requested and run. It remains a limited native test, never a claim of whole-artwork acceptance. All image/credential/third-party rights controls and process isolation remain in force.

## 3. Final integrated acceptance order

After R14–R19 core implementations are integrated and source CI is green, R20 should:

1. Freeze the integrated source SHA, document models/presets, checked data rights, target Krita versions, test cases and costs.
2. Run a small native protocol/brush/region/control-plane smoke with actual Krita; if it fails, fix root causes **before** expensive paintings.
3. Execute each relevant Windows build's region/brush, multi-layer KRA/PNG and strict fresh-reopen integrity test. Distinguish `supported`, `unsupported`, `blocked` and unverified modes per build.
4. Perform fixed small visual A/B diagnostics only after native smoke passes, then proceed to the full frozen 24-task campaign with actual pixels, original user-authorized reference data and independent human review.
5. Preserve all failed artworks and event ledgers. Declare formal artwork acceptance only when all technical, visual and human rubric gates are genuinely achieved. Missing or incomplete full-artwork evidence is not a pass.
6. If the frozen standards cannot be met, report the actual scope of support and failures, and develop targeted repairs without quietly weakening the criteria.

The existing [R12 local acceptance protocol](ROUND12-LOCAL-ACCEPTANCE-PROTOCOL.md), [R13–R20 acceptance rubric](ARTIST-ACCEPTANCE-R13-R20.md) and [artwork acceptance policy](ARTWORK-ACCEPTANCE.md) remain the reference for final quality. This document updates **schedule and frequency only**.

## 4. Cost-control methods and evidence integrity

- Offline schema/geometry/property tests should be repeatable and deterministic, not model-backed “AI opinions.”
- Use synthetic programmatic fixture PNGs **only in explicitly labeled offline software tests**, never as replacements for actual Krita paint/preview/canvas evidence.
- Don't use formal held-out 24 artwork tasks to optimize prompts or hardcode edge cases before the final campaign.
- No credentials, personal KRA files, user artwork, non-licensed reference images, raw acceptance logs or large artifacts are committed to GitHub. Existing ignored `artwork-results/` and `private-references/` policies remain.
- A downstream round must not assume predecessor code is already merged. State PR dependencies and only claim successful merge after verified actual GitHub state.
- User approval is still needed for actual local machine access, paid models, reference uploads, risky native writes, and PR merge actions as appropriate.

## 5. Status and retrospective

This policy begins with user instruction on 2026-11-24. Round 12 historically executed real native/artwork trials; those results and failure reports remain unchanged. R13 technical work has been merged into `main` (at policy creation); R14 and R15 are source development PRs and do not automatically constitute native or visual acceptance. Future R16–R19 coding agents should use this policy unless the user explicitly changes the workflow.

The policy is meant to reduce repeated user time, API costs and needless native test consumption, **not** to allow unsafe source mutations or false art quality claims.
