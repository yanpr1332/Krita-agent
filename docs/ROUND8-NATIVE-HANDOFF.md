# Round 8 native acceptance handoff — for the local Krita agent

> This is an **instruction for a later authorized local test**, not a record that the tests have run. Source revision: `a366a41f` (Round 8 initial implementation; later documentation-only commits may follow). Do not invent any screenshots, visual passes, KRA files or human reviewers.

## 1. Preparation

- Read `AGENTS.md`, `docs/ARTWORK-ACCEPTANCE.md`, `docs/ROUND8-API.md`, and the preserved R7 reports `ROUND7-LOCAL-ACCEPTANCE.md` / `ROUND7-ARTWORK-ATTEMPTS.md`.
- Use isolated new `artwork-results/round8-<run-id>/` directories. Never remove or overwrite R7 failed candidates, their full PNGs, original KRA files or review records.
- Confirm the installed Krita build and actual calibrated brush presets in Stable, Next Qt5 and Next Qt6. Some preset/pressure combinations may not look as described by the named technique.
- Use an isolated test canvas/project. Stop if the intended document cannot be uniquely identified. No unrelated Krita process termination.
- Create fixed subject briefs for landscape, still life and simple character; pre-register them and record which were used to tune algorithms vs held-out tests. Never modify the benchmark after reviewing output.

## 2. Controlled material A/B checks

- For each subject, preserve **one same composition/phase/brush-profile contract** and compare R7 legacy `coverage` with Round 8 `render` enabled, recording the actual differences in plan source/hash and technique parameters. Do not claim causal brush improvement from differently authored scenes alone.
- Inspect actual native RGB/alpha output at 100% zoom, especially stroke endpoint scalloping and blank slivers at filled shape edges. If the Round 8 brush footprint crosses its declared ROI, report it (centerline validation alone is insufficient).
- Test at least: cloud/sky, lake reflections, rock/facets, foliage, ceramic, fabric/hair/skin. One material on two different subjects is valuable transfer evidence.
- Switch among `staggered` and `blue_noise` placement on a fixed geometry to see whether the new sampling reduces visible repetition without opening accidental holes.
- Vary `light_angle`, `light_strength`, palette and `layers` on one area while holding the rest fixed. The renderer chooses palettes by geometry; it does **not** implement physically based lighting.

## 3. One end-to-end staged run

For the supplied technical example (do not mistake this for a complete artwork benchmark):

```powershell
krita-agent creative init --directory artwork-results/round8-smoke --brief-file brief.json
krita-agent creative plan --directory artwork-results/round8-smoke --candidate examples/round8-material-study.json
krita-agent creative approve --directory artwork-results/round8-smoke --confirm

# Run exactly one stage, inspect its actual Krita native preview and layers,
# and obtain a fresh, separate human/operator approval before the next:
krita-agent creative paint-stage --directory artwork-results/round8-smoke --session session.json --confirm
krita-agent creative paint-stage --directory artwork-results/round8-smoke --session session.json --confirm
krita-agent creative paint-stage --directory artwork-results/round8-smoke --session session.json --confirm
krita-agent creative export --directory artwork-results/round8-smoke --session session.json
krita-agent creative diagnose --directory artwork-results/round8-smoke
```

The above only illustrates the CLI; the local agent must provide an actual approved `brief.json`, matching canvas dimensions and a valid separate `session.json`. Before every stage, inspect the correct active document and hash-bound plan. If a previous run was interrupted or native effects are uncertain, **do not replay** and do not run the command until the lost effect is investigated.

`creative diagnose` is read-only. It reports geometric repetition and verified real Krita PNG changes by stage and subject ROI. A small change fraction is a review hint, **not automatic failure**, and an overlapping subject ROI does not prove which layer contributed the pixels.

## 4. Required evidence and verdict

For each test capture actual editable KRA, initial PNG, reopened PNG, strict export/reopen RGBA+ICC comparison, native screenshots, stage previews, source/compiled hashes, layer ablation/contributions, installed brush/preset identities, time and action ledger. Record both successful and failed cases; do not upload raw private `artwork-results` to GitHub.

Independent visual review must inspect the real images (not labels, metadata or a synthesized reference). Request a real human decision separately, reporting material naturalness, silhouette completeness, gaps, repetition and integration. Do not label an agent-authored executor approval as independent human artwork review.

Publish only a concise sanitized report and evidence indices to the existing Round 8 feature branch, preserving all earlier failures. If a particular build fails native behavior, mark that build unverified or failed, even if other builds pass. If a KRA reopen differs by a few pixels, strict Reopen Stability fails and the original evidence stays retained.

**Do not write `native accepted` or `artwork accepted` until these gates are actually exercised.**
