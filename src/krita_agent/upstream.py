"""Read-only upstream snapshot; source evidence does not imply runtime support."""
import subprocess
from pathlib import Path


def snapshot(repo):
    root = Path(repo).resolve()
    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args], check=True,
                              capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()
    return {"repository": str(root), "commit": git("rev-parse", "HEAD"),
            "branch": git("branch", "--show-current") or None,
            "dirty": bool(git("status", "--porcelain")),
            "evidence": "source snapshot only; runtime capabilities not verified"}
