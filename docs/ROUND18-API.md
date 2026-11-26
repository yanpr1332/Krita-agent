# Round 18 — local consent-gated line-art catalog and article-image discovery

> **SOURCE IMPLEMENTATION / NO USER ART INGESTED / NO MODEL TRAINING.** This is the first minimal, low-cost implementation of the [line-art data plan](LINEART-DATASET-AND-LEARNING.md). It does **not** download WeChat/other article images, bypass login/cookies/paywalls, upload user images, train model weights, or reproduce original pen trajectory from raster pixels. Real painting acceptance remains deferred under [CONSOLIDATED-ACCEPTANCE-POLICY.md](CONSOLIDATED-ACCEPTANCE-POLICY.md).
>
> Branch `feat/round18-lineart-library` depends on R17 source, which depends on the clean R15/R16 integration to `main`.

## 1. Three independent offline commands

```powershell
# Discover lazy-loaded image URLs in a locally saved HTML file.
# NO download, network connection or browser automation.
krita-agent lineart article-images --html C:/private/article-export.html --output C:/private/article-images.json

# Analyze user-provided, rights-approved local image basenames, and
# produce a non-image, provenance/permission-bound index.
krita-agent lineart analyze --root C:/private/lineart-inputs --manifest C:/private/rights-manifest.json --output C:/private/lineart-index.json

# Retrieve entries by user tags; returns only permitted METADATA.
krita-agent lineart search --index C:/private/lineart-index.json --tag animal --tag cat --purpose local
```

All three commands are **explicitly invoked**. `--output` uses create-exclusive semantics and will not overwrite an existing file. If absent, the returned bounded JSON is printed to the CLI. They never issue `Krita Bridge` commands, even for an approved source. Any user-provided private URLs in an offline HTML export stay on the user's machine and must **not be committed** to GitHub.

## 2. Source manifest schema

```json
{
  "schema": "krita-agent-lineart-request/1",
  "assets": [
    {
      "id": "my_cat_01",
      "file": "cat-01.png",
      "kind": "lineart",
      "creator": "Source artist or creator",
      "source_note": "Where this image came from and what license applies",
      "tags": ["cat", "animal", "thin_contour"],
      "rights": {
        "basis": "owned",
        "can_store_locally": true,
        "can_analyze_locally": true,
        "external_upload_permitted": false,
        "training_permitted": false,
        "can_publish_preview": false
      }
    }
  ]
}
```

**Never claim `basis=owned` or `training_permitted=true` merely because the image was visible on a webpage.** The rights fields describe a user-attested permission basis, not independent legal verification. Allowed rights basis: owned, public domain, licensed, explicit permission. Unknown/absent basis or absent local storage/analysis consent blocks inclusion. Remote upload requires `external_upload_permitted=true` **and** a specific `external_provider` string. Upload permission and model-training permission are different flags. Even `training_permitted=true` does not itself train a model.

Local files must be **single image basenames** located directly inside the explicitly supplied `--root`; PNG/JPEG/WebP only, no symlinks or path traversal. Max 8 MiB per image, 16 megapixels before decode, and 1–100 per request. Root and files must already exist; R18 does not clone, scrape or silently fetch anything. In the index, raw source filenames/paths are deliberately omitted.

## 3. What the image analyzer actually measures

Image reading uses Pillow, original-source SHA256, bounded thumbnail pixels and EXIF-orientation normalization. Current offline descriptors are:

- ink/paper grayscale fractions (numeric line-art heuristics only);
- average horizontal/vertical edge change (coarse density/orientation proxies);
- 64-bit difference hash for rough visual similarity **not identity or copyright**;
- actual pixel dimensions and declared material/style/subject tags.

Exact duplicate SHA groups are reported; source files are never modified or overwritten. A long panel/very large image will be rejected or requires a separately user-approved crop workflow; do not claim this tool segments complex multi-panel art or recovers original pen motion.

**Static image cannot establish real stylus pressure, original pen timing/order, Krita preset or undo sequence.** These fields are explicitly false in R18 metadata. Semantic labeling remains user-provided (tags); color statistics and edge features cannot replace understanding of anatomy, line quality or stage order. R18 is **retrieval/cataloging**, not foundation-model fine-tuning or model-weight learning.

## 4. How saved HTML image discovery works

`lineart article-images` uses Python `HTMLParser` only. It checks `data-src`, `data-original`, `src`, `data-lazy-src` and the first safe `srcset` candidate, deduplicates by URL and records article title, image order, optional declared width/height and alt text.

The extractor rejects `file:`, `javascript:`, embedded credentials, loopback/private IP literals, `.local`/`.internal` hosts and non-standard ports. It limits HTML size and image count; it flags likely tiny QR/logo/avatar decorations **for later review** without discarding potentially valid art. URLs are **discovered**, never fetched. It has no browser cookies, paywall bypass, rate-limit evasion, captcha support or HTTP client. Users should provide an authorized offline export or original files when the website disallows copying or its rights are uncertain.

The output marks **every discovered image as needing rights review**, and cannot directly become a training or publish dataset. A URL by itself proves neither rights nor successful access.

## 5. Search, permissions and integration with existing R10 techniques

`lineart search --purpose local|external_upload|training|publish` filters index entries to the corresponding explicit rights flag before ranking by tag overlap. It returns `id`, `sha256`, matching tags and score, **not original image bytes**. A search with `--purpose training` is a permission-filtering report only; no training or external request is performed.

R10 reference analysis/technique libraries remain the source of actionable **licensed recipes**. R18's tag catalog can help the user find matching material or gesture references, but it does not claim that a discovered WeChat picture is equivalent to validated native brush-technique evidence. Connecting extracted visual curves/authorized images to higher-quality semantic outlines requires separate R18+ geometry work; tracking real pressure would require opt-in Krita action capture or provided tablet recordings later.

## 5A. R18 incremental source feature: raster line-art guides and v4 placement

This same R18 source branch also includes a **bounded offline line-art vector-guide hypothesis**, bridging the metadata catalog to actual editable Krita planning, without pretending that the original artist's pen order, speed or pressure can be recovered.

```powershell
# Optional original ink/sketch source from the same rights-checked manifest.
krita-agent lineart trace --root C:/private/lineart-inputs --manifest C:/private/rights-manifest.json --source-id my_cat_01 --max-paths 12 --output C:/private/cat-guides.json

# Map explicit extracted guide curves onto one PRE-EXISTING v4 subject bbox.
# This only writes a NEW unapproved scene proposal, not a native drawing.
krita-agent lineart bind --scene C:/private/scene-plan-v4.json --guides C:/private/cat-guides.json --subject-id cat --confirm-proposal --output C:/private/scene-with-guides-proposal.json
```

**What happens:** User-authorized local image bytes are decoded as a bounded 256px thumbnail, thresholded, skeletonized with a finite Zhang–Suen pass budget, and walked into 2–128-point normalized polyline candidates (up to 16). Only raster-derived centerline estimates are returned; results are deterministic, SHA-256-bound and contain no original source image bytes. Input must be a specifically identified `lineart` or `sketch` entry with explicit local analysis rights; dark photographs or regions with excessive solid black are rejected rather than hallucinated as “pen drawings”.

`lineart bind` requires `--confirm-proposal`; maps user-chosen guide paths into **one reviewed subject's existing bbox**, then adds bounded `gesture.natural` intents to the *sketch stage of a separate v4 scene*. It does **not** draw, alter the original v4 scene or auto-approve any native stage. The output envelope includes the original scene SHA256, source line-art SHA256, new scene SHA256 and `stage_approval_required=true`; pass its nested `scene_v4` to the usual reviewed `creative plan` workflow if the user accepts it.

**Limitations:** This is morphology-based curve extraction and not true stroke decomposition, anatomy segmentation, accurate contour closure, pressure simulation grounded in physical measurements or full-picture tracing. The current R17 primitive block-in still determines the shaded mass; the added lines are a structure/detail *proposal*. More advanced correspondence, manually reviewed topology and complex shape segmentation remain future work.

## 6. Development tests, limitations and follow-on work

Offline tests create only **synthetic fixture images** and synthetic HTML, verifying strict manifest/rights validation, duplicate SHA, pixel descriptor stability, opt-in CLI, privacy-minded metadata-only search, unsafe URL rejection, absent network/native/model calls, and refusal to overwrite output. Full Windows Python 3.10/3.13 CI remains required.

**T2 cloud Krita / T3 Windows three-build / T4 full-artwork human/visual QA: NOT_RUN/DEFERRED**. No private source files, article HTML, image thumbnails, user credentials, actual line-art samples or model secrets are pushed to GitHub.

Remaining work includes: authorized image download only under a separate explicit rights and network policy; robust long-image/panel separation; perceptual dedup across encodings; line-art vectorization with pixel error; manual review/quality labels; pair alignment; proper reference-to-composition geometry adaptation; eventual actual stroke demonstrations and a separate, permission-specific model training process if justified. None of these are implemented by this PR.
