"""Explicit Krita launch configuration and local credential discovery."""
import json
import os
import secrets
import subprocess
import time
from pathlib import Path

DEFAULT_PORT = 47653


def session_path():
    base = os.getenv("LOCALAPPDATA")
    if base:
        return Path(base) / "KritaAgent" / "session.json"
    return Path.home() / ".krita-agent" / "session.json"


def save_session(info, path=None):
    destination = Path(path) if path else session_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + ".tmp")
    temp.write_text(json.dumps(info, indent=2), encoding="utf-8")
    try:
        os.chmod(temp, 0o600)
    except OSError:
        pass
    temp.replace(destination)
    return str(destination)


def load_session(path=None):
    source = Path(path) if path else session_path()
    value = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not value.get("token"):
        raise ValueError("Invalid session: token missing")
    return value


def launch(krita, port=DEFAULT_PORT, output_dir=None, session_file=None,
           input_dir=None, dock=False):
    executable = Path(krita).expanduser().resolve()
    if not executable.is_file() or executable.suffix.lower() != ".exe":
        raise ValueError("Specify a local Krita .exe")
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError("Invalid port")
    output = Path(output_dir or (Path.home() / "Pictures" / "KritaAgent")).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    source = Path(input_dir).expanduser().resolve() if input_dir else output
    if not source.is_dir():
        raise ValueError("Input directory does not exist: " + str(source))
    token = secrets.token_urlsafe(36)
    environment = os.environ.copy()
    environment.update(KRITA_AGENT_TOKEN=token, KRITA_AGENT_PORT=str(port),
                       KRITA_AGENT_OUTPUT_DIR=str(output),
                       KRITA_AGENT_INPUT_DIR=str(source),
                       KRITA_AGENT_DOCK="1" if dock else "0")
    # Bridge will start only if Krita's installed plugin is enabled.
    process = subprocess.Popen([str(executable)], cwd=str(executable.parent),
                               env=environment, close_fds=True)
    data = {"pid": process.pid, "port": port, "token": token,
            "krita": str(executable), "output_dir": str(output),
            "input_dir": str(source), "dock": dock,
            "started_at": time.time()}
    location = save_session(data, session_file)
    return {"pid": process.pid, "port": port, "session": location,
            "output_dir": str(output), "input_dir": str(source), "dock": dock,
            "note": "Launched; Bridge availability is not established. Enable plugin then test status."}
