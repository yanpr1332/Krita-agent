"""Optional lightweight status Docker. Enabled only via KRITA_AGENT_DOCK=1."""
from krita import Krita, DockWidget, DockWidgetFactory, DockWidgetFactoryBase

try:
    from PyQt5.QtCore import QTimer
    from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
except ImportError:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout

_bridge_ref = None


class AgentStatusDocker(DockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Krita Agent")
        container = QWidget()
        layout = QVBoxLayout(container)
        self.connection = QLabel("Krita Agent: not connected")
        self.progress = QLabel("No active job")
        layout.addWidget(self.connection)
        layout.addWidget(self.progress)
        row = QHBoxLayout()
        for label, operation in (("Pause", "pause"), ("Resume", "resume"), ("Cancel", "cancel")):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, operation=operation: self._action(operation))
            row.addWidget(button)
        layout.addLayout(row)
        self.setWidget(container)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._refresh)
        self.refresh_timer.start(500)

    def canvasChanged(self, canvas):
        self._refresh()

    def _refresh(self):
        bridge = _bridge_ref
        if bridge is None or bridge.server is None:
            self.connection.setText("Krita Agent: disabled")
            self.progress.setText("No active job")
            return
        self.connection.setText("Krita Agent: localhost bridge enabled")
        if not bridge.active:
            self.progress.setText("No active job")
            return
        job = bridge.jobs.get(bridge.active[0])
        if job:
            self.progress.setText("{} · {}/{}".format(
                job["state"], job["done"], job["total"]))

    def _action(self, operation):
        bridge = _bridge_ref
        if bridge is None or not bridge.active:
            return
        # Qt callback already runs on the correct GUI thread.
        bridge._job("job."+operation, {"id": bridge.active[0]})


def register(bridge):
    global _bridge_ref
    _bridge_ref = bridge
    Krita.instance().addDockWidgetFactory(
        DockWidgetFactory("krita_agent_status", DockWidgetFactoryBase.DockRight, AgentStatusDocker))
