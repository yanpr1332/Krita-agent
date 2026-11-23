# Contributing to Krita Agent

Thanks for helping improve Krita Agent. This is a local automation project capable of **modifying editable Krita documents**. Contributions must preserve user control, privacy, reproducibility and the distinction between engineering tests and actual artwork quality.

Read [AGENTS.md](AGENTS.md) for the authoritative development/acceptance rules, [SECURITY.md](SECURITY.md) for vulnerability reporting, and [docs/CLOUD-VALIDATION-STRATEGY.md](docs/CLOUD-VALIDATION-STRATEGY.md) for validation levels. If a proposal conflicts with those rules, discuss the conflict **before** changing behavior.

## Who can contribute, and where changes go

- **Anyone** can fork the public repository, make changes in their own fork, and propose a Pull Request (PR). Forking and submitting a PR do **not** grant write permission to the upstream repository.
- Collaborators with write access may push to permitted topic branches, but changes intended for protected `main` must be reviewed and merged through a PR. Do not attempt direct pushes, force pushes, deletion, or ruleset bypass.
- Start from the latest verified upstream `main` unless a documented dependency requires a different, explicitly reviewed baseline. **Create and verify a new branch before the first edit**, including for cross-round documentation.
- Each numbered development round has its **own new branch**, e.g. `feat/round11-visual-critic`. Cross-round policies or docs use a dedicated `docs/topic` branch; shared infrastructure uses `infra/topic`; bugfixes should be narrowly scoped. Do not append future-round work to a previous round's branch.
- Keep PRs focused. Describe dependencies on other unmerged branches rather than silently including unrelated commits. **Do not auto-merge** or modify `main` without the maintainer's explicit decision.

Suggested branch names: `feat/roundN-topic`, `fix/bridge-timeout`, `docs/contributing-security`, `test/pixel-reopen`, `infra/ci-native-smoke`.

## Good first contributions

Documentation corrections, reproducible Python-only tests, tighter input validation, clear CI failure diagnostics, and small fixes that **do not** change Krita's active document are especially welcome. For native drawing, Bridge permissions, authentication or file-handling changes, please describe the safety model and expected build compatibility in the PR first.

Open an issue or discussion with a small reproducible example for ordinary bugs, proposals and feature requests. **Never post exploitable security details, tokens or private artworks in public issues**; use the [private security reporting instructions](SECURITY.md) instead.

## Development setup

The project is Python >=3.10; core Controller dependencies are intentionally minimal. Use a virtual environment:

```bash
python -m venv .venv
# Activate your virtual environment using the command for your OS.
python -m pip install -e ".[test,feedback]"
python -m compileall -q src plugin scripts tests
python -m pytest -q
```

The tracked workflow [Python CI](.github/workflows/python-ci.yml) runs the offline suite on **Windows / Python 3.10 and 3.13**. If you cannot run both locally, run what you can and provide the Actions links; do not mark unchecked variants as passed. Do not add paid API calls or require a user-installed Krita to pass the offline suite.

Real GUI tests require an explicitly owned/disposable Krita session, temporary output files, and build-specific evidence. The optional [Linux Krita Xvfb workflow](.github/workflows/cloud-krita-smoke.yml) is for **authentic native smoke tests**, not proof of all Windows builds. Avoid triggering expensive native jobs when docs-only/offline checks suffice.

## Invariants that every change must preserve

1. **User control and non-destructive effects.** Model-generated JSON is untrusted. Validate schemas and allowlists before Bridge execution, require existing plan/stage confirmations, preserve user-locked objects and never silently overwrite a personal KRA or PNG. Keep original/failing output versions.
2. **IPC boundaries.** The Bridge must remain local-only (`127.0.0.1`), authenticated and command-allowlisted; do not add arbitrary Python/shell execution, remote listening or unchecked paths. Honor authorized input/output roots and maximum request/plan sizes.
3. **Uncertain outcomes.** A timeout or dropped response may mean a stroke, file save or checkpoint partially executed. **Do not automatically replay a possibly completed native effect.** Preserve evidence and require inspection or explicit new-version recovery.
4. **Explicit network consent.** Core and offline reference analysis must work without a model API. Sending a reference image to an external model requires a separately requested operation and source-specific permission; never put keys or private source pixels in logs or CI artifacts.
5. **Reference and technique provenance.** Use owned, public-domain or specifically permitted/licensed references, with recorded source identifiers and file hashes. User assertions are not an independent legal audit. Techniques extracted from pixel measurements are **hypotheses**, not evidence of recovered human brush strokes, learned model weights or good painting.
6. **Integrity and rollback.** Genuine Krita KRA/PNG comparisons, freshly reopened copies, hashes and independent evidence are required for native/delivery claims. Do not substitute a generated mock image or clipboard-pasted reference for native brush painting.
7. **No test contamination.** Lock fixtures and acceptance criteria before execution. Do not adjust benchmarks to make weak output pass, discard failures, impersonate a human reviewer, or expose personal artwork in publicly uploaded artifacts.
8. **Least privilege in CI.** Prefer `contents: read`, ephemeral tokens, synthetic source images, bounded time/size limits and independent fast gates before costly native runs. Do not run untrusted PR code with write credentials or real personal files.

## What to include in a PR

Use the [PR template](.github/PULL_REQUEST_TEMPLATE.md). At minimum:

- **Purpose and scope:** what changed and why, exact base/head branch, affected commands/APIs, and compatibility/migration concerns.
- **Threat/safety review:** can this touch user files, invoke native effects, change Bridge commands/roots, send images/model prompts over the network, add dependencies or store credentials? Explain mitigations and user confirmation requirements.
- **Evidence:** exact commands and environment, failing and passing test IDs, observed CI links, relevant build/Krita/Qt versions, and sanitized examples. Clearly label anything not run.
- **Limitations:** separate source implementation, offline checks, cloud native test, Windows local native test, independent image-based critique and real human artwork acceptance. **Green CI does not equal good artwork.**
- **Licensing and privacy:** MIT-compatible original contributions; identify any separately licensed resources, fonts, sample art, presets, generated content or third-party code. Never upload private artworks, secrets or unlicensed reference images.

### The three acceptance tiers

| Tier | What is actually tested | Permitted claim |
| --- | --- | --- |
| **T1: cloud/offline** | Unit tests, schema/geometry validation, mock Bridge, failure injection and Windows Python CI | `offline_passed` |
| **T2: real cloud Krita** | Real Krita + actual Bridge/brush operations, editable KRA, genuine stage PNGs, fresh reopen and strict RGBA/profile checks | `cloud_native_verified` **for the exact tested OS/build/commands** |
| **T3: consolidated local artwork** | User-approved installed Windows builds, multi-genre held-out works, authentic editable files and separate independent visual/human review | Report `local_native_verified` and `artwork_human_accepted` **separately** |

The cost-aware project policy is to do substantial source development and regression in cloud tiers, then one **staged** local acceptance campaign after integrated development. This does not waive a narrowly necessary authorized native smoke check. See [artwork acceptance](docs/ARTWORK-ACCEPTANCE.md) for the complete-artwork requirements.

## Review and merge

Maintainers may request focused revisions, security tests, sanitization or a smaller PR. Do not request a review of a known failing safety gate as if it passed. The current ruleset requires PRs, linear history/squash-compatible merging, resolved discussions, and prohibits force pushes/deletion on `main`. **GitHub settings may change:** inspect the actual required-check list instead of assuming all green CI jobs are enforced by the ruleset. A PR is **not** authorization to merge automatically.

## Documentation and language

- `README.md` is the primary English introduction, with `README.zh-CN.md` as the Simplified Chinese counterpart. If features, API names, installation guidance or status changes, update **both** in the same PR.
- Other durable project documentation is written in English; do not rewrite historical acceptance reports merely to adjust wording.
- Respect the repository [MIT license](LICENSE) and the separate licenses of Krita, Qt, dependencies, brush presets and artwork.

Thanks for helping keep a genuinely editable, safe and verifiable painting tool.
