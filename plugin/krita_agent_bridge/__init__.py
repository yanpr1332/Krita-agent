"""Krita-native, authenticated local IPC bridge. Import only within Krita."""
import json
import logging
import os
import queue
import secrets
import socket
import sys
import threading
import uuid
from collections import deque
from pathlib import Path

import krita as krita_module
from krita import Extension, InfoObject, Krita, ManagedColor

try:
    from PyQt5.QtCore import QPointF, QRectF, QTimer, QT_VERSION_STR
    from PyQt5.QtGui import QColor, QPainterPath
    QT_BINDING = "PyQt5"
except ImportError:
    from PyQt6.QtCore import QPointF, QRectF, QTimer, QT_VERSION_STR
    from PyQt6.QtGui import QColor, QPainterPath
    QT_BINDING = "PyQt6"

MAX_FRAME = 1024 * 1024
MAX_STEPS = 400
MAX_POINTS = 2048
COMMANDS = frozenset((
    "status", "capabilities", "canvas.create", "document.info", "document.open",
    "layer.create", "layer.select", "layer.list", "brush.configure",
    "draw.line", "draw.stroke", "draw.shape",
    "document.save", "document.export",
    "job.submit", "job.status", "job.list", "job.pause", "job.resume", "job.cancel"
))
TASK_STEPS = COMMANDS.difference((
    "status", "capabilities", "document.open", "job.submit", "job.status",
    "job.list", "job.pause", "job.resume", "job.cancel"
))


def _number(value, name, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(name + " must be numeric")
    value = float(value)
    import math
    if not math.isfinite(value) or (low is not None and value < low) or (high is not None and value > high):
        raise ValueError(name + " out of range")
    return value


def _int(value, name, low=None, high=None):
    if type(value) is not int or (low is not None and value < low) or (high is not None and value > high):
        raise ValueError(name + " must be an integer in range")
    return value


def _name(value, label="name", length=120):
    if not isinstance(value, str) or not value.strip() or len(value) > length or any(
            x in value for x in ("\n", "\r", "\x00")):
        raise ValueError(label + " must be a short single-line string")
    return value.strip()


def _point(value):
    if not isinstance(value, dict):
        raise ValueError("point must be an object")
    return QPointF(_number(value.get("x"), "x", -65536, 65536),
                   _number(value.get("y"), "y", -65536, 65536))


def _points(raw):
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_POINTS:
        raise ValueError("points must be a list of 1 to 2048 samples")
    return [_point(value) for value in raw]


class KritaAgentBridge(Extension):
    def __init__(self, parent):
        super().__init__(parent)
        self.server = None
        self.queue = queue.Queue(maxsize=128)
        self.command_timer = None
        self.job_timer = None
        self.token = None
        self.output_dir = None
        self.jobs = {}
        self.active = deque()
        self.recent = {}
        self.in_flight = set()
        self.guard = threading.Lock()
        self.log = logging.getLogger("krita_agent_bridge")

    def setup(self):
        token = os.environ.get("KRITA_AGENT_TOKEN")
        if not token:
            # Not launched by Krita Agent; remain completely inert.
            return
        if len(token) < 20:
            raise RuntimeError("Krita Agent token is too short")
        port = int(os.environ.get("KRITA_AGENT_PORT", "47653"))
        if not 1024 <= port <= 65535:
            raise ValueError("Invalid Krita Agent port")
        self.token = token
        self.output_dir = Path(os.environ.get(
            "KRITA_AGENT_OUTPUT_DIR", str(Path.home() / "Pictures" / "KritaAgent"))).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(("127.0.0.1", port))
        self.server.listen(8)
        self.server.settimeout(1.0)
        self.command_timer = QTimer(self)
        self.command_timer.timeout.connect(self._dispatch)
        self.command_timer.start(40)
        self.job_timer = QTimer(self)
        self.job_timer.timeout.connect(self._advance)
        self.job_timer.start(40)
        threading.Thread(target=self._serve, name="KritaAgentIPC", daemon=True).start()

    def createActions(self, window):
        """This Extension provides no user-facing menu actions."""

    def _serve(self):
        while self.server:
            try:
                connection, address = self.server.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            threading.Thread(target=self._handle, args=(connection,), daemon=True).start()

    def _handle(self, connection):
        request_id = None
        reserved = False
        response = None
        with connection:
            connection.settimeout(22)
            try:
                data = b""
                while b"\n" not in data:
                    chunk = connection.recv(4096)
                    if not chunk:
                        raise ValueError("Incomplete JSON request")
                    data += chunk
                    if len(data) > MAX_FRAME:
                        raise ValueError("Request exceeds 1 MiB")
                request = json.loads(data.split(b"\n", 1)[0].decode("utf-8"))
                if not isinstance(request, dict):
                    raise ValueError("Expected JSON object")
                request_id = request.get("id")
                if not isinstance(request_id, str) or not (1 <= len(request_id) <= 80):
                    raise ValueError("Invalid request ID")
                received = request.get("token", "")
                if not isinstance(received, str) or not secrets.compare_digest(received, self.token):
                    raise ValueError("Unauthorized")
                if request.get("command") not in COMMANDS:
                    raise ValueError("Unknown or denied command")
                if not isinstance(request.get("parameters", {}), dict):
                    raise ValueError("Parameters must be an object")
                with self.guard:
                    cached = self.recent.get(request_id)
                    if cached is not None:
                        response = cached
                    elif request_id in self.in_flight:
                        raise ValueError("Duplicate request still in progress")
                    else:
                        self.in_flight.add(request_id)
                        reserved = True
                if response is None:
                    event = threading.Event()
                    holder = {"request": request, "event": event}
                    try:
                        self.queue.put_nowait(holder)
                    except queue.Full:
                        raise RuntimeError("Krita GUI queue full")
                    if not event.wait(20):
                        raise TimeoutError("GUI dispatch timed out; operation may finish later")
                    response = holder["response"]
            except Exception as exc:
                response = {"ok": False, "id": request_id, "error": str(exc)}
            finally:
                if reserved:
                    with self.guard:
                        self.in_flight.discard(request_id)
                        if response is not None:
                            self.recent[request_id] = response
                            if len(self.recent) > 200:
                                self.recent.pop(next(iter(self.recent)))
            try:
                connection.sendall((json.dumps(response, ensure_ascii=False, allow_nan=False) + "\n").encode())
            except (OSError, ValueError):
                pass

    def _dispatch(self):
        for _ in range(6):
            try:
                holder = self.queue.get_nowait()
            except queue.Empty:
                return
            request = holder["request"]
            try:
                result = self._execute(request["command"], request.get("parameters", {}))
                holder["response"] = {"ok": True, "id": request["id"], "result": result}
            except Exception as exc:
                holder["response"] = {"ok": False, "id": request["id"], "error": str(exc)}
            finally:
                holder["event"].set()

    def _doc(self):
        document = Krita.instance().activeDocument()
        if document is None:
            raise RuntimeError("No active document")
        return document

    def _view(self):
        window = Krita.instance().activeWindow()
        if window is None or window.activeView() is None:
            raise RuntimeError("No active Krita view")
        return window.activeView()

    def _node(self):
        document = self._doc()
        node = document.activeNode()
        if node is None or node.type() != "paintlayer" or node.locked():
            raise RuntimeError("Select an unlocked paint layer")
        ability = getattr(node, "paintAbility", None)
        if ability is not None and ability() != "PAINT":
            raise RuntimeError("Active node cannot be painted with current brush")
        return node

    def _safe_path(self, value, suffix, overwrite=False):
        name = _name(value, "path", 300)
        path = Path(name)
        if ".." in path.parts or path.suffix.lower() != suffix:
            raise ValueError("Path traversal or invalid extension")
        target = (path if path.is_absolute() else self.output_dir / path).resolve()
        if target != self.output_dir and self.output_dir not in target.parents:
            raise ValueError("Output path is outside the authorized output directory")
        if target.exists() and not overwrite:
            raise FileExistsError("Refusing to overwrite existing file: " + str(target))
        target.parent.mkdir(parents=True, exist_ok=True)
        return str(target)

    def _capabilities(self):
        node_cls = getattr(krita_module, "Node", None)
        view_cls = getattr(krita_module, "View", None)
        symbols = {
            "Node.paintLine": hasattr(node_cls, "paintLine"),
            "Node.paintPolylineStroke": hasattr(node_cls, "paintPolylineStroke"),
            "StrokePoint": hasattr(krita_module, "StrokePoint"),
            "Node.paintPath": hasattr(node_cls, "paintPath"),
            "Node.paintEllipse": hasattr(node_cls, "paintEllipse"),
            "Node.paintPolygon": hasattr(node_cls, "paintPolygon"),
            "Node.paintRectangle": hasattr(node_cls, "paintRectangle"),
            "View.brushPosition": hasattr(view_cls, "brushPosition"),
            "View.setCurrentBrushPreset": hasattr(view_cls, "setCurrentBrushPreset"),
        }
        return {"krita_version": Krita.instance().version(), "qt_version": QT_VERSION_STR,
                "qt_binding": QT_BINDING, "python": sys.version.split()[0],
                "symbols": symbols, "evidence": "present_in_build only; drawing untested"}

    def _layers(self):
        result = []
        def collect(node, depth=0):
            for child in node.childNodes():
                result.append({"name": child.name(), "type": child.type(),
                               "visible": child.visible(), "locked": child.locked(),
                               "depth": depth})
                if len(result) >= 512:
                    return
                collect(child, depth + 1)
        collect(self._doc().rootNode())
        return result

    def _execute(self, command, p):
        app = Krita.instance()
        if command == "status":
            document = app.activeDocument()
            return {"krita_version": app.version(), "connected": True,
                    "active_document": bool(document),
                    "document": (document.name() if document else None),
                    "jobs": len(self.jobs), "output_dir": str(self.output_dir)}
        if command == "capabilities":
            return self._capabilities()
        if command.startswith("job."):
            return self._job(command, p)
        if command == "canvas.create":
            w = _int(p.get("width"), "width", 1, 8192)
            h = _int(p.get("height"), "height", 1, 8192)
            if w*h > 32000000:
                raise ValueError("Canvas area too large")
            name = _name(p.get("name", "Krita Agent"))
            window = app.activeWindow()
            if window is None:
                raise RuntimeError("Krita has no active window")
            document = app.createDocument(w, h, name, "RGBA", "U8", "", 120.0)
            if document is None:
                raise RuntimeError("Krita could not create the document")
            window.addView(document)
            return {"width": w, "height": h, "name": name}
        if command == "document.info":
            d = self._doc()
            return {"name": d.name(), "width": d.width(), "height": d.height(),
                    "active_layer": d.activeNode().name() if d.activeNode() else None}
        if command == "document.open":
            path = self._safe_path(p.get("path"), ".kra", overwrite=True)
            if not Path(path).is_file():
                raise FileNotFoundError(path)
            doc = app.openDocument(path)
            if doc is None:
                raise RuntimeError("Could not open KRA")
            window = app.activeWindow()
            if window is None:
                raise RuntimeError("No Krita window")
            window.addView(doc)
            return {"opened": path}
        if command == "layer.list":
            return self._layers()
        if command == "layer.create":
            name = _name(p.get("name"))
            doc = self._doc()
            node = doc.createNode(name, "paintlayer")
            if node is None:
                raise RuntimeError("Could not create paint layer")
            if not doc.rootNode().addChildNode(node, None):
                raise RuntimeError("Could not attach paint layer")
            doc.setActiveNode(node)
            return {"name": name, "type": "paintlayer"}
        if command == "layer.select":
            name = _name(p.get("name"))
            doc = self._doc()
            matches = [n for n in doc.rootNode().findChildNodes(name, True, False)
                       if n.name() == name and n.type() == "paintlayer"]
            if len(matches) != 1:
                raise ValueError("Expected exactly one paint layer named " + name)
            doc.setActiveNode(matches[0])
            return {"selected": name}
        if command == "brush.configure":
            view = self._view()
            result = {}
            if "preset" in p:
                preset_name = _name(p["preset"], "preset")
                resources = app.resources("preset")
                resource = resources.get(preset_name)
                if resource is None:
                    resource = next((item for item in resources.values()
                                     if item.name() == preset_name), None)
                if resource is None:
                    raise ValueError("Brush preset not found: " + preset_name)
                view.setCurrentBrushPreset(resource)
                result["preset"] = preset_name
            if "size" in p:
                size = _number(p["size"], "size", 0.1, 1000)
                view.setBrushSize(size)
                result["size"] = size
            if "opacity" in p:
                opacity = _number(p["opacity"], "opacity", 0, 1)
                view.setPaintingOpacity(opacity)
                result["opacity"] = opacity
            if "color" in p:
                value = _name(p["color"], "color", 7)
                color = QColor(value)
                if not color.isValid() or len(value) != 7 or not value.startswith("#"):
                    raise ValueError("Expected #RRGGBB color")
                view.setForeGroundColor(ManagedColor.fromQColor(color, view.canvas()))
                result["color"] = value
            if "pressure_enabled" in p:
                if type(p["pressure_enabled"]) is not bool:
                    raise ValueError("pressure_enabled must be boolean")
                view.setDisablePressure(not p["pressure_enabled"])
                result["pressure_enabled"] = p["pressure_enabled"]
            return result
        if command == "draw.line":
            node = self._node()
            a = QPointF(_number(p.get("x1"), "x1"), _number(p.get("y1"), "y1"))
            b = QPointF(_number(p.get("x2"), "x2"), _number(p.get("y2"), "y2"))
            first = _number(p.get("pressure1", 1), "pressure1", 0, 1)
            last = _number(p.get("pressure2", 1), "pressure2", 0, 1)
            node.paintLine(a, b, first, last)
            return {"mode": "line", "warning": "Visual pressure response depends on active brush preset"}
        if command == "draw.stroke":
            node = self._node()
            raw = p.get("points")
            locations = _points(raw)
            mode = p.get("mode", "auto")
            if mode not in ("auto", "segmented", "continuous"):
                raise ValueError("Unknown stroke mode")
            continuous = hasattr(node, "paintPolylineStroke") and hasattr(krita_module, "StrokePoint")
            if mode == "continuous" and not continuous:
                raise RuntimeError("This Krita build lacks continuous-stroke API")
            if mode == "continuous" or (mode == "auto" and continuous):
                samples = []
                last_time = -1
                for i, item in enumerate(raw):
                    t = _number(item.get("time_ms", i*16), "time_ms", 0, 3600000)
                    if t < last_time:
                        raise ValueError("time_ms must not decrease")
                    last_time = t
                    samples.append(krita_module.StrokePoint(
                        locations[i], _number(item.get("pressure", 1), "pressure", 0, 1),
                        _number(item.get("x_tilt", 0), "x_tilt", -90, 90),
                        _number(item.get("y_tilt", 0), "y_tilt", -90, 90),
                        _number(item.get("rotation", 0), "rotation", -360, 360),
                        _number(item.get("tangential_pressure", 0), "tangential_pressure", 0, 1),
                        t, _number(item.get("speed", 0), "speed", 0, 1)))
                node.paintPolylineStroke(samples)
                return {"mode": "continuous", "points": len(samples),
                        "warning": "Brush must have appropriate pressure dynamics; visual result unverified"}
            if len(locations) == 1:
                pressure = _number(raw[0].get("pressure", 1), "pressure", 0, 1)
                node.paintLine(locations[0], locations[0], pressure, pressure)
            else:
                for i in range(1, len(locations)):
                    p0 = _number(raw[i-1].get("pressure", 1), "pressure", 0, 1)
                    p1 = _number(raw[i].get("pressure", 1), "pressure", 0, 1)
                    node.paintLine(locations[i-1], locations[i], p0, p1)
            return {"mode": "segmented", "points": len(locations),
                    "warning": "Separate paintLine calls may have seams and distinct undo steps"}
        if command == "draw.shape":
            node = self._node()
            kind = p.get("shape")
            fill = p.get("fill", "None")
            if fill not in ("None", "ForegroundColor", "BackgroundColor"):
                raise ValueError("Invalid fill")
            if kind in ("rectangle", "ellipse"):
                rect = p.get("rect")
                if not isinstance(rect, list) or len(rect) != 4:
                    raise ValueError("Expected rect [x,y,w,h]")
                values = [_number(x, "rect", -65536, 65536) for x in rect]
                if values[2] <= 0 or values[3] <= 0:
                    raise ValueError("Invalid rect size")
                box = QRectF(*values)
                if kind == "rectangle":
                    node.paintRectangle(box, "ForegroundColor", fill)
                else:
                    node.paintEllipse(box, "ForegroundColor", fill)
            elif kind in ("polygon", "path"):
                locations = _points(p.get("points"))
                if len(locations) < (3 if kind == "polygon" else 2):
                    raise ValueError("Not enough points for shape")
                if kind == "polygon":
                    node.paintPolygon(locations, "ForegroundColor", fill)
                else:
                    curve = QPainterPath(locations[0])
                    for location in locations[1:]:
                        curve.lineTo(location)
                    node.paintPath(curve, "ForegroundColor", fill)
            else:
                raise ValueError("Unsupported shape")
            return {"shape": kind}
        if command in ("document.save", "document.export"):
            expected = ".kra" if command == "document.save" else ".png"
            if type(p.get("overwrite", False)) is not bool:
                raise ValueError("overwrite must be boolean")
            target = self._safe_path(p.get("path"), expected, p.get("overwrite", False))
            document = self._doc()
            document.waitForDone()
            succeeded = (document.saveAs(target) if expected == ".kra"
                         else document.exportImage(target, InfoObject()))
            if not succeeded:
                raise RuntimeError("Krita refused to write " + target)
            return {"path": target, "format": expected[1:]}
        raise ValueError("Command not implemented or denied: " + command)

    def _job(self, command, p):
        if command == "job.submit":
            steps = p.get("steps")
            if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
                raise ValueError("A job needs 1 to 400 steps")
            for step in steps:
                if not isinstance(step, dict) or step.get("command") not in TASK_STEPS:
                    raise ValueError("Job contains a denied command")
                if not isinstance(step.get("parameters", {}), dict):
                    raise ValueError("Job parameters must be objects")
            identifier = uuid.uuid4().hex
            self.jobs[identifier] = {
                "id": identifier, "state": "queued", "total": len(steps), "done": 0,
                "steps": steps, "error": None, "last_result": None, "cancel_requested": False}
            self.active.append(identifier)
            return self._describe(self.jobs[identifier])
        if command == "job.list":
            return [self._describe(x) for x in list(self.jobs.values())[-100:]]
        identifier = _name(p.get("id"), "job id", 80)
        job = self.jobs.get(identifier)
        if job is None:
            raise ValueError("Unknown job ID")
        if command == "job.status":
            return self._describe(job)
        if command == "job.pause":
            if job["state"] in ("queued", "running"):
                job["state"] = "paused"
        elif command == "job.resume":
            if job["state"] == "paused":
                job["state"] = "running"
        elif command == "job.cancel":
            if job["state"] not in ("completed", "failed", "cancelled"):
                job["cancel_requested"] = True
        else:
            raise ValueError("Unknown job operation")
        return self._describe(job)

    def _describe(self, job):
        return {key: job.get(key) for key in (
            "id", "state", "total", "done", "error", "last_result", "cancel_requested")}

    def _advance(self):
        if not self.active:
            return
        identifier = self.active[0]
        job = self.jobs[identifier]
        if job["cancel_requested"]:
            job["state"] = "cancelled"
            self.active.popleft()
            return
        if job["state"] == "paused":
            return
        if job["done"] >= job["total"]:
            job["state"] = "completed"
            self.active.popleft()
            return
        job["state"] = "running"
        step = job["steps"][job["done"]]
        try:
            job["last_result"] = self._execute(step["command"], step.get("parameters", {}))
            job["done"] += 1
            if job["done"] == job["total"]:
                job["state"] = "completed"
                self.active.popleft()
        except Exception as exc:
            job["state"] = "failed"
            job["error"] = str(exc)
            self.active.popleft()
            # Partial artwork is preserved for inspection; no destructive rollback.


Krita.instance().addExtension(KritaAgentBridge(Krita.instance()))
