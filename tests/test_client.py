"""Local socket protocol tests; run only when user approves verification."""
import json
import socket
import threading
import unittest

from krita_agent.client import Client, BridgeError


class ClientTests(unittest.TestCase):
    def exchange(self, responder):
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        def serve():
            with server:
                connection, _ = server.accept()
                with connection:
                    data = b""
                    while b"\n" not in data:
                        data += connection.recv(4096)
                    connection.sendall((json.dumps(responder(json.loads(data))) + "\n").encode())
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        return Client("test-token", port, timeout=2), thread

    def test_real_socket_roundtrip(self):
        client, thread = self.exchange(lambda request: {
            "ok": True, "id": request["id"], "result": {"version": "test"}})
        self.assertEqual(client.request("status"), {"version": "test"})
        thread.join(2)

    def test_mismatched_response_rejected(self):
        client, thread = self.exchange(lambda request: {
            "ok": True, "id": "wrong", "result": {}})
        with self.assertRaises(BridgeError):
            client.request("status")
        thread.join(2)

    def test_empty_token_and_oversized_request(self):
        with self.assertRaises(ValueError):
            Client("")
        with self.assertRaises(ValueError):
            Client("test").request("status", value="x" * (1024*1024))
