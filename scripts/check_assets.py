#!/usr/bin/env python3
"""Verify templates reference existing static files and pages exist."""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL_DIR = os.path.join(ROOT, "frontend", "templates")
STATIC_DIR = os.path.join(ROOT, "frontend", "static")

STATIC_RE = re.compile(r"/static/([^\s\"'<>]+)")


def main():
    missing = []
    for fn in sorted(os.listdir(TPL_DIR)):
        if not fn.endswith(".html"):
            continue
        path = os.path.join(TPL_DIR, fn)
        text = open(path, encoding="utf-8").read()
        for m in STATIC_RE.finditer(text):
            rel = m.group(1).replace("/", os.sep)
            static_path = os.path.join(STATIC_DIR, rel)
            if not os.path.isfile(static_path):
                missing.append((fn, m.group(0)))

    if missing:
        print("MISSING STATIC FILES:")
        for tpl, ref in missing:
            print(f"  {tpl}: {ref}")
        return 1

    print(f"OK: all static references in {len(os.listdir(TPL_DIR))} templates resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
