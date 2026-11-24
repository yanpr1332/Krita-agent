# Native brush calibration matrix

The \`brushcal\` command creates and manages evidence-backed brush profiles. The Round 12 calibration task now tests three separate behaviors:

1. **Pressure ladder:** four constant-pressure lines at 0.1 / 0.3 / 0.6 / 0.9, allowing visual comparison of line width and opacity.
2. **Pressure ramps:** increasing and decreasing pressure along continuous strokes, checking whether the response is smooth rather than only comparing isolated values.
3. **Size ladder:** three nominal brush sizes, using the selected preset and pressure enabled.

## Generate and run

    krita-agent brushcal generate --preset "Pencil-2" --size 24 --output .cache/brush-calibration/pencil-task.json
    krita-agent job run --file .cache/brush-calibration/pencil-task.json --wait --session <your-session.json>

The calibration workflow opens a new document and exports a PNG to a unique path under \`brush-calibration/\`. It does not automatically register the profile.

## Record after visual inspection

Create a review JSON only after inspecting the native Krita result:

    {
      "preset": "Pencil-2",
      "build": "Krita 5.3.4.1 Qt5",
      "category": "paint",
      "pressure_size": true,
      "pressure_opacity": false,
      "confidence": 0.95
    }

Then record the profile:

    krita-agent brushcal record --data .cache/brush-calibration/review.json --evidence brush-calibration/<exported-image>.png --directory .cache/brush-profiles

The profile is accepted only when the evidence file exists, is non-empty and is at most 5 MB. Its SHA-256 is stored. Listing/choosing rechecks the evidence hash and ignores malformed, tampered, unreviewed, wrong-build or low-confidence profiles.

## Important boundary

The test fixture is a measurement aid, not an automatic claim that pressure size or opacity works. A person must inspect the actual exported native Krita image and set the two capability booleans truthfully. Profiles are build-specific; a different Krita build requires recalibration.
