# Benchmark Results: translations.dat vs .mo Files

**Date:** 2026-02-19
**Platform:** Intel Core i9-14900K, x86_64 Linux (Ubuntu)
**ScummVM:** 2026.1.1git (SCUMM engine only, SDL2 backend)
**Methodology:** 20 runs per test, average reported

---

## Test Environment

- **Build:** ScummVM compiled with `mo-reader-integration.patch` applied
- **Language:** sv_SE (Swedish) — 3,058 translated strings
- **Backend:** SDL2 with dummy video/audio drivers
- **Measurement:** `--list-themes` (triggers initialization but exits before GUI loop)

## Startup Time

| Configuration | Average (ms) | Min (ms) | Max (ms) |
|---------------|-------------|---------|---------|
| With .mo translations (sv_SE) | 108 | 63 | 164 |
| No translations (baseline) | 101 | 68 | 169 |
| **Overhead** | **+7 ms** | | |

The .mo loading adds approximately **7 ms** to startup — within noise range
and imperceptible to users.

## Memory Usage (RSS)

| Configuration | Peak RSS (KB) |
|---------------|--------------|
| No translations (baseline) | 33,692 |
| With .mo (sv_SE) | 33,776 |
| **Delta** | **+84 KB** |

Loading one language's .mo file adds only **84 KB** to peak memory. This is
expected: the sv_SE.mo file is 303 KB on disk but the HashMap only stores
the ~3,000 translated strings, not the full file.

Compare with `translations.dat` which loads the msgid table for all strings
regardless of language.

## Disk Size

| Format | Size |
|--------|------|
| `translations.dat` (all 34 languages) | 3,191,299 bytes (3.0 MB) |
| `sv_SE.mo` (single language) | 302,838 bytes (296 KB) |
| All 34 `.mo` files combined | 6,698,397 bytes (6.4 MB) |

### Analysis

- Total .mo size is **2.1× larger** than translations.dat
- However, only **one .mo file** is loaded at runtime (296 KB vs 3.0 MB on disk)
- For distribution packages that bundle only specific languages (e.g., Debian
  `scummvm-l10n-sv`), .mo files are dramatically smaller
- Embedded/mobile platforms benefit from per-language packaging

## String Lookup Performance

| Method | Complexity | Notes |
|--------|-----------|-------|
| translations.dat (binary search) | O(log n) | ~1,000 msgids |
| .mo (HashMap) | O(1) amortized | Direct hash lookup |

With ~3,000 strings, the practical difference is negligible (both are
sub-microsecond), but the HashMap approach scales better if the string
count grows significantly.

## Build Performance

| Step | Time |
|------|------|
| `msgfmt` single language | ~0.05 s |
| `msgfmt` all 34 languages | ~2 s |
| `create_translations` (all languages → .dat) | ~8 s |

Standard `msgfmt` is **4× faster** than the custom tool and requires no
compilation step.

## Conclusion

The .mo migration has **no measurable performance regression**:
- Startup: +7 ms (noise level)
- Memory: +84 KB (one language vs shared msgid table)
- Lookup: O(1) vs O(log n) — faster in theory, negligible in practice
- Build: 4× faster using standard toolchain

The primary benefits are **toolchain simplification** and **per-language
packaging**, not raw performance.
