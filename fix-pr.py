#!/usr/bin/env python3
"""fix-pr.py

Rename files in a single directory (no recursion) that start with
prwhy-<number>, reviewpr-<number>, prrespond-<number>
to the format <number>-prwhy, <number>-reviewpr, <number>-prrespond

Usage examples:
  python fix-pr.py --dir ~/tmp --dry-run
  python fix-pr.py --dir ~/tmp --force

Options:
  --dir DIR     Directory to process (default: ~/tmp)
  --dry-run     Show what would be renamed without changing files
  --force       Overwrite destination files if they exist
  --verbose     Print detailed operations

This script does not recurse into subdirectories. It only operates on
files directly inside the given directory.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Iterable, List, Tuple


PATTERNS = [
    (re.compile(r"^prwhy-(\d+)(.*)$"), "{num}-prwhy{rest}"),
    (re.compile(r"^reviewpr-(\d+)(.*)$"), "{num}-reviewpr{rest}"),
    (re.compile(r"^prrespond-(\d+)(.*)$"), "{num}-prrespond{rest}"),
]


def find_matches(filenames: Iterable[str]) -> List[Tuple[str, str]]:
    """Return list of (src, dst) for filenames that match known patterns.

    Keeps the remainder of the filename after the number (like extension or
    suffix) and appends it to the new name.
    """
    out: List[Tuple[str, str]] = []
    for name in filenames:
        for regex, fmt in PATTERNS:
            m = regex.match(name)
            if m:
                num = m.group(1)
                rest = m.group(2) or ""
                dst = fmt.format(num=num, rest=rest)
                out.append((name, dst))
                break
    return out


def rename_files(directory: str, pairs: List[Tuple[str, str]], dry_run: bool = True, force: bool = False, verbose: bool = False) -> int:
    """Rename files in `directory` according to pairs (src, dst).

    Returns the number of files successfully renamed (or would be renamed
    in dry-run).
    """
    renamed = 0
    for src, dst in pairs:
        src_path = os.path.join(directory, src)
        dst_path = os.path.join(directory, dst)

        if not os.path.exists(src_path):
            if verbose:
                print(f"skip: source not found: {src_path}")
            continue

        if os.path.exists(dst_path):
            if force:
                if verbose:
                    print(f"overwrite: {dst_path} (exists)")
            else:
                if verbose:
                    print(f"skip: destination exists (use --force to override): {dst_path}")
                continue

        if dry_run:
            print(f"rename: {src} -> {dst}")
            renamed += 1
            continue

        try:
            if force and os.path.exists(dst_path):
                os.remove(dst_path)
            os.rename(src_path, dst_path)
            if verbose:
                print(f"renamed: {src} -> {dst}")
            renamed += 1
        except Exception as exc:  # pragma: no cover - filesystem errors
            print(f"error renaming {src} -> {dst}: {exc}", file=sys.stderr)

    return renamed


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Normalize PR file names in a directory")
    parser.add_argument("--dir", default=os.path.expanduser("~/tmp"), help="Directory to process (default: ~/tmp)")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without renaming files")
    parser.add_argument("--force", action="store_true", help="Overwrite existing destination files")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args(argv)
    directory = os.path.expanduser(args.dir)

    if not os.path.isdir(directory):
        print(f"error: not a directory: {directory}", file=sys.stderr)
        return 2

    try:
        entries = [e for e in os.listdir(directory) if os.path.isfile(os.path.join(directory, e))]
    except Exception as exc:  # pragma: no cover - filesystem errors
        print(f"error reading directory {directory}: {exc}", file=sys.stderr)
        return 3

    pairs = find_matches(entries)

    if not pairs:
        if args.verbose:
            print("no matching files found")
        return 0

    count = rename_files(directory, pairs, dry_run=args.dry_run or False, force=args.force, verbose=args.verbose)

    if args.dry_run:
        print(f"dry-run: {count} file(s) would be renamed")
    else:
        print(f"done: {count} file(s) renamed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
