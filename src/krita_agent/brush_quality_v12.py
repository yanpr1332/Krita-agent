"""Profile-aware native brush diversity floors for planned scenes.

This evaluates deterministic plan parameters only; it does not judge pixels,
installed brush-engine behavior or finished artwork quality.
"""
from .stroke_quality import analyze_scene

RULES = {
    "quick_sketch": {
        "min_major_strokes": 8, "min_sizes": 2, "min_colors": 2,
        "min_opacities": 1, "min_pressure_span": 0.08,
        "min_direction_bins": 2, "max_repeated_ratio": 0.50,
    },
    "standard": {
        "min_major_strokes": 12, "min_sizes": 2, "min_colors": 2,
        "min_opacities": 2, "min_pressure_span": 0.12,
        "min_direction_bins": 3, "max_repeated_ratio": 0.33,
    },
    "detailed": {
        "min_major_strokes": 20, "min_sizes": 3, "min_colors": 3,
        "min_opacities": 3, "min_pressure_span": 0.20,
        "min_direction_bins": 4, "max_repeated_ratio": 0.25,
    },
}


def describe_floor(profile):
    rule = RULES[profile]
    return (
        "large/complex subjects: at least {min_major_strokes} strokes, "
        "{min_sizes} effective sizes, {min_colors} colors, "
        "{min_opacities} opacity levels, pressure span {min_pressure_span}, "
        "{min_direction_bins} direction bins, and repeated trajectory ratio "
        "no greater than {max_repeated_ratio}"
    ).format(**rule)


def evaluate_brush_plan(scene, profile):
    if profile not in RULES:
        raise ValueError("Unknown brush diversity profile")
    rule = RULES[profile]
    diagnostics = analyze_scene(scene)
    objects = {item["id"]: item for item in scene["objects"]}
    results, issues = [], []
    for row in diagnostics["objects"]:
        obj = objects[row["id"]]
        area = obj["bounds"][2] * obj["bounds"][3]
        major = area >= 50000 or row["stroke_count"] >= rule["min_major_strokes"]
        if not major:
            results.append({
                "subject_id": row["id"], "status": "not_applicable",
                "stroke_count": row["stroke_count"],
            })
            continue
        local = []
        def require(key, actual, expected, comparator="min"):
            failed = actual is None or (
                actual < expected if comparator == "min" else actual > expected
            )
            if failed:
                local.append({
                    "subject_id": row["id"], "requirement": key,
                    "expected": expected, "actual": actual,
                })
        require("min_major_strokes", row["stroke_count"], rule["min_major_strokes"])
        require("distinct_sizes", row["distinct_sizes"], rule["min_sizes"])
        require("distinct_colors", row["distinct_colors"], rule["min_colors"])
        require("distinct_opacities", row["distinct_opacities"], rule["min_opacities"])
        require("pressure_span", row["pressure_span"], rule["min_pressure_span"])
        require("direction_bins", row["direction_bins"], rule["min_direction_bins"])
        repeated_ratio = (
            row["repeated_trajectory_signatures"] / row["stroke_count"]
            if row["stroke_count"] else 1.0
        )
        require("repeated_trajectory_ratio", round(repeated_ratio, 4),
                rule["max_repeated_ratio"], comparator="max")
        issues.extend(local)
        results.append({
            "subject_id": row["id"],
            "status": "fail" if local else "pass",
            "stroke_count": row["stroke_count"],
            "distinct_sizes": row["distinct_sizes"],
            "distinct_colors": row["distinct_colors"],
            "distinct_opacities": row["distinct_opacities"],
            "pressure_span": row["pressure_span"],
            "direction_bins": row["direction_bins"],
            "repeated_trajectory_ratio": round(repeated_ratio, 4),
            "issues": local,
        })
    return {
        "schema": "krita-agent-brush-diversity-floor/1",
        "profile": profile,
        "status": "fail" if issues else "pass",
        "thresholds": dict(rule),
        "subjects": results,
        "issues": issues,
        "not_artwork_acceptance": True,
    }
