"""Run inside Krita's Scripter; reports symbol presence, not functional behavior."""
import json
import krita

app = krita.Krita.instance()
report = {
    "krita_version": app.version(),
    "StrokePoint": hasattr(krita, "StrokePoint"),
    "Node.paintPolylineStroke": hasattr(krita.Node, "paintPolylineStroke"),
    "Node.paintLine": hasattr(krita.Node, "paintLine"),
    "View.brushPosition": hasattr(krita.View, "brushPosition"),
    "interpretation": "Symbol presence only; drawing behavior is not tested."
}
print(json.dumps(report, indent=2))
