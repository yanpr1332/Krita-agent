"""Safe, read-only static creative workflow dashboard.

Does not control Krita or silently invoke cloud models. Open dashboard.html
locally to review stage history, retained versions and existing previews.
"""
import html
import json
import os
import uuid
from pathlib import Path

from .workflow_metrics_v12 import summarize as summarize_metrics


def _escape(value):
    return html.escape(str(value), quote=True)


def render(workflow, output=None, replace=False):
    record = workflow.read()
    root = workflow.root
    destination = Path(output).expanduser().resolve() if output else root / "dashboard.html"
    if root not in destination.parents or destination.suffix.lower() != ".html":
        raise ValueError("Dashboard must be an HTML file inside the creative run directory")
    if destination.exists() and replace is not True:
        raise FileExistsError("Dashboard exists; use --replace to regenerate it")
    row_html = []
    for item in record.get("history", []):
        row_html.append(
            "<tr><td>{}</td><td>{}</td></tr>".format(
                _escape(item.get("at", "")), _escape(item.get("event", ""))
            )
        )
    thumbs = []
    for path in sorted((root / "stages").glob("*.png")) if (root / "stages").is_dir() else []:
        if path.is_file() and path.parent.resolve() == (root / "stages").resolve():
            thumbs.append('<figure><img loading="lazy" src="stages/{}" alt="{}">'
                          '<figcaption>{}</figcaption></figure>'.format(
                              _escape(path.name), _escape(path.name), _escape(path.name)
                          ))
    latest = record.get("artifacts", {}).get("latest", {})
    if isinstance(latest, dict):
        image = latest.get("png")
        if isinstance(image, str):
            candidate = (root / image).resolve()
            if root in candidate.parents and candidate.is_file():
                thumbs.insert(0,
                    '<figure class="main-image"><img src="{}" alt="Current native artwork">'
                    '<figcaption>Latest native artwork — version {}</figcaption></figure>'.format(
                        _escape(candidate.relative_to(root).as_posix()),
                        _escape(record.get("version", 0))
                    ))
    state = _escape(record.get("status", "unknown"))
    title = _escape(record.get("brief", {}).get("title", "Krita Creative Workflow"))
    metrics = summarize_metrics(root, record)
    profile = metrics.get("planning_profile", {})
    plan_metrics = metrics.get("compiled_plan", {})
    time_budget = profile.get("time_budget_minutes")
    time_budget_label = str(time_budget) + " minutes" if time_budget is not None else "not set"
    brush_quality = plan_metrics.get("brush_quality_v12") or {}
    brush_subject_rows = []
    for item in brush_quality.get("subjects", []):
        brush_subject_rows.append(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td>"
            "<td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                _escape(item.get("subject_id", "")),
                _escape(item.get("status", "")),
                _escape(item.get("stroke_count", 0)),
                _escape(item.get("distinct_sizes", "—")),
                _escape(item.get("distinct_colors", "—")),
                _escape(item.get("distinct_opacities", "—")),
                _escape(item.get("pressure_span", "—")),
                _escape(item.get("direction_bins", "—")),
                _escape(item.get("repeated_trajectory_ratio", "—")),
            )
        )
    brush_issue_rows = []
    for item in brush_quality.get("issues", []):
        brush_issue_rows.append(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                _escape(item.get("subject_id", "")),
                _escape(item.get("requirement", "")),
                _escape(item.get("expected", "")),
                _escape(item.get("actual", "not available")),
            )
        )
    brush_metrics_summary = {
        key: plan_metrics.get(key)
        for key in ("native_steps", "planned_strokes", "brush_configurations",
                    "distinct_sizes", "distinct_colors", "distinct_opacities",
                    "distinct_presets", "pressure_samples", "pressure_min",
                    "pressure_max", "pressure_spread")
        if key in plan_metrics
    }
    metric_rows = []
    for item in metrics.get("operations", []):
        metric_rows.append(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                _escape(item.get("operation", "")), _escape(item.get("count", 0)),
                _escape(item.get("mean_ms", "")), _escape(item.get("p95_ms", "")),
                _escape(item.get("raised", 0)),
            )
        )
    html_page = """<!doctype html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ color-scheme: light dark; font-family: system-ui, sans-serif; }}
body {{ max-width: 1120px; margin: auto; padding: 32px 20px; line-height: 1.55; }}
header {{ border-bottom: 1px solid #9995; padding-bottom: 16px; margin-bottom: 24px; }}
h1 {{ font-size: 2rem; margin-bottom: 8px; }}
.state {{ font-size: 1.25rem; font-weight: 700; }}
.small {{ opacity: .72; }}
.gallery {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px; }}
figure {{ margin: 0; }} img {{ width: 100%; height: auto; border-radius: 6px; }}
figcaption {{ padding-top: 8px; }} .main-image {{ grid-column: 1/-1; }}
table {{ width: 100%; border-collapse: collapse; }} th, td {{ text-align: left; border-bottom: 1px solid #9995; padding: 9px; }}
footer {{ margin-top: 32px; font-size: .9rem; opacity: .7; }}
</style></head><body>
<header><h1>{title}</h1><div class="state">Current stage: {state}</div>
<div class="small">Run: {id} | Version: {version}</div></header>
<h2>Actual native artwork and stage previews</h2><div class="gallery">{images}</div>
<h2>Run profile</h2>
<p>Complexity: {complexity} · Target time: {time_budget} · Native-step ceiling: {step_budget} · Brush diversity: {brush_policy}</p>
<h2>Brush quality gate — planned values only</h2>
<p>Policy: {brush_policy} · Result: {brush_quality_status} · This is a structural plan check, not a visual-quality verdict.</p>
<p>{brush_metrics_summary}</p>
<table><thead><tr><th>Subject</th><th>Gate</th><th>Strokes</th><th>Sizes</th><th>Colors</th><th>Opacity levels</th><th>Pressure span</th><th>Directions</th><th>Repeated ratio</th></tr></thead>
<tbody>{brush_subject_rows}</tbody></table>
<h3>Unmet brush requirements</h3>
<table><thead><tr><th>Subject</th><th>Requirement</th><th>Expected</th><th>Actual</th></tr></thead>
<tbody>{brush_issue_rows}</tbody></table>
<h2>Execution timings</h2>
<p>Telemetry integrity: {metrics_integrity} · Recorded operations: {metric_count} · Raised calls: {metric_failures}</p>
<table><thead><tr><th>Operation</th><th>Count</th><th>Mean ms</th><th>P95 ms</th><th>Raised</th></tr></thead>
<tbody>{metric_rows}</tbody></table>
<h2>Workflow history</h2><table><thead><tr><th>Time (UTC)</th><th>Event</th></tr></thead>
<tbody>{rows}</tbody></table>
<footer>Generated from local run artifacts only. No human or independent VLM acceptance is implied.
Refresh explicitly with --replace; this page does not update itself.</footer></body></html>
""".format(
        title=title, state=state, id=_escape(record.get("id", "")),
        version=_escape(record.get("version", 0)),
        images="".join(thumbs) or "<p>No native artwork/preview has been archived yet.</p>",
        complexity=_escape(profile.get("complexity", "not set")),
        time_budget=_escape(time_budget_label),
        step_budget=_escape(profile.get("max_native_steps", "not set")),
        brush_policy=_escape(profile.get("brush_diversity_policy", "advisory")),
        brush_quality_status=_escape(brush_quality.get("status", "not available")),
        brush_metrics_summary=_escape(json.dumps(brush_metrics_summary, ensure_ascii=False, sort_keys=True)),
        brush_subject_rows="".join(brush_subject_rows) or "<tr><td colspan=\"9\">No compiled brush-quality report yet.</td></tr>",
        brush_issue_rows="".join(brush_issue_rows) or "<tr><td colspan=\"4\">No unmet requirements reported.</td></tr>",
        metrics_integrity=_escape(metrics.get("integrity", "unknown")),
        metric_count=_escape(metrics.get("event_count", 0)),
        metric_failures=_escape(metrics.get("raised_invocations", 0)),
        metric_rows="".join(metric_rows) or "<tr><td colspan=\"5\">No operation timings recorded.</td></tr>",
        rows="".join(row_html),
    )
    temp = destination.with_name(destination.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("x", encoding="utf-8") as stream:
            stream.write(html_page)
            stream.flush()
            os.fsync(stream.fileno())
        if destination.exists() and replace is not True:
            raise FileExistsError("Dashboard already exists")
        os.replace(temp, destination)
    finally:
        temp.unlink(missing_ok=True)
    return {"path": str(destination), "status": record["status"], "read_only": True}
