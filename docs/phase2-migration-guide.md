# ScummVM i18n Phase 2 — Migration Guide: translations.dat → .mo files

**Date:** 2026-02-19
**Author:** Daniel Nylander <daniel@danielnylander.se>
**License:** GPL-3.0-or-later

---

## Summary

This guide describes how to migrate ScummVM's GUI translation system from the
proprietary `translations.dat` binary format to standard GNU gettext `.mo` files.

**Key benefits:**
- Standard toolchain (`msgfmt`) replaces custom `devtools/create_translations/`
- Per-language files enable incremental updates
- Direct Weblate → `.po` → `msgfmt` → `.mo` pipeline (no custom build step)
- `.mo` is a well-documented, universal format with mature tooling

**What doesn't change:**
- The `_s()` / `_sc()` / `_()` / `_c()` macro system
- The `TranslationManager` public API
- The Weblate workflow (Weblate still produces `.po` files)
- Engine code — no changes needed

---

## Files Changed

### Modified files (in ScummVM source tree)

| File | Change |
|------|--------|
| `common/translation.h` | Added `.mo` support methods, `HashMap` for translations, `_usingMo` flag |
| `common/translation.cpp` | Added `scanMoFiles()`, `loadLanguageMo()`, `parseMoData()`, `moRead32()`; `setLanguage()` tries `.mo` first, falls back to `.dat` |
| `po/POTFILES` | Optionally consolidated (engines already have per-engine POTFILES; total: 1,052 files, 3,069 strings) |

### New files (in data/)

| File | Description |
|------|-------------|
| `translations/<lang>.mo` | Per-language compiled translation files (34 languages) |

### Files that can be removed (future)

| File | Notes |
|------|-------|
| `devtools/create_translations/` | Only needed for `translations.dat` generation |
| `gui/themes/translations.dat` | Replaced by `translations/*.mo` |

---

## Step-by-Step Migration

### Step 1: Apply the integration patch

```bash
cd scummvm/
patch -p0 < patches/mo-reader-integration.patch
```

This modifies `common/translation.h` and `common/translation.cpp` to:
- Scan for `.mo` files in `translations/` directory on startup
- Load per-language `.mo` files using standard GNU gettext binary format
- Fall back to `translations.dat` if no `.mo` files are found

### Step 2: Generate .mo files

```bash
python3 scripts/generate-mo.py --podir po/ --outdir translations/
```

This runs `msgfmt` on each `.po` file. All 34 languages compile successfully.
Place the resulting `translations/` directory where ScummVM can find it
(alongside themes, or in the data path).

### Step 3: Apply the POTFILES expansion (optional, independent)

```bash
cd scummvm/
patch -p0 < patches/potfiles-expansion.patch
```

This adds 741 engine source files to `po/POTFILES`, enabling extraction of
1048+ engine-specific `_s()` strings that were previously invisible to the
translation system.

After applying, regenerate the `.pot` template:

```bash
cd po/
xgettext --files-from=POTFILES --keyword=_:1 --keyword=_s:1 \
         --keyword=_c:1,2c --keyword=_sc:1,2c \
         --keyword=DECLARE_TRANSLATION_ADDITIONAL_CONTEXT:1,2c \
         -o scummvm.pot
```

### Step 4: Test

```bash
python3 scripts/test-mo-reader.py
```

Validates the PoC `.mo` reader against all 34 generated `.mo` files,
including specific string lookups for `sv_SE`.

### Step 5: Remove legacy support (future, optional)

Once confident that `.mo` loading works across all platforms:

1. Remove `devtools/create_translations/` directory
2. Remove `translations.dat` from theme packages
3. Remove the `loadTranslationsInfoDat()` / `loadLanguageDat()` / `checkHeader()` / `openTranslationsFile()` methods
4. Remove `_messageIds` and `_currentTranslationMessages` member variables

---

## Backward Compatibility

The patch implements a **graceful fallback**:

1. On startup, `TranslationManager` scans for `translations/*.mo` files
2. If `.mo` files are found → uses `.mo` path (hash map lookup, O(1))
3. If no `.mo` files found → loads `translations.dat` as before (binary search, O(log n))
4. When switching language, tries `.mo` first, then `.dat`

This means:
- **Old ScummVM + old data** → works (uses `translations.dat`)
- **New ScummVM + old data** → works (falls back to `translations.dat`)
- **New ScummVM + new data** → works (uses `.mo` files)
- **Old ScummVM + new data** → works (ignores `.mo`, uses `translations.dat` if present)

---

## Weblate Integration

**No changes needed.** The workflow remains:

```
Weblate → po/<lang>.po → msgfmt → translations/<lang>.mo
```

The only difference is the final build step: instead of running
`devtools/create_translations/create_translations` to produce a single
`translations.dat`, you run `msgfmt` per language. This is simpler and uses
standard tools available on every system.

The `scripts/generate-mo.py` script automates this and can be integrated
into CI/CD.

---

## Technical Notes

### .mo format

GNU gettext `.mo` is a binary format optimized for fast lookup:
- Magic number identifies endianness (LE: `0x950412de`, BE: `0xde120495`)
- String table with offset/length pairs for originals and translations
- Context encoded as `msgctxt\x04msgid` in the original string
- Well-documented: https://www.gnu.org/software/gettext/manual/html_node/MO-Files.html

### Performance

- `.mo` lookup: O(1) via hash map (vs O(log n) binary search in `.dat`)
- Per-language loading: only the active language is in memory
- File I/O: one small file per language switch (vs re-reading entire `.dat`)

### Size comparison (sv_SE)

| Format | Size |
|--------|------|
| `translations.dat` (all 34 langs) | ~4.5 MB |
| `sv_SE.mo` (single language) | 303 KB |
| All 34 `.mo` files combined | ~6.2 MB |

The total is ~38% larger, but only one language is loaded at a time, reducing
runtime memory usage.

---

## Repository Structure

```
yeager/scummvm-i18n/
├── docs/
│   ├── phase1-report.md          # Initial analysis
│   └── phase2-migration-guide.md # This document
├── patches/
│   ├── mo-reader-integration.patch   # translation.h/.cpp changes
│   └── potfiles-expansion.patch      # POTFILES additions
├── poc/
│   ├── mo_reader.cpp             # Standalone PoC reader
│   └── mo_reader.h
├── scripts/
│   ├── generate-mo.py            # .po → .mo compiler
│   └── test-mo-reader.py         # Validation test suite
└── translations/
    ├── sv_SE.mo                  # 34 compiled .mo files
    ├── de_DE.mo
    └── ...
```
