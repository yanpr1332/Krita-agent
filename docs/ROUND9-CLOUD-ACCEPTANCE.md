# Round 9 real cloud Krita evidence — structural sketch native run

**Status:** cloud native technical acceptance **passed** for **one bounded synthetic fixture** on Linux Krita 5.3.4.1. This does not validate real human/animal appearance, Round 8's full material repertoire, Windows Stable/Next Qt5/Next Qt6 or user artwork.

- Branch: `feat/round9-multigenre-structure`, observed code commit `5a43ed5fbb7ed297fd82d83776cf3d52585fba8c`.
- [GitHub Actions #44494279816](https://github.com/yanpr1332/Krita-agent/actions/runs/44494279816): fast protocol gate **success**, real Krita AppImage + Xvfb job **success**.
- [Actual artifact #14512924624](https://github.com/yanpr1332/Krita-agent/actions/runs/44494279816/artifacts/14512924624): downloaded and independently inspected in a separate analysis sandbox, including live KRA/PNG ZIP/hash and real stage preview files. Artifact retention: 3 days.
- Validated structural plan had two semantic subjects (ceramic vessel and water stripe), two generic part boxes, two rendered construction chains, a `left_of` relationship, two generated subject strategies and zero structural-warning issues.
- Actual Krita Bridge executed **41** allowlisted commands. Three visible stages, six native editable phase/subject paint layers (+ background) and six stage/milestone PNGs.
- Stage preview change counts: 1,807 then 79 different RGBA pixels; colored material pixels in expected subjects: vessel red 1,635; water blue 459. These are deterministic visibility metrics, **not** assessments of brush naturalness or semantic correctness.
- Saved real editable KRA **96,146 bytes**. PNG sizes 4,507 bytes each.
- Strict `export_integrity.status=pass` (0 different RGBA pixels); `reopen_stability.status=pass` (0 different RGBA pixels, PNG profile metadata consistent). Original/freshly reopened exported PNG hashes identical.

## SHA-256 provenance

| Artifact | SHA-256 |
| --- | --- |
| normalized v4 ScenePlan | `8310b11e2242b229fc7672f61952231855b163ff83346f81e8df3d4af9c94c3c` |
| compiled native steps | `a8a0384e7c139eaab5a67da3cee2d0ab54ee2ca41d205c92720e4c0d10b1bf86` |
| `native-staged.kra` and fresh independent KRA copy | `4ac3eee5000a9b7fa8af0231bdf88c3342a2fd3a04beff835319737eb0339f27` |
| `native-staged.png` and `native-staged-reopened.png` | `9ff2bae2dce80ced058ab4c68e35c6a5863836d70251b43d72784a7f1ee69200` |
| native stage 1 preview PNG | `8b8022fadac249632406408a5fe388071bd0e3480e90c29f9829e4298013d94f` |
| native stage 2 preview PNG | `8889252cd399683c0c04d2660b10eb9df3727893072092ee1f7f72d087ac8e84` |
| native stage 3 preview PNG | `05dd41335f6a447cc5504614ab0530ee235f232a2e4b0230b597c5244d380900` |

All source/protocol and native experiments were run in GitHub-hosted cloud machines. No work was performed in the user's Windows/WSL environment, no RDC connection and no paid model calls.

**Tier 3 remains deferred:** unseen six-genre artworks, local Windows three-build compatibility, subjective visual quality and independent human approval. See [Round 9 acceptance](ROUND9-ACCEPTANCE.md), [API](ROUND9-API.md) and [cloud acceptance strategy](CLOUD-VALIDATION-STRATEGY.md).
