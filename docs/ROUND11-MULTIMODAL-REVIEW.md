# Round 11 — Multimodal visual review

Round 11 adds an opt-in multimodal review path without replacing the existing Round 5 critic.

## Safety and evidence

- The final exported PNG is always the first image sent to the model.
- Reference, stage-preview, layer metadata and ROI uploads each require separate explicit consent. Reference uploads also require confirmation of upload rights.
- Image dimensions and source SHA-256 values are recorded. Stage previews must match the final canvas dimensions.
- Metadata is size-limited and sensitive path/credential-like keys are removed before transmission.
- The model sees actual pixels; scene labels and layer metadata are context, not visual proof.
- Critique output is advisory. It never executes Krita commands or independently accepts artwork.
- Revisions continue through the existing non-destructive revision compiler, explicit approval and native execution gate.

## Budget and privacy

Set `KRITA_AGENT_MODEL_API_KEY` in the process environment. Optional endpoint override: `KRITA_AGENT_CHAT_COMPLETIONS_URL` (HTTPS only).

A run locks its review rounds, image count, output-token cap, model-call cap and optional user-supplied token prices. Calls are recorded in an append-only JSONL ledger. Prompt text, image bytes, API keys, local paths and raw provider responses are not logged. If provider usage is unavailable, cost is unknown; a configured cost cap fails closed.

## CLI

Example:

    krita-agent creative critique-v11 --directory ./my-run --model YOUR_VISION_MODEL --confirm-external-review --upload-artwork

Optional evidence requires its corresponding consent flags. Stage previews use `--stage-preview LABEL=FILE --upload-stages`; reference images require `--reference FILE --upload-reference --confirm-reference-rights`; ROI crops require `--upload-rois`. Layer metadata requires `--upload-layer-metadata` and the relevant JSON files. Optional prices are USD per million tokens; configure both input and output rates together before using a total-cost cap.

Do not upload private, confidential, or third-party material unless you have permission. A provisional pass is not acceptance.
