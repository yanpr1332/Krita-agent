# Round 19 — actual-PNG-bound visual issue triage and safe revision handoff

> **SOURCE IMPLEMENTED / NATIVE & ARTISTIC ACCEPTANCE DEFERRED.** R19 links the existing R11 pixel-grounded reviewer and R5 bounded revision machinery with an offline, deterministic cost-aware triage stage. It uses a **real supplied PNG file** only when explicitly invoked. Development tests use *synthetic* fixture PNGs, not Krita paintings. No model uploads, model API calls, automatic native edits or human acceptance occur.
>
> Source branch `feat/round19-image-feedback-triage`, stacked after R18 → R17 → clean R15/R16 main integration. See [consolidated QA policy](CONSOLIDATED-ACCEPTANCE-POLICY.md).

## 1. Why this is needed

A VLM critique from R11 might identify dozens of defects, each in a different subject or region. Blindly converting all suggestions into an unbounded brush plan is costly and can damage previously correct layers. R19 defines a small deterministic **approval queue** bound to the exact scene source, exact actual exported PNG, and exact critic review record.

This does **not** assert that the model's issue assessment is correct or that its underlying PNG came from Krita. Only subsequent native/human evidence establishes painting quality. A per-region RGB histogram cannot certify recognizable anatomy or artistic coherence.

## 2. Inspect and prioritize real submitted pixels, locally

```powershell
krita-agent art-review triage --scene C:/private/scene-plan-v4.json --png C:/private/artwork.png --review C:/private/review-v11.json --max-tickets 6 --max-area-fraction 0.20 --output C:/private/revision-queue.json

krita-agent art-review verify --scene C:/private/scene-plan-v4.json --png C:/private/artwork.png --review C:/private/review-v11.json --report C:/private/revision-queue.json
```

The source review may come from R11 `krita-agent-multimodal-review/1` (which has independent, explicit model/upload consent) or the older R5 `krita-agent-creative-critique/1`. **R19 itself never calls a model or uploads the PNG.**

The triage operation:

- Validates the **full v4 scene** and actual PNG format, image dimensions, file size and SHA256; rejects symlinked paths and unsafe/broken images.
- Requires the review's `artwork_png_sha256` to exactly match actual local bytes.
- Maps each review object to a known scene subject, including optional `sXX_subject-id` v3 stage-layer identifiers.
- Refuses arbitrary unknown fields, unsupported severity, missing visible observations/correction, off-canvas or out-of-subject ROI and duplicate issue entries.
- Prioritizes `critical → major → minor`, then affected area, within **1–8 tickets** and a configurable **1–50% canvas area** total budget. Excess defects are recorded in `deferred_issues`, never silently discarded or described as solved.
- For each selected ROI, analyzes **real supplied pixels locally** for mean color, brightness variance, alpha coverage and coarse color bucket count. This is quantitative pixel evidence, *not* an inference that the region is artistically complete.
- Returns structured `next_action=request_explicit_localized_native_repaint_plan`, not painting commands, screenshot forgeries or model approvals.

The triage record contains source ScenePlan v4 SHA, raw PNG SHA, review digest, ordered tickets, budget and immutable evidence summaries; no original PNG pixels or model secrets are written to the record. `art-review verify` recomputes all hashes/ROI metrics and rejects changed files/reviews/proposals.

## 3. Native handoff stays non-destructive and explicit

R19 produces a queue only; it does **not** invoke Krita `draw.stroke` or patch existing layers. For any selected ticket:

1. Review the actual PNG and the ROI issue. If the visual critic is wrong, reject the ticket.
2. If needed, use the **existing** R5 reviewed native revision planner to propose brush commands limited to the approved ROI. Do not paste raster references or reuse a model output as arbitrary command input.
3. Separately confirm and execute the R5 new-layer revision only on a supported, authorized Krita session, with its real baseline PNG, graph safety checks, checkpoint, non-overwrite output and no replay after ambiguous effects.
4. Preserve the original KRA/PNG and failed revision evidence. Inspect new native result and repeat review only when budget and user approval permit.
5. Independent human acceptance and the original frozen multi-genre benchmarks remain mandatory at R20; model “provisional pass” is not a user approval.

This isolates **what to fix** from **how to draw** and from **when to approve native effects**. There is no automatic paid VLM loop or feature claim that Krita has already repainted any ticket.

## 4. Source tests, cost limits and known missing work

Offline tests cover strict source PNG/checksums, real crop pixel statistics on explicitly labeled synthetic fixtures, approved-v4 ROI constraints, stage-object ID mapping, critic issue tampering/contradictory pass refusal, stable priority ordering, budget deferrals, output create-exclusive semantics and revalidation of modified reports.

Minimum development gate is Windows Python 3.10 + 3.13 full repository offline CI. **T2 cloud native / T3 actual Windows Krita multi-build source/reopen / T4 independent human/VLM artistic acceptance: NOT_RUN / DEFERRED.**

**Not provided by R19 yet:** automatic semantic repair of anatomy, physically accurate relighting, image editability from a composite PNG, reliable critic judgment without the actual images, cross-layer masked paint fidelity in every Krita build, or an unattended iterative paint loop. This separation intentionally avoids costly unbounded, visually destructive actions before the consolidated final acceptance.
