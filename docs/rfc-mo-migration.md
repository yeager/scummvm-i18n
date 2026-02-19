# RFC: Migrate ScummVM Translations from translations.dat to GNU gettext .mo Files

**Author:** Daniel Nylander <daniel@danielnylander.se>
**Date:** 2026-02-19
**Status:** Draft — for discussion on scummvm-devel@
**License:** GPL-3.0-or-later

---

## Abstract

This RFC proposes replacing ScummVM's proprietary `translations.dat` binary
format with standard GNU gettext `.mo` files for GUI and engine string
translations. The change eliminates a custom build tool, integrates with
standard gettext toolchains, reduces runtime memory usage, and enables
all 1,000+ currently untranslated engine strings to enter the translation
pipeline — all without changing a single line of engine code.

## Motivation

### Problem 1: Custom binary format with custom tooling

ScummVM uses `translations.dat`, a proprietary v4 binary format that bundles
all 34 languages into a single file. It is produced by
`devtools/create_translations/`, a custom C++ tool that:

- Must be built and maintained separately
- Has no tests
- Produces a format documented only in source code
- Cannot be inspected or manipulated with standard tools

GNU gettext `.mo` is the industry standard for compiled translations, with
mature tooling (`msgfmt`, `msginit`, `msgmerge`) available on every platform.

### Problem 2: 1,048+ engine strings are never translated

76 engines contain `_s()` translation markers (1,048 strings total), but
**none of their source files appear in `po/POTFILES`**. This means `xgettext`
never extracts them, they never appear in `.po` files, and translators never
see them. The top offenders:

| Engine | Untranslated strings |
|--------|---------------------|
| ultima | 319 |
| mm | 57 |
| scumm | 51 |
| sci | 48 |
| twp | 39 |
| kyra | 30 |

This is a data bug, not a code bug. The fix is adding 741 source files to
`po/POTFILES` — a patch included in this proposal.

### Problem 3: All languages loaded, only one used

`translations.dat` contains all 34 languages in one file (~4.5 MB). While
`TranslationManager` only loads one language at a time via seeking, the
entire msgid table (~1,000 entries) is always in memory. With `.mo` files,
only the selected language's file is loaded — typically ~300 KB.

## Proposal

### Approach: Single .pot, per-language .mo

We propose the simplest possible migration that maintains the current
translation workflow:

1. **One `scummvm.pot` template** containing all strings (GUI + engines)
2. **One `.po` file per language** (same as today)
3. **One `.mo` file per language** in `translations/` directory
4. **Standard `msgfmt`** replaces `devtools/create_translations/`

This is deliberately conservative. Per-engine `.pot` splitting was considered
but rejected for this phase:

- It would create 108 Weblate components, overwhelming for translators
- Context is often shared between engines (e.g., "Save", "Load")
- The monolithic approach matches how ScummVM packages translations today
- Split can be revisited later if the string count grows significantly

### Changes

#### Modified files

| File | Change |
|------|--------|
| `common/translation.h` | Add `.mo` reader methods, `HashMap` for translations |
| `common/translation.cpp` | Add `scanMoFiles()`, `loadLanguageMo()`, `parseMoData()` |
| `po/POTFILES` | Add 741 engine source files (134 → 875 entries) |

#### New files

| File | Description |
|------|-------------|
| `translations/<lang>.mo` | Compiled translation files (34 languages) |

#### Files removable (future)

| File | Notes |
|------|-------|
| `devtools/create_translations/` | Replaced by `msgfmt` |
| `gui/themes/translations.dat` | Replaced by `translations/*.mo` |

### Backward Compatibility

The implementation uses graceful fallback:

```
startup:
  scan for translations/*.mo
  if .mo files found → use .mo path
  else → load translations.dat (existing behavior)
```

All four combinations work:

| ScummVM version | Data | Result |
|----------------|------|--------|
| Old | Old (.dat) | ✅ Works |
| New | Old (.dat) | ✅ Falls back to .dat |
| New | New (.mo) | ✅ Uses .mo |
| Old | New (.mo) | ✅ Ignores .mo, uses .dat if present |

### Translation Workflow

**No changes for translators.** Weblate continues to produce `.po` files.
The only difference is the build step:

```
Before: create_translations *.po → translations.dat
After:  msgfmt <lang>.po → translations/<lang>.mo
```

A `scripts/generate-mo.py` helper automates this for all languages.

## Implementation

### .mo Reader

The `.mo` reader is ~60 lines of C++ that:

1. Reads the standard GNU gettext `.mo` binary format
2. Detects endianness from the magic number (`0x950412de` LE, `0xde120495` BE)
3. Parses the string offset tables
4. Handles `msgctxt\x04msgid` context encoding (standard gettext convention)
5. Stores translations in a `HashMap<String, U32String>` for O(1) lookup

The reader has been validated against all 34 language `.mo` files, including
specific string lookups for Swedish (sv_SE).

### POTFILES Expansion

A patch adds 741 engine source files to `po/POTFILES`. After applying,
`xgettext` extracts all engine `_s()` strings into `scummvm.pot`, making
them visible to translators immediately.

No engine code changes are required — the `_s()` markers are already in place.

### Patches

All patches are available at: https://github.com/yeager/scummvm-i18n

| Patch | Description |
|-------|-------------|
| `patches/mo-reader-integration.patch` | TranslationManager .mo support |
| `patches/potfiles-expansion.patch` | POTFILES engine file additions |

## Benchmarks

Measured on x86_64 Linux (Intel Core i9-14900K), ScummVM 2026.1.1git with
SCUMM engine, SDL2 dummy backend, 20 runs averaged. Full methodology and
raw data in `docs/benchmark-results.md`.

### Startup Performance

| Configuration | Average | Delta |
|---------------|---------|-------|
| Baseline (no translations) | 101 ms | — |
| With .mo (sv_SE, 3058 strings) | 108 ms | +7 ms |

The +7 ms overhead is within noise range and imperceptible to users.

### Memory Usage

| Configuration | Peak RSS |
|---------------|----------|
| Baseline (no translations) | 33,692 KB |
| With .mo (sv_SE) | 33,776 KB |
| **Delta** | **+84 KB** |

Only the active language is loaded. Compare with `translations.dat` which
requires the full msgid table (~1,000 entries) in memory regardless of language.

### Disk Size

| Format | Size |
|--------|------|
| `translations.dat` (all 34 languages) | 3.0 MB |
| `sv_SE.mo` (single language) | 296 KB |
| All 34 `.mo` files combined | 6.4 MB |

Total on-disk size increases by 2.1×, but distribution packages can include
only the languages they need — a significant advantage for embedded/mobile
platforms.

### Build Performance

| Step | translations.dat | .mo files |
|------|-----------------|-----------|
| Compile all languages | ~8 s (create_translations) | ~2 s (msgfmt × 34) |
| Compile one language | N/A (all-or-nothing) | ~0.05 s |
| Tool availability | Custom build required | Standard gettext |

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Platforms without filesystem (e.g., some embedded) | Keep `.dat` fallback; can bundle `.mo` in virtual filesystem |
| `.mo` not endian-safe across platforms | Reader detects endianness from magic; rebuild `.mo` per target if needed (standard practice) |
| More files to distribute | Package managers handle this well; optionally bundle in a tarball |
| Translators confused by new strings | New engine strings appear gradually; no workflow change |

## Rollout Plan

### Phase 1 (immediate, no code changes)
Apply `potfiles-expansion.patch` to add engine source files to `po/POTFILES`.
Run `xgettext` to regenerate `scummvm.pot`. This alone makes 1,048+ engine
strings available for translation.

### Phase 2 (code change, backward compatible)
Apply `mo-reader-integration.patch`. Ship `.mo` files alongside
`translations.dat`. The system auto-detects and prefers `.mo` files.

### Phase 3 (cleanup, future release)
Remove `devtools/create_translations/` and `translations.dat` from the
distribution. Update CI to use `msgfmt` in the build pipeline.

## References

- GNU gettext `.mo` format: https://www.gnu.org/software/gettext/manual/html_node/MO-Files.html
- ScummVM translation system: `common/translation.h`, `common/translation.cpp`
- Weblate ScummVM project: https://translations.scummvm.org/
- Proof of concept & patches: https://github.com/yeager/scummvm-i18n
- Phase 1 analysis: `docs/phase1-report.md`
- Phase 2 migration guide: `docs/phase2-migration-guide.md`
