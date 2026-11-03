# Roadmap and acceptance

All items remain to be developed; ordering may change as experiments provide evidence.

- [ ] **P0-A — Environment discovery:** report the actual stable and Next build versions, plugin environment, and available APIs; establish a capability matrix.
- [ ] **P0-B — Minimal bridge:** exchange simple commands and success / failure results between CLI and plugin without freezing the GUI.
- [ ] **P0-C — Basic drawing:** create a canvas, layers, and basic strokes; save and reopen a layered KRA document.
- [ ] **P0-D — Pressure:** validate continuous pressure input and brush response separately; compare Next and a stable-build fallback, including undo behavior.
- [ ] **P0-E — Delivery:** provide installation, logging, tests, and a reproducible basic task.
- [ ] **P1 — Drawing workflow:** structured drawing tasks, brush settings, reference images, checkpoints, pause and resume.
- [ ] **P1-U — Upstream tracking:** incremental Git changes, traceable reports, and a capability matrix distinguishing source presence from runtime behavior.
- [ ] **P2 — Intelligent iteration:** optional natural-language planning, visual feedback, and local revisions.
- [ ] **P2-U — Enhanced tracking:** generate candidate compatibility tests and run them in isolation; scheduled checks are opt-in.

## First real drawing acceptance

Create a 2048 × 2048 canvas with at least three layers. Select native brushes configured to respond to pressure and draw constant-pressure, increasing-pressure, and thin–thick–thin curves. Test pressure-to-size and pressure-to-opacity separately. Record the actual stable and Next builds and compare line width, seams, antialiasing, texture, performance, and undo behavior. Save PNG and KRA, reopen the KRA to verify layers, and repeat the task to check that user artwork is not overwritten and uncontrolled files are not left behind.
