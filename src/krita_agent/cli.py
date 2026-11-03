"""Read-only, explicit-path inspection of a Krita executable."""
import argparse
import json
import subprocess
from pathlib import Path


def inspect(path, timeout=10):
    executable = Path(path).expanduser().resolve()
    result = {"path": str(executable), "exists": executable.is_file(),
              "version": None, "error": None,
              "runtime_capabilities": "not probed"}
    if not result["exists"]:
        result["error"] = "Executable does not exist or is not a file"
        return result
    try:
        completed = subprocess.run([str(executable), "--version"], capture_output=True,
                                   text=True, timeout=timeout, check=False,
                                   encoding="utf-8", errors="replace")
        output = (completed.stdout or completed.stderr).strip()
        if completed.returncode == 0 and output:
            result["version"] = output
        else:
            result["error"] = f"Version command failed (exit {completed.returncode}): {output}"
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["error"] = str(exc) or type(exc).__name__
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Krita Agent environment tools")
    sub = parser.add_subparsers(dest="command", required=True)
    doctor = sub.add_parser("doctor", help="Inspect an explicitly selected Krita executable")
    doctor.add_argument("--krita", required=True, help="Path to a Krita executable")
    args = parser.parse_args(argv)
    result = inspect(args.krita)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
