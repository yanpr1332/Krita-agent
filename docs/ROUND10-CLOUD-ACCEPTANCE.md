# Round 10 Cloud Tier-2 evidence — authorized reference to genuine Krita native painting

> **Executed technical acceptance**, November 19, 2026. Source revision `27887d170c8b6454d3cbae6a838042be07a5cff3` on `feat/round10-reference-technique`. This is a single **synthetic, permissibly generated reference** on Linux Krita 5.3.4.1; it is *not* a human-quality or reference-likeness acceptance.

## Verified build and workflow

- [Successful GitHub Actions #44517302418](https://github.com/yanpr1332/Krita-agent/actions/runs/44517302418), Ubuntu/Xvfb with official **Krita 5.3.4.1 (git bd6e8d0)** AppImage. Real isolated authenticated Python Bridge and no contact with the user's workstation.
- The earlier basic native brush and three-stage v4 fixture both passed in the same action, before the new Round 10 fixture.
- Round 10 input was an **original 128×128 CI-generated RGB reference**, stored as a *source* for analysis only. Source rights basis `owned`, explicit permission true, **external upload false**. No paid model or remote visual provider was called.
- The image was SHA-256 bound and its author-declared vessel/water ROIs were measured. A palette/material repaint proposal was separately verified with source hashes; a **hypothesis** water technique profile was extracted from the actual ROI and routed through the independent technique-approval check. A bounded ScenePlan v4 compiled into real original brush strokes. No `image.import`, pasted reference, raster copying or silent native replay.
- Actual native execution: **52** compiled commands, **3** stages, **6** editable subject/phase paint layers (+ background), **6** real Krita stage/milestone PNGs, all **128×128**.
- Stage previews changed **1,563** and **80** RGBA pixels between adjacent phases. Strokes genuinely contributed to the native canvas. The KRA source was independently copied and freshly reopened, the active Krita document identity was checked, and the reopened document exported again.
- Strict KRA embedded/export PNG consistency: **pass, 0 different RGBA pixels**. Strict original/reopened export: **pass, 0 different RGBA pixels**, PNG color metadata consistent.
- The returned reference-to-output comparison contains **two** subject-level ROI reports, color/value/edge differences and actual KRA/Png hashes; it explicitly returns `artwork_accepted:false`.

## SHA-256 evidence independently inspected after CI upload

| Resource | SHA-256 |
| --- | --- |
| Original generated source PNG | `1add7957621610bd3af00fd0cd3098911e3f9871ef6cd6e49e0815233cd0cbd3` |
| Reference analysis | `05b20c65820a64382d09f5afd2cdb7f29a7827d9c4460605f4e1ff1e1c7d2665` |
| `native-reference-study.kra` and independently reopened copy | `131e7405c93ddceef6c96d998d2e0e73d0f9c075488963ae1ef1f80394444a9f` |
| `native-reference-study.png` and fresh reopened export | `abe59c2fdb7c51b678d59e6ffd296a0b5e286cd4d5ce4123b77c56032d775564` |

KRA size **97,805 bytes**; output PNG **4,757 bytes** each; archive ZIP CRC passed, `maindoc.xml`, `mergedimage.png` and native `paintlayer` evidence were inspected. All four actual output-file digests were recalculated independently from the downloaded CI artifact and matched the generated JSON report. All six stage previews were opened and checked for 128×128 size.

- Artifact: [#14526108082](https://github.com/yanpr1332/Krita-agent/actions/runs/44517302418/artifacts/14526108082). It includes genuine KRA, PNG, phase previews, isolated Krita logs and JSON reports. Retention 3 days; this textual report preserves evidence after expiry.
- Offline [Windows Python CI #44517302459](https://github.com/yanpr1332/Krita-agent/actions/runs/44517302459): **285 passing tests each** on 3.10 and 3.13 for the same source revision; no reported test warnings.

## What the output actually proves — and what it does not

The source water region was a **uniform RGB rectangle**. Its edge-orientation extractor correctly returned `indeterminate_no_oriented_edges`, **0 usable samples**, and **0 orientation confidence**; it did **not invent** a brush angle or source technique. This is a good failure-mode behavior, not proof of real brush-trajectory learning. A separate patterned-ROI offline fixture tests the positive directional case.

The measured source-to-native color differences were **large**: absolute mean RGB gaps per channel of **[54.26, 139.58, 163.44]** for the vessel ROI and **[201.83, 151.75, 59.61]** for the water ROI (different source/image/canvas regions, so not direct perceptual similarity scores). The resulting native drawing **does not demonstrate faithful reference reconstruction**. This must not be hidden behind a successful technical status.

**Allowed claim:** on a single Linux Krita build, a rights-recorded source image was actually read and analyzed; a measured palette and a conservatively extracted technique hypothesis were turned into an approved bounded v4 plan; the *real* Bridge painted editable layers and delivered an intact, strictly consistent KRA/PNG with documented source-to-output differences.

**Not established:** faithful complex source resemblance, reliable real brush signature recovery, any general anatomical/composition understanding from source images, real user-owned photo model upload, Windows Stable/Next Qt5/Next Qt6 parity, independent VLM and human aesthetic evaluation. The consolidated local full-artwork campaign remains deferred to R11–R12 integration.

See [Round 10 API](ROUND10-API.md), [Round 10 acceptance](ROUND10-ACCEPTANCE.md), [Cloud Validation Strategy](CLOUD-VALIDATION-STRATEGY.md), and [the six-genre roadmap](ARTIST-ROADMAP-R7-R12.md).
