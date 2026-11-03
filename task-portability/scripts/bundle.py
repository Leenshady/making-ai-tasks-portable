#!/usr/bin/env python3
"""Package a snapshot bundle directory into a portable zip.

Usage:
    python3 bundle.py <bundle-dir> [-o OUT.zip]

The archive keeps the bundle directory as its top-level entry, so unzipping
restores the original layout.

Standard library only.
"""

import argparse
import os
import sys
import zipfile

SKIP_DIRS = {".git", "__pycache__", ".idea", ".vscode"}


def main():
    parser = argparse.ArgumentParser(
        description="Package a snapshot bundle into a portable zip."
    )
    parser.add_argument("bundle", help="snapshot bundle directory")
    parser.add_argument("-o", "--out", help="output zip path (default <bundle>.zip)")
    args = parser.parse_args()

    source = os.path.abspath(args.bundle)
    if not os.path.isdir(source):
        print("ERROR: not a directory: %s" % source, file=sys.stderr)
        return 2

    name = os.path.basename(source.rstrip(os.sep)) or "bundle"
    target = os.path.abspath(args.out or (name + ".zip"))

    if os.path.exists(target):
        os.remove(target)

    count = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for root, dirs, files in os.walk(source):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for filename in sorted(files):
                full = os.path.join(root, filename)
                if os.path.abspath(full) == target:
                    continue
                relative = os.path.relpath(full, source)
                archive.write(full, os.path.join(name, relative))
                count += 1

    print("Bundled %d file(s) -> %s" % (count, target))
    return 0


if __name__ == "__main__":
    sys.exit(main())
