# Round 10 — authorized reference studies and technique provenance

**Status:** independent development branch `feat/round10-reference-technique`. This adds reproducible, rights-gated reference image analysis, manually mapped reference-to-v4 repaint plans, optional external visual hypotheses, immutable technique profiles, and real-KRA-bound diagnostic comparison. It does **not** train model weights, automatically understand anatomy, or certify that a painting resembles a reference.

## 1. Privacy, rights, provenance

Images are read from a *user-chosen local reference root* with simple basename files only (no traversal/symlink, no network fetching). Every image requires a user-authored manifest with `permission_confirmed:true` and rights basis `owned`, `public_domain`, `licensed` or `explicit_permission`. A recorded basis is a **user declaration**, not legal license verification; confirm the actual permitted use yourself. Max **4 sources**, **8 MiB / 16 MP each**, 12 normalized regions each. Only PNG/JPEG/WebP; the image bytes never become native painting content.

Each source has explicit roles from `composition`, `structure`, `palette`, `material`, `technique`. Ambiguous competing global controllers for composition, structure or palette fail rather than silently mixing references. You can use different sources for composition and color, with per-subject material ROIs, but the final author is responsible for conflicting cues.

Offline analysis does **not** invoke a network API. An external visual model is accessible only with *both* `--allow-external-upload` and `rights.external_upload_permitted:true` for **every** source; the user explicitly configures a model and API credentials. Model-derived subjects, bounding boxes, materials and visual notes are labeled unverified hypotheses with uncalibrated confidence. Source pixels are sent to the configured HTTPS model only in this explicit operation. Do not use third-party assets for external upload if the permission scope excludes it.

## 2. Offline image measurements

`reference_assets_v10.analyze_references(root, manifest)` reads genuine pixels and produces:

- SHA-256 of original file, source IDs and declared license/permission and reuse roles (no private source path emitted).
- Source dimensions, global and manually specified normalized ROI statistics, bounded color histogram palette, RGB mean, five-band luminance fractions and local grayscale edge-density proxy.
- Evidence digest `analysis_sha256`. The output explicitly says `semantic_objects_detected:false` and `stroke_technique_inferred:false`: histograms do **not** prove silhouettes, poses, materials or painterly skill.

A region may have `subject_id` and material so source data can be matched to an already authored v4 subject. These identifiers and ROIs come from the user, not image segmentation.

## 3. Reference-to-native painting proposal

`reference_plan_v10.propose_reference_repaint(scene, analysis, bindings, mode=...)` supports:

| Mode | Behavior | Important boundary |
| --- | --- | --- |
| `palette_repaint` | Explicit subject bindings update v4 subject brush colors using sampled ROI palettes | Does not alter geometries or automatically repaint |
| `material_study` | Also binds sampled colors to already-selected R8 render palettes | Does not guess the `render.technique` from RGB |
| `structure_study` | Requires a separate complete user/model-authored v4 candidate | Pixel statistics cannot infer accurate anatomy |
| `free_adaptation` | Requires separately reviewed complete v4 candidate | No automatic composition migration or raster paste |

Bindings have `subject_id`, `source_id`, optional `region_id`, and a role authorized by that source. Duplicate subject/role bindings and user-locked structures are refused.

The proposal stores original scene/analysis/source hashes, the new fully validated v4 scene, and its actual allowlisted native command digest; it performs **no Krita command**. `approve_reference_repaint(original_scene, manifest, reference_root, proposal, confirm=True)` re-measures the source **at approval time**; changed pixels, permissions, geometry or native command hash fail closed. The returned scene can be supplied to the existing `creative plan --candidate` and later explicitly approved per stage. A reference asset is never imported or pasted by this compiler.

## 4. Reusable technique profiles

`technique_library_v10` supports `validate_technique`, `save_technique`, `list_techniques`, `load_technique`, `propose_technique_application`, and `approve_technique_application`.

Every profile requires `id`, monotonically chosen `version`, `title`, `materials`, `render` (one validated R8 material recipe), `provenance` with source SHA/licensing, `limitations`, optional brush override, allowed subjects/genres, stages, intent kinds and permitted Krita builds. Status is `hypothesis`, `native_tested` or `human_reviewed`; the latter two require recorded evidence, but evidence references themselves are still user-authored and must not be treated as automatically verified. A saved `id--vNNNN.json` cannot be overwritten, and the library does not persist source image bytes.

Applying a technique yields a new hash-bound scene candidate; explicit approval is required and existing artwork remains immutable. Only a compatible material/phase/intent can accept the recipe, and an allowed-build profile cannot be applied to a different build.

**Technique learning is structured knowledge extraction and reuse, not automatic training or fine-tuning.**


### 4.1 Offline technique extraction (additional R10 capability)

`technique_extraction_v10.extract_technique_hypothesis(root, manifest, source_id, region_id, profile_id, material, phase)` reads only a user-authorized ROI and combines its **actual sampled palette, coarse image-edge tangent orientation, edge density and an explicitly HUMAN-DECLARED material name** into a conservative Round 8 `render` recipe. It generates a valid `krita-agent-technique/1` profile with `status:hypothesis`, analysis hash, source SHA, rights note, and explicit limitations. Anisotropy is reported as an *uncalibrated image edge proxy*; this is **not recognition of physical brush strokes, material identity or the original artist's technique**. No network or model training.

The JSON result contains a `profile` object that can be saved immutably, and separate diagnostic fields `image_orientation` and `material_label_source`. Use the CLI flag `--profile-only` to write a library-ready profile:

```powershell
krita-agent reference technique-extract --root ./authorized_refs --manifest refs.json --source-id palette --region-id highlight --id water_ripples_study --version 1 --material water --phase material --profile-only --output water-ripples.json
krita-agent reference technique-save --library ./techniques --profile water-ripples.json
```

A saved hypothesis cannot be promoted to `native_tested` or `human_reviewed` without separately recorded inspection. Its material family is supplied by the user; the derived spacing/angle/color may be unsuitable on another subject, canvas size, Krita brush preset or build. `technique-plan` and `technique-approve` are still required before reusing it on a native painting.

## 5. Actual native comparison

`reference_compare_v10.compare_native_repaint(scene, analysis, bindings, kra, png, fresh_reopened_png)` requires a genuine Krita KRA archive with editable paint-layer metadata and strict matching embedded/exported PNG. If a separate native reopened PNG is supplied, strict RGBA and color-profile consistency are also required. It returns descriptive per-subject color, value, edge and provenance diagnostics.

This does **not** prove the drawing looks like the reference or that all painting came from native brushes (a separate Bridge execution log is essential). Its output preserves `artwork_accepted:false` and `human_review:required`. **Never substitute an image made with Pillow for the native KRA/PNG.**

## 6. CLI workflow (manual, no hidden model call)

```powershell
krita-agent reference analyze --root ./authorized_refs --manifest refs.json --output ref-analysis.json
krita-agent reference propose --scene original-v4.json --analysis ref-analysis.json --bindings bindings.json --mode material_study --output ref-proposal.json
krita-agent reference approve --scene original-v4.json --manifest refs.json --root ./authorized_refs --proposal ref-proposal.json --confirm --output approved-v4.json

# Existing explicit creative workflow (its native painting approvals still apply)
krita-agent creative init --directory ./art-run --brief-file brief.json
krita-agent creative plan --directory ./art-run --candidate approved-v4.json
krita-agent creative approve --directory ./art-run --confirm
krita-agent creative paint-stage --directory ./art-run --session session.json --confirm
# Review and approve every subsequent native stage separately, then export.

krita-agent reference compare --scene approved-v4.json --analysis ref-analysis.json --bindings bindings.json --kra out.kra --png out.png --reopened reopened.png
```

The `reference approve --confirm` gate approves a *future plan*, not direct permission to draw; `creative approve` and `paint-stage --confirm` remain separate native-effect gates. The CLI output file option creates a **new** report, refusing overwrite.

Other commands:

```powershell
krita-agent reference technique-save --library ./techniques --profile technique.json
krita-agent reference technique-list --library ./techniques
krita-agent reference technique-plan --library ./techniques --id water_stripes --version 1 --scene original-v4.json --subject water --intent waterfill --output technique-proposal.json
krita-agent reference technique-approve --library ./techniques --id water_stripes --version 1 --scene original-v4.json --proposal technique-proposal.json --confirm --output technique-approved-v4.json

# Only with explicitly permitted source upload and configured VLM credentials:
krita-agent reference annotate --root ./authorized_refs --manifest refs.json --model YOUR_MODEL --allow-external-upload --output reference-hypotheses.json
```

## 7. Cloud verification and limits

- Tier 1: Windows Python 3.10/3.13 plus mock provider and rights/geometry/immutability tests.
- Tier 2: official Linux Krita 5.3.4.1 under Xvfb should draw a **synthetic** rights-declared image analysis plan as real native strokes, preserve real stage previews, editable KRA, fresh reopened PNG and provenance-bound comparison. It runs *after* the already verified basic/staged native fixtures, using the same disposable Krita process.
- Tier 3: full real Windows Stable / Next Qt5 / Next Qt6, unseen legally sourced reference studies, human review and image-grounded multimodal evaluation are deliberately deferred to the consolidated R9–R12 campaign. A successful native synthetic fixture is a plumbing check, not finished-art acceptance.

See [Round 10 acceptance](ROUND10-ACCEPTANCE.md), [Cloud-tier strategy](CLOUD-VALIDATION-STRATEGY.md), [Round 9 API](ROUND9-API.md) and [Full artwork acceptance](ARTWORK-ACCEPTANCE.md).
