"""Explicit, backup-first Krita user resource installer; dry run by default."""
import argparse
import os
import shutil
from datetime import datetime
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Install Krita Agent Bridge in user pykrita resources")
    parser.add_argument("--resource-dir", help="Explicit Krita pykrita directory")
    parser.add_argument("--apply", action="store_true", help="Actually install (default is dry-run)")
    parser.add_argument("--replace", action="store_true", help="Backup and replace an existing install")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    if args.resource_dir:
        target = Path(args.resource_dir).expanduser()
    else:
        appdata = os.environ.get("APPDATA")
        if not appdata:
            parser.error("APPDATA unavailable; specify --resource-dir")
        target = Path(appdata) / "krita" / "pykrita"
    files = [(root / "plugin" / "krita_agent_bridge.desktop", target / "krita_agent_bridge.desktop"),
             (root / "plugin" / "krita_agent_bridge", target / "krita_agent_bridge")]
    for source, dest in files:
        print(("INSTALL" if args.apply else "WOULD_INSTALL"), source, "->", dest)
        if dest.exists() and not args.replace and args.apply:
            parser.error("Destination exists; use --replace to back it up first: " + str(dest))
        if dest.exists() and not args.apply:
            print("EXISTING_DESTINATION", dest)
    if not args.apply:
        print("DRY RUN: no files were changed.")
        return 0
    target.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for source, dest in files:
        if dest.exists():
            backup = dest.with_name(dest.name + ".backup-" + stamp)
            dest.rename(backup)
            print("BACKUP", backup)
        if source.is_dir():
            shutil.copytree(source, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(source, dest)
    print("Enable Krita Agent Bridge in Settings > Configure Krita > Python Plugin Manager; restart Krita.")
    print("IMPORTANT: Stable and Next may share this resource directory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
