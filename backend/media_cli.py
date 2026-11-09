"""Database-free, resumable media backfill. JSON stdout is safe for automation."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path

from app.services.media_assets import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, UUID_NAME, check_tools, default_media_root, media_status, process_media


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=default_media_root(), help="Upload root; no database connection is opened")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Inspect only (the default)")
    mode.add_argument("--check-tools", action="store_true", help="Only report FFmpeg/ffprobe availability")
    mode.add_argument("--apply", action="store_true", help="Generate missing/stale derivatives and retry failed/pending jobs")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    report = {"mode": "apply" if args.apply else "check-tools" if args.check_tools else "dry-run",
              "root": str(root), "tools": check_tools(), "items": []}
    if not args.check_tools:
        for directory, directories, filenames in os.walk(root, followlinks=False):
            media_directory = Path(directory) == root / "_media"
            directories[:] = [] if media_directory else sorted(d for d in directories if not (Path(directory) / d).is_symlink())
            for name in sorted(filenames):
                path = Path(directory) / name
                if media_directory and not UUID_NAME.fullmatch(name):
                    continue
                if path.is_symlink() or path.suffix.lower() not in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS:
                    continue
                result = process_media(path, root) if args.apply else media_status(path, root)
                report["items"].append({"source": path.relative_to(root).as_posix(), "status": result["status"], "reason": result.get("reason")})
    report["counts"] = dict(Counter(item["status"] for item in report["items"]))
    print(json.dumps(report, ensure_ascii=True))
    if args.check_tools:
        return 0 if all(tool["status"] == "available" for tool in report["tools"].values()) else 2
    return 1 if args.apply and report["counts"].get("failed") else 0


if __name__ == "__main__":
    raise SystemExit(run())
