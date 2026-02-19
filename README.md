# ScummVM i18n Modernization

Analysis, proof-of-concept code, and patches for modernizing ScummVM's translation infrastructure.

## Goal

Replace the custom `translations.dat` binary format with standard gettext `.mo` files, and expand translation coverage to engine-specific strings.

## Status

- [x] Phase 1: Analysis & mapping ([report](docs/phase1-report.md))
- [ ] Phase 2: .mo reader integration
- [ ] Phase 3: Per-engine translation domains
- [ ] Phase 4: POTFILES expansion (1048 untranslatable engine strings identified)

## Key Findings

- **1048 `_s()` strings** across 76/117 engines are never extracted (not in `po/POTFILES`)
- `translations.dat` is a custom big-endian binary blob (format v4) bundling all languages
- A minimal `.mo` reader (~100 lines C++) can replace the custom format entirely
- Migration requires zero changes to the Weblate workflow or translator experience

## Structure

```
docs/       — Analysis reports
poc/        — Proof-of-concept code (mo_reader)
patches/    — Future patches for ScummVM
```

## Note

This is a staging repo for preparation and testing. No PRs will be submitted to ScummVM until everything is thoroughly tested.

## License

PoC code: GPL-3.0 (matching ScummVM)
