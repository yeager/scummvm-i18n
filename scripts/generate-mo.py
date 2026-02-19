#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate .mo files from ScummVM .po files.

Usage:
    python3 generate-mo.py [--podir PO_DIR] [--outdir OUT_DIR]

Runs msgfmt on each .po file in podir and writes the corresponding .mo
to outdir.  Exit code is non-zero if any language fails to compile.

SPDX-License-Identifier: GPL-3.0-or-later
Copyright (C) 2026 Daniel Nylander <daniel@danielnylander.se>
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Compile .po → .mo for ScummVM")
    parser.add_argument("--podir", default="po", help="Directory with .po files")
    parser.add_argument("--outdir", default="translations", help="Output directory for .mo files")
    parser.add_argument("--check", action="store_true", help="Also run --check-format")
    args = parser.parse_args()

    podir = Path(args.podir)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    po_files = sorted(podir.glob("*.po"))
    if not po_files:
        print(f"ERROR: No .po files found in {podir}", file=sys.stderr)
        return 1

    ok = 0
    fail = 0

    for po in po_files:
        lang = po.stem  # e.g. "sv_SE"
        mo = outdir / f"{lang}.mo"

        cmd = ["msgfmt"]
        if args.check:
            cmd.append("--check-format")
        cmd += ["-o", str(mo), str(po)]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FAIL  {lang}: {result.stderr.strip()}")
            fail += 1
        else:
            size = mo.stat().st_size
            print(f"  OK  {lang} → {mo.name} ({size:,} bytes)")
            ok += 1

    print(f"\nResults: {ok} OK, {fail} FAILED out of {ok + fail} languages")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
