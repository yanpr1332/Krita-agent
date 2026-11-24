# Round 14 development testing policy — consolidated artwork acceptance

> **User-directed development optimization (2026-11-24).** The user asked to perform **one consolidated acceptance after major feature development**, avoiding repeated expensive native Windows multi-build runs and artwork/VLM/human campaigns while source is actively changing. This document governs **R14 development work** and describes the intended handoff to the final cross-round acceptance. It does not change the technical meaning of accepted native artwork.

## 1. What we check now (cheap and essential)

- Compile and strict-import checks for new/modified Python modules.
- GitHub Actions offline pytest on Python 3.10 and 3.13; unit, schema, geometry, backward-compatible API, security and source-hash tests.
- Directly test deterministic transformations and invalid inputs; do not assume a green test proves artistic merit.
- Confirm only explicitly allowed modules/files changed and no real model credentials, private images or native art files entered Git history.
- A source PR may be code-complete and reviewed even if its real Krita API and final-art tasks remain `NOT_RUN`.

## 2. What we defer until integration (expensive and unstable during dev)

- Re-running 3 Windows Krita builds and full PNG/KRA/reopen suites for **every minor coding PR**.
- Generating multi-subject native A/B paintings and calling paid VLMs to score all intermediate prototypes.
- Human rating and redoing the frozen 24-task generalist campaign after each module.
- Large model fine-tuning or large-scale third-party image imports as an unrequested prerequisite.

Defer **testing**, not safeguards: code still must be designed to fail closed on invalid source/unsafe side effects, and must clearly report that T2/T3/T4 have not run. **A real native rendering dependency may still require a narrowly scoped smoke test** if offline tests cannot provide credible confidence; never claim that smoke is full-art acceptance.

## 3. Final consolidated campaign (not softened)

At the end of the planned core development, use the existing [R12 24-task contract](ROUND12-LOCAL-ACCEPTANCE-PROTOCOL.md) and [R13–R20 technical + artwork acceptance plan](ARTIST-ACCEPTANCE-R13-R20.md). Run small/native Krita interface smoke first, then real 3-build interoperability, and then a fixed, source-hash-bound 24-task sample with independent actual-pixel and human review.

We will still preserve technical export integrity, genuine editable KRA/layers/stages, user consent and model upload limits; failed artworks stay in the denominator. If final artwork performance is inadequate, report failure and fix the relevant module rather than repeatedly invoking expensive acceptance loops during unrelated development.

## 4. R14 specific feature boundary

- R14 delivers a **validated proposal and deterministic lowering** to existing ScenePlan v4; it is not R15 region fill or R16 natural-stroke achievement.
- Fast offline tests may verify exactly what Krita Bridge will be asked to do; they **cannot claim** the renderer really painted a complete image.
- The new source/CLI is fully opt-in and is not authorized to invoke any model or modify a user's Krita project.
- No private images or API keys are needed to develop/CI this feature.
- Later R15+ implementations should be developed on separate numbered GitHub branches, with their own lightweight engineering gates. Cross-round policy changes should occur by a separate policy/docs PR, not by silently weakening `AGENTS.md`.
