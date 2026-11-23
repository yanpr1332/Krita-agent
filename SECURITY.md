# Security Policy

Krita Agent connects a Python Controller to a Krita Python extension with the ability to create and modify **real editable documents**. This is a local automation component, not a hardened multi-user remote painting service. Please treat vulnerabilities that could modify files, bypass approvals, expose images or gain command execution as security-sensitive.

## Supported scope

Security fixes are considered for the **current maintained `main`** and, when relevant, current development branches. The repository's development version and historical Krita/Qt builds are **not** a promise of security maintenance or backports for every earlier commit, archived build, third-party plugin or unmerged feature branch.

When reporting a problem, include the exact Krita version/build (Stable/Next, Qt/Python), plugin/Controller commit, OS and relevant enabled options. There is no published response-time or fix-time SLA.

## Privately report a vulnerability

1. **Preferred:** On [the repository Security page](https://github.com/yanpr1332/Krita-agent/security), use **Report a vulnerability** / **Private vulnerability reporting** *if GitHub offers that control*. We have not verified that private vulnerability reporting is enabled; do not assume that this button exists.
2. **If unavailable:** Contact the repository maintainer through an **existing private channel** and request a secure reporting route. If there is no private channel, ask for one **without sharing the exploit or affected files publicly**; the maintainer should enable GitHub private vulnerability reporting or arrange another private method. Public issues and PRs are **not** a substitute for private disclosure.
3. In a private report, provide a concise impact summary; affected commit/build; safe minimal steps to reproduce using **synthetic, non-sensitive** inputs; expected versus actual behavior; relevant logs with secrets removed; and whether an actual user file or machine was affected. Use a private, agreed-upon route for any sensitive proof-of-concept files.

Please allow time for triage and a coordinated fix before publishing exploit details. Do not run tests against anyone else's device, expose credentials, collect third-party artwork, or access data without authorization. Maintainers should acknowledge and triage reports privately, preserve reporter credit where appropriate, and coordinate disclosure after a fix is available; no response deadline is guaranteed.

### Security-sensitive examples

Report privately if you discover any of the following:

- Bridge command execution without a valid token, unintended access from outside loopback, unsafe command dispatch, or leakage of authentication tokens.
- Path traversal, symlink/race-based escape, unauthorized KRA/PNG overwrite/deletion or read access outside an approved input/output root.
- Model prompts, image metadata or downloaded content overriding the validated plan and issuing arbitrary native commands or bypassing user approvals.
- Silent re-execution after ambiguous Krita effects, corruption of saved art/checkpoints, or falsified KRA/PNG/acceptance evidence.
- External upload of reference images, prompts, local file paths or credentials without the user's deliberate authorization, or exfiltration through logs/CI artifacts.
- Unsafe installation/update behavior, dependency or workflow supply-chain compromise, or privilege escalation.

Ordinary non-sensitive UI bugs, feature requests, documentation errors and artistic-quality issues belong in public issues/PRs, with sanitized examples only.

## Current security boundaries (code-backed, not a guarantee)

### Local authenticated Bridge

- The Controller client only permits `127.0.0.1`; the Krita Bridge binds to `127.0.0.1` and requires a token via `KRITA_AGENT_TOKEN`. The Bridge checks tokens with `secrets.compare_digest` and rejects unknown commands; requests and responses are bounded to **1 MiB**.
- The Bridge refuses a startup token shorter than **20 characters**. For real use choose a **fresh, unpredictable token of at least 32 random bytes**, rather than relying on the minimum length. Keep it in the process environment or another private secret store, never in repository files, screenshots, issue posts or logs.
- The default port is **47653**, configurable by `KRITA_AGENT_PORT`. **Do not expose, tunnel or proxy it to a public network**. Loopback itself is not a defense against a malicious process running as the same local user; restrict access to the workstation/session and keep dependencies up to date.
- Treat the existing allowlist and input validation as mandatory. Adding a new Bridge command requires tests of input types, upper bounds, authorized paths, authentication, idempotency and uncertain-effect recovery. Do not add arbitrary Python evaluation, shell forwarding or remote binding.

### Filesystem and real-art protection

- Krita native output is constrained by `KRITA_AGENT_OUTPUT_DIR` (default under the user's `Pictures/KritaAgent`); reference input uses an explicitly selected directory. Keep generated paths under authorized roots and refuse traversal/symlinks. The Bridge's own `document.open` and save/export behavior must be reviewed carefully before changing file handling.
- Preserve original, copied and failed KRA/PNG/checkpoint versions; never silently overwrite personal artwork. Do not retry a possibly completed draw/save/open/export after a transport timeout, even if a client claims failure.
- Only actual Krita-generated editable KRA with independent reopen and strict PNG/ICC integrity can establish a **native** test. Never present a Pillow rendering, pasted reference, simulated Bridge response, or invented human review as a native or artwork pass.
- Actual local artwork acceptance outputs are intentionally excluded from Git by [`artwork-results/.gitignore`](artwork-results/.gitignore). That is an accidental-commit safeguard, **not encryption or access control**. Manually audit any staged/uploaded files and delete leaked secrets via a proper credential-rotation and history-remediation process.

### Reference images and optional model providers

- Reference analysis is **offline by default**. Every source requires a declared, permitted use and recorded provenance/file SHA; these assertions do not automatically verify copyright or redistribution rights.
- Remote vision/image annotation requires an explicit user operation **and** source-level `external_upload_permitted: true` for each image. A license to view an image does not automatically authorize cloud upload. Avoid sending identifiable/private images without clear permission and user awareness.
- Optional model access uses an HTTPS JSON provider configured by the user; an API key may be supplied through `KRITA_AGENT_MODEL_API_KEY`. Do not write keys into commands, source, examples, traces, screenshots or PRs. External providers may have separate storage/retention policies; verify those terms before enabling an upload.
- Treat external model responses, image annotations, reference manifests and imported technique profiles as **untrusted inputs**. They are bounded hypotheses and cannot authorize new executable code, remote endpoints or native effects without the validated ScenePlan and explicit user/stage approvals.

### Plugins, CI and contributors

- Never run integration tests on a user's current artwork without their permission. Use a disposable test document/profile and terminate **only processes started by that test**.
- GitHub Actions should use least-privilege token permissions, synthetic/publicly shareable fixtures, bounded native workloads and fail-closed approval gates; do not make credentials or a user's local desktop available to untrusted PR builds. Do not put personal art, production KRA, secret env files or unauthorized reference images into artifacts.
- Keep dependencies and Krita builds updated and test actual version-specific behavior. Passing Windows offline CI does **not** prove Linux/Windows native compatibility, nor does successful cloud native rendering prove aesthetic quality or the absence of vulnerabilities.
- The project-authored code is MIT-licensed. Krita/Qt, third-party binaries, model services, assets, presets and references have separate security and license obligations.

## If you suspect a compromise

Stop the affected Krita automation session, disconnect any unintended proxy/tunnel, preserve a **sanitized** timeline and affected file hashes, and do not automatically replay pending native steps. Rotate potentially exposed Bridge/API tokens and revoke affected provider credentials. Restore from a trusted, independently checked KRA copy; avoid overwriting evidence. Report the incident privately using the process above.

See [CONTRIBUTING.md](CONTRIBUTING.md), [AGENTS.md](AGENTS.md), [docs/CLOUD-VALIDATION-STRATEGY.md](docs/CLOUD-VALIDATION-STRATEGY.md) and [docs/ARTWORK-ACCEPTANCE.md](docs/ARTWORK-ACCEPTANCE.md).
