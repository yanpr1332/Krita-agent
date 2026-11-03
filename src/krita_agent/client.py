"""Authenticated and bounded newline-delimited JSON client."""
import json
import socket
import uuid


class BridgeError(RuntimeError):
    """Bridge transport or remote execution failure."""


class Client:
    MAX_FRAME = 1024 * 1024

    def __init__(self, token, port=47653, timeout=15, host="127.0.0.1"):
        if not isinstance(token, str) or not token:
            raise ValueError("A non-empty bridge token is required")
        if host != "127.0.0.1":
            raise ValueError("Only loopback access is supported")
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError("Invalid port")
        self.token, self.port, self.timeout, self.host = token, port, timeout, host

    def request(self, command, **parameters):
        if not isinstance(command, str) or not command:
            raise ValueError("A command name is required")
        request_id = uuid.uuid4().hex
        payload = {"id": request_id, "token": self.token,
                   "command": command, "parameters": parameters}
        data = (json.dumps(payload, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
        if len(data) > self.MAX_FRAME:
            raise ValueError("Request exceeds 1 MiB")
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as connection:
                connection.settimeout(self.timeout)
                connection.sendall(data)
                response = b""
                while b"\n" not in response:
                    chunk = connection.recv(4096)
                    if not chunk:
                        raise BridgeError("Bridge disconnected before returning a result")
                    response += chunk
                    if len(response) > self.MAX_FRAME:
                        raise BridgeError("Bridge response exceeds 1 MiB")
                result = json.loads(response.split(b"\n", 1)[0])
        except (OSError, ValueError) as exc:
            raise BridgeError(str(exc)) from exc
        if not isinstance(result, dict) or result.get("id") != request_id:
            raise BridgeError("Bridge response ID does not match request")
        if result.get("ok") is not True:
            raise BridgeError(str(result.get("error", "Bridge request failed")))
        return result.get("result")

    def submit(self, steps):
        if not isinstance(steps, list):
            raise ValueError("steps must be a list")
        return self.request("job.submit", steps=steps)
