# Local acceptance artwork (persistent)

This directory is the **mandatory local storage** for actual end-to-end painting acceptance artifacts. Every acceptance run gets its own subdirectory (e.g. \`artwork-results/2026-11-07-sunset-001/\`). Do not replace earlier runs, do not delete work because the test failed, and never store only scripts/logs without the visible artwork.

Each run must include \`artwork.kra\`, \`artwork.png\`, \`krita-screen.png\`, scene plan, actual execution log, final layer graph, three stage PNG previews, VLM evaluation and a human evaluation. See \`docs/ARTWORK-ACCEPTANCE.md\`.

Child run directories are ignored by Git **only to avoid unintentionally committing large or personal files**; the files remain visible locally. After independent approval, an operator can prepare curated public evidence with \`scripts/prepare_artwork_publish.py\`, review it, and selectively commit it. Full KRA can be attached via Git LFS or a GitHub Release asset after consent and file-size checks.
