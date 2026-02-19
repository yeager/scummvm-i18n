#!/usr/bin/env bash
# expand-potfiles.sh — Generate expanded .pot and merge/compile all .po → .mo
#
# This script automates the full i18n build pipeline for ScummVM:
#   1. Collects all POTFILES (global + per-engine)
#   2. Runs xgettext to generate scummvm.pot
#   3. Merges each .po with the new .pot (adding new untranslated strings)
#   4. Compiles each .po to .mo
#
# Usage:
#   ./scripts/expand-potfiles.sh [SCUMMVM_DIR] [OUTPUT_DIR]
#
# SCUMMVM_DIR defaults to current directory (must be ScummVM source root).
# OUTPUT_DIR  defaults to ./translations/
#
# Requirements: xgettext, msgmerge, msgfmt (GNU gettext tools)
#
# Copyright (C) 2026 Daniel Nylander <daniel@danielnylander.se>
# License: GPL-3.0-or-later

set -euo pipefail

SCUMMVM_DIR="${1:-.}"
OUTPUT_DIR="${2:-${SCUMMVM_DIR}/translations}"

# Validate
if [ ! -f "${SCUMMVM_DIR}/po/POTFILES" ]; then
    echo "Error: ${SCUMMVM_DIR}/po/POTFILES not found. Is this a ScummVM source tree?" >&2
    exit 1
fi

command -v xgettext >/dev/null 2>&1 || { echo "Error: xgettext not found (install gettext)" >&2; exit 1; }
command -v msgmerge >/dev/null 2>&1 || { echo "Error: msgmerge not found (install gettext)" >&2; exit 1; }
command -v msgfmt   >/dev/null 2>&1 || { echo "Error: msgfmt not found (install gettext)"  >&2; exit 1; }

POTFILE="${SCUMMVM_DIR}/po/scummvm.pot"
PODIR="${SCUMMVM_DIR}/po"

echo "=== Step 1: Collecting POTFILES ==="

# Collect global POTFILES + per-engine POTFILES (same as po/module.mk)
ENGINE_POTFILES=$(find "${SCUMMVM_DIR}/engines" -name POTFILES -type f 2>/dev/null | sort)
COMBINED_LIST=$(mktemp)
cat "${SCUMMVM_DIR}/po/POTFILES" ${ENGINE_POTFILES} | sort -u > "${COMBINED_LIST}"
TOTAL_FILES=$(wc -l < "${COMBINED_LIST}" | tr -d ' ')
echo "  Total source files: ${TOTAL_FILES}"

echo "=== Step 2: Generating scummvm.pot ==="

TMPPOT=$(mktemp)
xgettext -f "${COMBINED_LIST}" -D "${SCUMMVM_DIR}" \
    -d scummvm --c++ \
    -k_ -k_s -k_c:1,2c -k_sc:1,2c \
    -kDECLARE_TRANSLATION_ADDITIONAL_CONTEXT:1,2c \
    --add-comments=I18N \
    --from-code=UTF-8 \
    --package-name=ScummVM \
    --copyright-holder="ScummVM Team" \
    --msgid-bugs-address=scummvm-devel@lists.scummvm.org \
    -o "${TMPPOT}" 2>&1 | grep -v 'warning:' || true

# Apply ScummVM's standard header fixups
sed -e 's/SOME DESCRIPTIVE TITLE/LANGUAGE translation for ScummVM/' \
    -e 's/UTF-8/CHARSET/' \
    -e 's/PACKAGE/ScummVM/' "${TMPPOT}" > "${POTFILE}"
rm -f "${TMPPOT}"

TOTAL_STRINGS=$(grep -c '^msgid ' "${POTFILE}")
echo "  Total translatable strings: ${TOTAL_STRINGS}"

echo "=== Step 3: Merging .po files ==="

mkdir -p "${OUTPUT_DIR}"
LANG_COUNT=0
FAIL_COUNT=0

for po in "${PODIR}"/*.po; do
    [ -f "$po" ] || continue
    lang=$(basename "$po" .po)

    if msgmerge -q "$po" "${POTFILE}" -o "${po}.new" 2>/dev/null; then
        mv "${po}.new" "$po"
        LANG_COUNT=$((LANG_COUNT + 1))
    else
        echo "  WARNING: msgmerge failed for ${lang}" >&2
        FAIL_COUNT=$((FAIL_COUNT + 1))
        rm -f "${po}.new"
    fi
done
echo "  Merged: ${LANG_COUNT} languages (${FAIL_COUNT} failures)"

echo "=== Step 4: Compiling .mo files ==="

MO_COUNT=0
for po in "${PODIR}"/*.po; do
    [ -f "$po" ] || continue
    lang=$(basename "$po" .po)
    mofile="${OUTPUT_DIR}/${lang}.mo"

    if msgfmt "$po" -o "${mofile}" 2>/dev/null; then
        stats=$(msgfmt --statistics "$po" 2>&1 || true)
        size=$(wc -c < "${mofile}" | tr -d ' ')
        echo "  ${lang}: ${size} bytes — ${stats}"
        MO_COUNT=$((MO_COUNT + 1))
    else
        echo "  WARNING: msgfmt failed for ${lang}" >&2
    fi
done

echo ""
echo "=== Summary ==="
echo "  Source files in POTFILES: ${TOTAL_FILES}"
echo "  Translatable strings:    ${TOTAL_STRINGS}"
echo "  Languages compiled:      ${MO_COUNT}"
echo "  Output directory:        ${OUTPUT_DIR}/"
echo ""
echo "Done. Place ${OUTPUT_DIR}/ in ScummVM's data path to use .mo translations."

rm -f "${COMBINED_LIST}"
