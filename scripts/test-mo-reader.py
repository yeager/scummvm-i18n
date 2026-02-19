#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the MoReader PoC against generated .mo files.

1. Compiles poc/mo_reader.cpp into a test binary with an embedded main().
2. Runs the binary against translations/sv_SE.mo (and others).
3. Validates specific string lookups using a companion C++ test harness.

SPDX-License-Identifier: GPL-3.0-or-later
Copyright (C) 2026 Daniel Nylander <daniel@danielnylander.se>
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
POC_DIR = REPO / "poc"
TRANS_DIR = REPO / "translations"

TEST_HARNESS = r"""
#include "mo_reader.h"
#include <iostream>
#include <cstdlib>
#include <cassert>

int main(int argc, char *argv[]) {
    if (argc < 2) {
        std::cerr << "Usage: " << argv[0] << " <file.mo> [msgid [expected_msgstr]]" << std::endl;
        return 1;
    }

    MoReader reader;
    if (!reader.loadFromFile(argv[1])) {
        std::cerr << "FAIL: Could not load " << argv[1] << std::endl;
        return 1;
    }

    std::cout << "Loaded " << reader.size() << " strings from " << argv[1] << std::endl;

    if (argc >= 3) {
        const std::string &trans = reader.getTranslation(argv[2]);
        if (trans.empty()) {
            std::cerr << "FAIL: No translation for '" << argv[2] << "'" << std::endl;
            return 1;
        }
        std::cout << "  \"" << argv[2] << "\" => \"" << trans << "\"" << std::endl;

        if (argc >= 4) {
            std::string expected(argv[3]);
            if (trans != expected) {
                std::cerr << "FAIL: Expected '" << expected << "' but got '" << trans << "'" << std::endl;
                return 1;
            }
            std::cout << "  MATCH OK" << std::endl;
        }
    }

    // Self-test: look up a string that shouldn't exist
    const std::string &missing = reader.getTranslation("__nonexistent_string_42__");
    if (!missing.empty()) {
        std::cerr << "FAIL: Non-existent string returned a value" << std::endl;
        return 1;
    }

    std::cout << "ALL TESTS PASSED" << std::endl;
    return 0;
}
"""


def main():
    # Write test harness
    test_main = POC_DIR / "test_main.cpp"
    test_main.write_text(TEST_HARNESS)

    # Compile
    binary = POC_DIR / "test_mo_reader"
    cmd = [
        "c++", "-std=c++17", "-O2", "-Wall", "-Wextra",
        "-I", str(POC_DIR),
        str(POC_DIR / "mo_reader.cpp"),
        str(test_main),
        "-o", str(binary),
    ]
    print(f"Compiling: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"COMPILE FAIL:\n{r.stderr}")
        return 1
    print("Compilation OK\n")

    failures = 0

    # Test 1: Load sv_SE.mo and check string count
    mo_sv = TRANS_DIR / "sv_SE.mo"
    if not mo_sv.exists():
        print(f"SKIP: {mo_sv} not found")
        return 1

    print("=== Test 1: Load sv_SE.mo ===")
    r = subprocess.run([str(binary), str(mo_sv)], capture_output=True, text=True)
    print(r.stdout)
    if r.returncode != 0:
        print(f"FAIL: {r.stderr}")
        failures += 1

    # Test 2: Look up known strings from sv_SE
    # We extract a known msgid/msgstr pair from the .po first
    print("=== Test 2: Known string lookup (sv_SE) ===")
    known_pairs = extract_known_pairs(Path("/tmp/scummvm-phase2/po/sv_SE.po"), limit=5)
    for msgid, msgstr in known_pairs:
        r = subprocess.run(
            [str(binary), str(mo_sv), msgid, msgstr],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            print(f"  FAIL: '{msgid}' => expected '{msgstr}'")
            print(f"    {r.stderr.strip()}")
            failures += 1
        else:
            print(f"  OK: '{msgid}' => '{msgstr}'")

    # Test 3: Load all .mo files, check they parse
    print("\n=== Test 3: Load all .mo files ===")
    for mo in sorted(TRANS_DIR.glob("*.mo")):
        r = subprocess.run([str(binary), str(mo)], capture_output=True, text=True)
        status = "OK" if r.returncode == 0 else "FAIL"
        count = ""
        for line in r.stdout.splitlines():
            if "Loaded" in line:
                count = line.strip()
                break
        print(f"  {status}  {mo.name}: {count}")
        if r.returncode != 0:
            failures += 1

    # Cleanup
    test_main.unlink(missing_ok=True)
    binary.unlink(missing_ok=True)

    print(f"\n{'ALL TESTS PASSED' if failures == 0 else f'{failures} FAILURES'}")
    return 1 if failures else 0


def extract_known_pairs(po_path, limit=5):
    """Extract simple msgid/msgstr pairs from a .po file."""
    pairs = []
    if not po_path.exists():
        return pairs

    with open(po_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines) and len(pairs) < limit:
        line = lines[i].strip()
        if line.startswith("msgid ") and not line.startswith("msgid_plural"):
            msgid = line[7:-1]  # strip msgid "..."
            # Skip empty msgid
            if not msgid:
                i += 1
                continue
            # Check it's a simple single-line entry
            i += 1
            if i < len(lines):
                next_line = lines[i].strip()
                if next_line.startswith("msgstr "):
                    msgstr = next_line[8:-1]
                    if msgstr and '\\"' not in msgid and '\\"' not in msgstr:
                        pairs.append((msgid, msgstr))
        i += 1

    return pairs


if __name__ == "__main__":
    sys.exit(main())
