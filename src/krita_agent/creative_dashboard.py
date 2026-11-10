"""Safe, read-only static creative workflow dashboard.

Does not control Krita or silently invoke cloud models. Open dashboard.html
locally to review stage history, retained versions and existing previews.
"""
import html
import os
import uuid
from pathlib import Path


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
<h2>Workflow history</h2><table><thead><tr><th>Time (UTC)</th><th>Event</th></tr></thead>
<tbody>{rows}</tbody></table>
<footer>Generated from local run artifacts only. No human or independent VLM acceptance is implied.
Refresh explicitly with --replace; this page does not update itself.</footer></body></html>
""".format(
        title=title, state=state, id=_escape(record.get("id", "")),
        version=_escape(record.get("version", 0)),
        images="".join(thumbs) or "<p>No native artwork/preview has been archived yet.</p>",
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
