"""Tier-1 loopback contract: deliberately FAKE Bridge, never native Krita evidence."""
import json
import socketserver
import threading
from contextlib import contextmanager

import pytest

from krita_agent.client import BridgeError, Client


@contextmanager
def fake_bridge(mode="normal"):
    calls = []
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            raw = self.rfile.readline(1024 * 1024 + 1)
            if not raw:
                return
            try:
                req = json.loads(raw)
            except ValueError:
                return
            calls.append(req.get("command"))
            # One request per TCP connection. Drop after executing a mutation
            # to simulate an unknowable outcome; never signal safe replay.
            if mode == "drop" and req.get("command") == "draw.stroke":
                return
            if mode == "wrong-id":
                rid = "invalid-id"
            else:
                rid = req.get("id")
            if req.get("token") != "test-token-value-at-least-20chars":
                data = {"id": rid, "ok": False, "error": "unauthorized"}
            elif req.get("command") == "status":
                data = {"id": rid, "ok": True, "result": {
                    "connected": True, "krita_version": "MOCK (not Krita)",
                    "output_dir": "/fake-output",
                }}
            else:
                data = {"id": rid, "ok": True, "result": {"simulated": True}}
            self.wfile.write(json.dumps(data).encode() + b"\n")

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    with Server(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server.server_address[1], calls
        finally:
            server.shutdown()
            thread.join(timeout=2)


def test_mock_bridge_confirms_client_wire_contract_only():
    with fake_bridge() as (port, calls):
        c = Client("test-token-value-at-least-20chars", port=port)
        status = c.request("status")
        assert status["krita_version"] == "MOCK (not Krita)"
        assert c.request("brush.configure", color="#FF5533")["simulated"] is True
        assert calls == ["status", "brush.configure"]


def test_mock_bridge_rejects_bad_credentials():
    with fake_bridge() as (port, calls):
        with pytest.raises(BridgeError, match="unauthorized"):
            Client("different-secret-value-of-30-chars", port=port).request("status")
        assert calls == ["status"]


def test_mock_bridge_rejects_response_with_wrong_request_id():
    with fake_bridge("wrong-id") as (port, calls):
        with pytest.raises(BridgeError, match="response ID"):
            Client("test-token-value-at-least-20chars", port=port).request("status")
        assert calls == ["status"]


def test_lost_mutation_reply_is_not_automatically_replayed():
    with fake_bridge("drop") as (port, calls):
        with pytest.raises(BridgeError):
            Client("test-token-value-at-least-20chars", port=port, timeout=0.2).request(
                "draw.stroke", points=[{"x": 1, "y": 1, "pressure": 1.0}]
            )
        assert calls == ["draw.stroke"]


def test_outbound_frame_size_check_happens_before_network():
    client = Client("test-token-value-at-least-20chars", port=47653)
    with pytest.raises(ValueError, match="1 MiB"):
        client.request("status", garbage="x" * (1024 * 1024))


def test_native_probe_failure_report_is_not_a_false_acceptance(tmp_path):
    from importlib.util import module_from_spec, spec_from_file_location
    from pathlib import Path
    module_file = Path(__file__).resolve().parents[1] / "scripts" / "cloud_native_probe.py"
    spec = spec_from_file_location("cloud_native_probe", module_file)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    class Fake:
        calls = []
        def request(self, name, **kwargs):
            self.calls.append(name)
            if name == "status":
                return {"connected": True, "krita_version": "MOCK (not Krita)",
                        "output_dir": str(tmp_path)}
            raise BridgeError("reply lost after uncertain native mutation")

    fake = Fake()
    with pytest.raises(BridgeError):
        module.perform_native_smoke(fake, tmp_path, wait=1)
    report = json.loads((tmp_path / "cloud-native-report.json").read_text())
    assert report["status"] == "cloud_native_unverified"
    assert "canvas.create" not in report["native_steps"]
    assert fake.calls == ["status", "canvas.create"]
