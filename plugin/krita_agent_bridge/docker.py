"""Optional Round 3 Docker: jobs, errors, checkpoint history and preview.

No remote calls, no auto-resume; all buttons operate on the Krita GUI thread.
Qt5 and Qt6 enum handling is kept compatible with the Round 2 acceptance.
"""
from pathlib import Path
from krita import Krita, DockWidget, DockWidgetFactory, DockWidgetFactoryBase

try:
    from PyQt5.QtCore import QTimer
    from PyQt5.QtGui import QPixmap
    from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QListWidget, QScrollArea
except ImportError:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtGui import QPixmap
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QListWidget, QScrollArea

_bridge_ref = None


class AgentStatusDocker(DockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Krita Agent")
        container = QWidget()
        layout = QVBoxLayout(container)
        self.connection = QLabel("Krita Agent: not connected")
        self.progress = QLabel("No active job")
        self.history = QListWidget()
        self.history.setMaximumHeight(140)
        self.error = QLabel("No recorded error")
        self.error.setWordWrap(True)
        self.preview = QLabel("No preview yet")
        self.preview.setMaximumHeight(180)
        self.preview.setMinimumHeight(80)
        layout.addWidget(self.connection)
        layout.addWidget(self.progress)
        layout.addWidget(QLabel("Recent jobs"))
        layout.addWidget(self.history)
        layout.addWidget(self.error)
        layout.addWidget(self.preview)
        row = QHBoxLayout()
        self.controls = []
        for label, operation in (("Pause", "pause"), ("Resume", "resume"), ("Cancel", "cancel")):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, operation=operation: self._action(operation))
            row.addWidget(button)
            self.controls.append(button)
        root = QWidget()
        root_layout = QVBoxLayout(root)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        root_layout.addWidget(scroll)
        root_layout.addLayout(row)
        self.setWidget(root)
        self._last_thumbnail = None
        self._last_rows = ()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh)
        self.refresh_timer.start(750)

    def canvasChanged(self, canvas):
        self._refresh()

    def _refresh(self):
        bridge = _bridge_ref
        if bridge is None or bridge.server is None:
            self.connection.setText("Krita Agent: disabled")
            self.progress.setText("No active job")
            for button in self.controls:
                button.setEnabled(False)
            return
        self.connection.setText("Krita Agent: localhost bridge enabled")
        active = bridge.jobs.get(bridge.active[0]) if bridge.active else None
        for button in self.controls:
            button.setEnabled(active is not None)
        if active:
            self.progress.setText("{} · {}/{}".format(active["state"], active["done"], active["total"]))
        else:
            self.progress.setText("No active job")
        recent = list(bridge.jobs.values())[-8:]
        rows = tuple("{} {} {}/{}".format(j["id"][:8], j["state"], j["done"], j["total"])
                     for j in reversed(recent))
        if rows != self._last_rows:
            self.history.clear()
            self.history.addItems(list(rows))
            self._last_rows = rows
        errors = [str(j["error"]) for j in reversed(recent) if j.get("error")]
        self.error.setText(("Last error: " + errors[0][:220]) if errors else "No recorded error")
        location = getattr(bridge, "last_preview_path", None)
        if not location or not Path(location).is_file():
            return
        try:
            identity = (str(location), Path(location).stat().st_mtime_ns)
            if identity != self._last_thumbnail:
                image = QPixmap(str(location))
                if not image.isNull():
                    self.preview.setPixmap(image.scaledToHeight(min(100, image.height())))
                    self._last_thumbnail = identity
        except OSError:
            pass

    def _action(self, operation):
        bridge = _bridge_ref
        if bridge is None or not bridge.active:
            return
        bridge._job("job." + operation, {"id": bridge.active[0]})


def register(bridge):
    global _bridge_ref
    _bridge_ref = bridge
    position = getattr(DockWidgetFactoryBase, "DockRight", None)
    if position is None:
        position = DockWidgetFactoryBase.DockPosition.DockRight
    Krita.instance().addDockWidgetFactory(
        DockWidgetFactory("krita_agent_status", position, AgentStatusDocker))
