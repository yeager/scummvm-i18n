# ScummVM i18n Modernization

**Replacing the custom `translations.dat` binary format with standard GNU gettext `.mo` files — simplifying the build pipeline, enabling per-language packaging, and consolidating a fragmented POTFILES system.**

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL--3.0-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

---

## Executive Summary

This repository contains analysis, patches, proof-of-concept code, and benchmark data for modernizing ScummVM's translation infrastructure. The proposal:

1. **Replace** the custom `translations.dat` binary format with standard GNU gettext `.mo` files
2. **Consolidate** 109 per-engine `POTFILES` + the main `po/POTFILES` into a single file for easier maintenance

The migration requires **zero changes to engine code**, **zero changes to translator workflows**, and maintains **full backward compatibility** with the existing `.dat` format during transition.

---

## The Problem

ScummVM's current translation system works — all 3,069 strings across GUI and 109 engines are extracted and translatable. But the infrastructure has accumulated technical debt:

### 1. Custom Binary Format

`translations.dat` is a proprietary v4 big-endian binary format that bundles all 34 languages into a single 3.0 MB blob. It is produced by `devtools/create_translations/`, a custom C++ tool that:

- Must be compiled separately before building translations
- Has no test suite
- Produces a format documented only in source code comments
- Cannot be inspected or manipulated with standard tools (`msgunfmt`, `pocount`, etc.)
- Implements a custom parser (~300 lines) in `common/translation.cpp`

Every other major open-source project with gettext-based translations uses standard `.mo` files.

### 2. Fragmented POTFILES

Engine strings are extracted via 109 separate `engines/*/POTFILES` files, concatenated by `po/module.mk` at build time. While this works, it means:

- 109 individual files to maintain across engine additions and refactors
- No single place to audit what's being extracted
- The main `po/POTFILES` only lists shared files (~134 entries)
- Total source file count across all POTFILES: 1,052 files

A consolidated POTFILES would be simpler to maintain and audit.

### 3. Monolithic Loading

`translations.dat` contains all 34 languages in one file. While `TranslationManager` uses seeking to load only one language, the entire msgid table is always in memory. Distribution packages must ship the full 3.0 MB file even if the user needs only one language.

---

## The Solution

### Standard `.mo` Files

Replace the custom format with GNU gettext `.mo` files — one per language, produced by the standard `msgfmt` tool. A minimal `.mo` reader (~60 lines of C++) replaces the ~300 line custom parser.

### Consolidated POTFILES

Optionally merge all 1,052 source files into a single `po/POTFILES`, producing an identical `.pot` file with simplified maintenance.

---

## Key Numbers

| Metric | Current | Proposed |
|--------|---------|----------|
| Total translatable strings | 3,069 | 3,069 (unchanged) |
| Engines with translations | 109 | 109 (unchanged) |
| POTFILES to maintain | 110 files (1 main + 109 engine) | 1 file |
| Custom code to maintain | ~800 lines (parser + build tool) | ~60 lines (.mo reader) |
| Build tool required | Custom C++ (compile first) | `msgfmt` (system package) |

### Top Engines by String Count

| Engine | `_s()` Strings |
|--------|---------------|
| ultima | 319 |
| mm | 57 |
| scumm | 51 |
| sci | 48 |
| twp | 39 |
| kyra | 30 |

Full analysis: [`docs/phase1-report.md`](docs/phase1-report.md)

---

## Performance Comparison

All benchmarks measured on x86_64 Linux (Intel Core i9-14900K), ScummVM 2026.1.1git, SDL2 dummy backend, 20 runs averaged. Full data: [`docs/benchmark-results.md`](docs/benchmark-results.md)

| Metric | `translations.dat` | `.mo` files | Delta |
|--------|-------------------|-------------|-------|
| **Startup time** | 101 ms (baseline) | 108 ms | +7 ms (noise level) |
| **Memory (RSS)** | All msgids loaded | +84 KB (one language) | Per-language only |
| **Disk (all languages)** | 3.0 MB (one blob) | 6.4 MB (34 files) | 2.1× larger total |
| **Disk (one language)** | 3.0 MB (entire blob) | 296 KB | **10× smaller** |
| **Build time** | ~8 s (custom tool) | ~2 s (msgfmt × 34) | **4× faster** |
| **Build one language** | N/A (all-or-nothing) | ~0.05 s | Incremental |
| **String lookup** | O(log n) binary search | O(1) HashMap | Faster |
| **Tool required** | Custom C++ (compile first) | `msgfmt` (system package) | Standard |

---

## Pros and Cons

### ✅ Pros

- **Standard tooling** — `msgfmt`, `msgunfmt`, `pocount`, `gettext` ecosystem works out of the box
- **Less custom code** — ~60 line reader replaces ~300 line custom parser + separate build tool
- **Per-language loading** — only the active language is in memory (296 KB vs 3.0 MB blob)
- **4× faster builds** — standard `msgfmt` vs custom `create_translations`
- **Easier local testing** — edit `.po`, run `msgfmt`, restart ScummVM. No recompile of custom tool
- **Distribution-friendly** — package managers can ship per-language packages (`scummvm-l10n-sv`)
- **Incremental builds** — change one language, rebuild one file in 0.05s
- **Consolidated POTFILES** — single file to audit instead of 110

### ⚠️ Cons

- **More files** — 34 `.mo` files instead of one `.dat` blob
- **Slightly larger total disk** — 6.4 MB vs 3.0 MB when shipping all languages (2.1×)
- **Migration effort** — code review, testing, transition period with both formats
- **Platform edge cases** — embedded systems without filesystem need virtual FS or continued `.dat` support

---

## Migration Path

| Phase | Description | Code Changes |
|-------|-------------|-------------|
| **Phase 1** | Analysis & proof of concept (complete) | None |
| **Phase 2** | Apply `.mo` reader patch. Ship `.mo` alongside `.dat`. Auto-detection prefers `.mo`. | Backward compatible |
| **Phase 3** | Optionally consolidate POTFILES. Identical `.pot` output. | Structural only |
| **Phase 4** | Remove `devtools/create_translations/` and `translations.dat`. Update CI to use `msgfmt`. | Cleanup |

Each phase is independently valuable and can be shipped in separate releases.

---

## Compatibility

| Concern | Impact |
|---------|--------|
| **Weblate workflow** | Unchanged — Weblate produces `.po` files regardless of compiled format |
| **Translator experience** | Unchanged — same `.po` editing, same Weblate UI |
| **Old ScummVM + new data** | ✅ Ignores `.mo` files, uses `.dat` if present |
| **New ScummVM + old data** | ✅ Falls back to `.dat` when no `.mo` files found |
| **New ScummVM + new data** | ✅ Prefers `.mo` files |
| **Engine code** | Zero changes — `_s()` calls work identically |

---

## How to Test

```bash
# 1. Clone this repo
git clone https://github.com/yeager/scummvm-i18n.git
cd scummvm-i18n

# 2. Clone ScummVM
git clone https://github.com/scummvm/scummvm.git /tmp/scummvm-test

# 3. Apply patches
cd /tmp/scummvm-test
git apply /path/to/scummvm-i18n/patches/mo-reader-integration.patch

# 4. Build ScummVM
./configure
make -j$(nproc)

# 5. Copy .mo files
mkdir -p translations/
cp /path/to/scummvm-i18n/translations/*.mo translations/

# 6. Run and set language to verify
./scummvm
# Options → GUI → Language → pick any language
```

See [`docs/TESTING.md`](docs/TESTING.md) for detailed step-by-step instructions.

---

## Repository Structure

```
README.md                           This file
docs/
  benchmark-results.md              Performance measurements (.dat vs .mo)
  phase1-report.md                  Full analysis of current translation system
  phase2-migration-guide.md         Implementation details for .mo integration
  rfc-mo-migration.md               Formal RFC for scummvm-devel@
  COMPARISON.md                     Side-by-side format comparison
  TESTING.md                        Step-by-step testing guide
patches/
  mo-reader-integration.patch       TranslationManager .mo reader support
  potfiles-expansion.patch          POTFILES consolidation patch
poc/
  mo_reader.cpp                     Standalone .mo reader proof of concept
  mo_reader.h                       Header for PoC reader
scripts/
  generate-mo.py                    Compile all .po → .mo files
  test-mo-reader.py                 Validation script for .mo reading
translations/
  *.mo                              Pre-built .mo files for all 34 languages
```

---

## License

All code in this repository is licensed under [GPL-3.0-or-later](https://www.gnu.org/licenses/gpl-3.0), matching ScummVM.
