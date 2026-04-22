"""
Single entry for local / server: build Vue admin + mobile H5, then start Flask (API + static).

Usage:
  python start.py                 # npm run build (admin + mobile) + python backend/wsgi.py
  python start.py --skip-build    # only start Flask (expects built files under static/admin & static/mobile)
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys


ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_ADMIN = os.path.join(ROOT, "frontend-admin")
FRONTEND_MOBILE = os.path.join(ROOT, "frontend-mobile")
BACKEND = os.path.join(ROOT, "backend")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Do not run npm run build; use existing static/admin and static/mobile",
    )
    args = parser.parse_args()

    if not args.skip_build:
        if not os.path.isdir(FRONTEND_ADMIN):
            raise SystemExit("frontend-admin/ not found")
        if not os.path.isdir(FRONTEND_MOBILE):
            raise SystemExit("frontend-mobile/ not found")
        subprocess.check_call(["npm", "run", "build"], cwd=FRONTEND_ADMIN)
        subprocess.check_call(["npm", "run", "build"], cwd=FRONTEND_MOBILE)

    # Run Flask dev server from wsgi.py (single process serves /api + SPA)
    subprocess.check_call([sys.executable, "wsgi.py"], cwd=BACKEND)


if __name__ == "__main__":
    main()
