# Round 4 command guide

See [REPORT-011](REPORT-011.md) for the local acceptance evidence and build-specific limits.
First install/enable the local Krita Bridge explicitly in a disposable test profile and launch with authorized input/output directories.

## Graph capture and layered overlay

    krita-agent graph capture --output ".\plans\graph.json"
    krita-agent graph diff --before ".\plans\graph-old.json" --after ".\plans\graph-new.json"
    krita-agent graph rebind --before ".\plans\graph-old.json" --after ".\plans\graph-new.json"

    krita-agent overlay plan --before "D:\drawings\inputs\before.png" --target "D:\drawings\inputs\goal.png" --graph ".\plans\graph.json" --output ".\plans\overlay.json" --tile-size 512
    krita-agent overlay apply --plan ".\plans\overlay.json" --confirm

The GOAL PNG must be inside the Bridge's authorized input directory; source and goal SHA256, graph fingerprint and every changed tile are checked. Only changed regions with fully opaque goal pixels are supported. Original layer nodes are not replaced.

## Serial long jobs and checkpoints

    krita-agent longjob plan --file ".\examples\round4-longjob.json" --batch-size 120
    krita-agent longjob run --file ".\examples\round4-longjob.json" --ledger-dir ".\logs"
    krita-agent longjob inspect --file ".\logs\long-job-LEDGERID.json"

Each batch submits via existing authenticated v1 IPC and ends in an actual KRA checkpoint. Uncertain replies halt execution; never rerun blindly.

## Brush calibration and ScenePlan v2

    krita-agent brushcal generate --preset "b) Basic-5 Size" --size 24 --output ".\plans\brush-calibration.json"
    krita-agent brushcal record --data ".\plans\calibration-reviewed.json" --evidence ".\evidence\brush-output.png" --directory ".\profiles"
    krita-agent brushcal choose --directory ".\profiles" --build "Next Qt5" --category ink

    krita-agent scene-v2 compile --file ".\examples\round4-scene-v2.json" --output ".\plans\scene.json"
    krita-agent scene-v2 submit --file ".\examples\round4-scene-v2.json" --ledger-dir ".\logs"

Only a real inspected output should be recorded as a calibrated brush. Scene-v2 is deterministic JSON; no free-text commands or model invocation.

## Offline large-canvas preview pyramid and long strokes

    krita-agent pyramid build --image ".\images\full.png" --output-dir ".\preview-tiles" --tile-size 512
    krita-agent pyramid inspect --manifest ".\preview-tiles\manifest.json"

ScenePlan v2 optionally accepts a long_stroke element with allow_seams=true and
segment_points <=2048, which emits separate native strokes (possible texture
seams and multiple Undo operations). Without allow_seams it refuses.

ScenePlan v2 can choose a manually reviewed brush by category when invoked with
--profiles-directory and --build. Build-specific evidence must match the actual
preset; missing profiles are refused.

## Feedback, projects and metrics

    krita-agent feedback-v2 review --current ".\current.png" --goal ".\goal.png" --graph ".\plans\graph.json" --round 0 --max-rounds 3 --output ".\plans\review.json"

    krita-agent project init --directory ".\projects\landscape" --title "Landscape"
    krita-agent project add --directory ".\projects\landscape" --file ".\projects\landscape\art.kra" --kind kra
    krita-agent project audit --directory ".\projects\landscape"

    krita-agent performance job --id JOB_ID
    krita-agent invoke runtime.limits --params "{}"

All feedback review results require explicit approval before any edit. Status/provenance objects are local; no account data or image is uploaded.

## Versions and installation

The project development version is 0.5.0.dev0. The new typed protocol v2 classes are SDK objects; Bridge network protocol is still v1. Optional Pillow: pip install -e ".[feedback]". Tests are NOT executed by adding the manual CI workflow.
