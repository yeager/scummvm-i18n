# ScummVM i18n Phase 1 — Mapping the Translation System

**Date:** 2026-02-19
**Status:** Complete analysis + PoC

---

## 1. Overview: `_s()` / `_sc()` strings per engine

**Total:** 1048 `_s()` strings, 0 `_sc()` strings in engines/
**Engines with strings:** 76 of 117
**Engines without strings:** 41

### Top 20 engines (most strings)

| # | Engine | Count |
|---|--------|-------|
| 1 | ultima | 319 |
| 2 | mm | 57 |
| 3 | scumm | 51 |
| 4 | sci | 48 |
| 5 | twp | 39 |
| 6 | kyra | 30 |
| 7 | twine | 21 |
| 8 | agi | 21 |
| 9 | freescape | 20 |
| 10 | bladerunner | 19 |
| 11 | agos | 18 |
| 12 | bagel | 17 |
| 13 | efh | 16 |
| 14 | wintermute | 15 |
| 15 | vcruise | 15 |
| 16 | groovie | 15 |
| 17 | zvision | 14 |
| 18 | sherlock | 14 |
| 19 | nancy | 14 |
| 20 | mads | 14 |

### Engines without `_s()`/`_sc()` (41 total)

access, agds, ags, asylum, avalanche, bbvs, chamber, composer, cryo, dgds, dm, dragons, gnap, hadesch, hpl1, icb, illusions, immortal, kingdom, lab, lastexpress, lilliput, macventure, mediastation, neverhood, ngi, pegasus, petka, pink, playground3d, plumbers, qdengine, saga2, sludge, startrek, sword1, titanic, touche, tsage, tucker, watchmaker

### POTFILES status

**No individual engine directories are listed in `po/POTFILES`!**

POTFILES only references `engines/*.cpp` (shared files: achievements.cpp, advancedDetector.cpp, dialogs.cpp, engine.cpp, game.cpp, metaengine.cpp, savestate.cpp). All 76 engines with `_s()` strings are therefore missing from POTFILES, which means that **engine-specific strings are never extracted to .po files and never translated**.

---

## 2. translations.dat binary format (v4)

### File structure

```
Offset  Type         Description
0x00    char[12]     Magic: "TRANSLATIONS"
0x0C    uint8        Version (TRANSLATIONS_DAT_VER = 4)
0x0D    uint16BE     N = number of languages

// Block sizes (for random access)
0x0F    uint32BE     Size: language descriptions
+4      uint32BE     Size: original messages (English)
+4×N    uint32BE[]   Size per translation block

// Block 1: Language list (N entries)
        [uint16BE len][char[] lang_code]    // e.g. "sv_SE\0"
        [uint16BE len][char[] lang_name]    // e.g. "Svenska\0"

// Block 2: Original messages
        uint16BE     Number of messages (M)
        M × [uint16BE len][char[] msgid]

// Block 3..N+2: Translation blocks (one per language)
        uint16BE     Number of translated messages (K)
        K × {
            uint16BE    msgid-index (references Block 2)
            [uint16BE len][char[] msgstr]
            [uint16BE len][char[] msgctxt]  // can be empty (len=0)
        }
```

### String format
Each string is preceded by a `uint16BE length` (including NUL terminator), followed by `length` bytes of data.

### Loading flow
1. `loadTranslationsInfoDat()` — reads header, all block sizes, language list, all original msgids
2. `loadLanguageDat(index)` — reopens the file, calculates skip offset via block sizes, reads only the selected language's block
3. `getTranslation()` — binary search on msgid in `_currentTranslationMessages` (sorted by msgid index)

---

## 3. Runtime analysis

### Entry points (defined in `common/translation.h`)

| Macro | Expansion (USE_TRANSLATION) | Expansion (without) |
|-------|---------------------------|-------------------|
| `_(str)` | `TransMan.getTranslation(str)` | `U32String(str)` |
| `_c(str, ctx)` | `TransMan.getTranslation(str, ctx)` | `U32String(str)` |
| `_s(str)` | `str` (identity — marker for xgettext) | `str` |
| `_sc(str, ctx)` | `str` (identity — marker for xgettext) | `str` |

**Important:** `_s()` and `_sc()` are **only markers** — they return the string unchanged. They exist so that `xgettext` can extract them. Translation only happens when the string passes through `_()` at runtime.

### TranslationManager::getTranslation()

- Binary search in `_currentTranslationMessages` (sorted by msgid)
- Context handling: finds all entries with the same msgid, then searches linearly for the correct context
- Fallback: returns the first translation if the context doesn't match
- If no translation is found: returns the original msgid as U32String

### Singleton pattern
`MainTranslationManager` inherits from `TranslationManager` + `Singleton`. Instantiated via the `TransMan` macro.

---

## 4. Proof of Concept: .mo reader

**Files:** `/tmp/scummvm-i18n/poc/mo_reader.cpp` + `mo_reader.h`
**Status:** Compiles without errors (C++17)

### Functionality
- Reads .mo files (LE and BE)
- Parses magic, revision, string tables
- Supports context via `msgctxt\x04msgid` encoding (standard gettext)
- Hash-map-based lookup (O(1) vs ScummVM's O(log n) binary search)
- 100 lines of implementation

### Differences from ScummVM's TranslationManager
| Aspect | translations.dat | .mo file |
|--------|-----------------|---------|
| Format | Proprietary binary | GNU gettext standard |
| Tools | create_translations | msgfmt (standard) |
| All languages in one file | Yes | No (one .mo per language) |
| Build step | Requires custom tool | Standard gettext toolchain |
| Size | Compact (shared msgid table) | Slightly larger (duplicated msgids) |

---

## 5. Migration proposal

### Step 1: Fix POTFILES (low-hanging fruit)
Add all 76 engine directories with `_s()` strings to `po/POTFILES`. This enables engine strings to be extracted and translated using the existing system. **No code changes required.**

Priority order (by number of strings):
1. ultima (319) — alone responsible for 30% of all engine strings
2. mm, scumm, sci, twp, kyra (total ~225)
3. The rest in batches

### Step 2: Migrate to standard .mo files
1. **Replace translations.dat with per-language .mo files** in data/
2. **Modify TranslationManager** to use MoReader logic instead of the custom binary format
3. **Remove devtools/create_translations/** — replaced by standard `msgfmt`
4. **Keep the `_s()`/`_sc()` macros** — they already work as xgettext markers

### Step 3: Per-engine translation (future)
- Separate .po/.mo per engine (e.g. `po/engines/ultima/sv.po`)
- Lazy-loading of engine translations at engine startup
- Enables community contributions per engine without touching GUI translations

### Risks
- **translations.dat supports all languages in one file** — .mo requires one file per language, more I/O
- **Backward compatibility** — older ScummVM versions expect translations.dat
- **Binary format difference** — .mo has no context in the offset table, context is encoded in the key

---

## Summary

| Metric | Result |
|----------|----------|
| Total engines | 117 |
| Engines with `_s()` | 76 |
| Total `_s()` strings | 1048 |
| Engine strings in POTFILES | **0** (all missing!) |
| translations.dat version | 4 |
| PoC mo_reader | ✅ Compiles, ~100 lines |
