# Testing Guide: ScummVM `.mo` Translation Support

Step-by-step instructions for building and testing the `.mo` translation patches.

---

## Prerequisites

- Git
- Standard build tools (`gcc`/`clang`, `make`)
- SDL2 development libraries
- GNU gettext (`msgfmt` command)
- A ScummVM-supported platform (Linux, macOS, Windows with MSYS2)

### Installing gettext

```bash
# Debian/Ubuntu
sudo apt install gettext

# macOS (Homebrew)
brew install gettext

# Fedora
sudo dnf install gettext
```

---

## Step 1: Clone Repositories

```bash
# Clone this repo (patches and .mo files)
git clone https://github.com/yeager/scummvm-i18n.git
cd scummvm-i18n

# Clone ScummVM
git clone https://github.com/scummvm/scummvm.git /tmp/scummvm-test
```

---

## Step 2: Apply Patches

```bash
cd /tmp/scummvm-test

# Apply the .mo reader integration patch
git apply /path/to/scummvm-i18n/patches/mo-reader-integration.patch

# Apply the POTFILES expansion patch (optional — for regenerating .pot)
git apply /path/to/scummvm-i18n/patches/potfiles-expansion.patch
```

### Verify patches applied cleanly

```bash
git diff --stat
# Should show changes to:
#   common/translation.h
#   common/translation.cpp
#   po/POTFILES (if second patch applied)
```

---

## Step 3: Build ScummVM

```bash
cd /tmp/scummvm-test

./configure
make -j$(nproc)
```

The build should complete without warnings related to translation code.

---

## Step 4: Install `.mo` Files

```bash
# Create the translations directory next to the ScummVM binary
mkdir -p /tmp/scummvm-test/translations/

# Copy pre-built .mo files from this repo
cp /path/to/scummvm-i18n/translations/*.mo /tmp/scummvm-test/translations/
```

### Alternatively, build `.mo` files from `.po` sources

```bash
# If you have .po files (e.g., from ScummVM's po/ directory)
msgfmt -o translations/sv_SE.mo po/sv_SE.po
```

Or use the helper script:

```bash
python3 /path/to/scummvm-i18n/scripts/generate-mo.py \
    --po-dir /tmp/scummvm-test/po \
    --output-dir /tmp/scummvm-test/translations
```

---

## Step 5: Verify `.mo` Loading

### Quick test (no GUI)

```bash
cd /tmp/scummvm-test

# Run with --list-themes to trigger translation initialization
./scummvm --list-themes 2>&1 | head -20
# Should complete without errors
```

### GUI test

```bash
./scummvm
```

1. Go to **Options** → **GUI** → **Language**
2. Select any language (e.g., "Svenska")
3. Click **OK**
4. Verify that the GUI is now in the selected language
5. All menus, buttons, and dialogs should be translated

### Verify .mo is being used (not .dat fallback)

To confirm the `.mo` path is active, temporarily rename or remove `gui/themes/translations.dat`:

```bash
mv gui/themes/translations.dat gui/themes/translations.dat.bak
./scummvm
# Translations should still work (loaded from .mo files)
# If translations disappear, the .mo loading is not working
```

---

## Step 6: Validate String Coverage

### Check that engine strings are extracted (requires POTFILES patch)

```bash
cd /tmp/scummvm-test

# Regenerate the .pot template
cd po/
xgettext --files-from=POTFILES --keyword=_s --keyword=_sc:1,2c \
    --from-code=UTF-8 -o scummvm.pot

# Count strings
grep -c '^msgid ' scummvm.pot
# Should be significantly higher than before the POTFILES patch
# (1,048+ additional engine strings)
```

### Verify specific engine strings

```bash
# Check that ultima strings are now in the .pot
grep -i "ultima" scummvm.pot | head -10

# Check any specific engine
grep "engines/scumm" scummvm.pot | head -10
```

---

## Step 7: Test Backward Compatibility

### Scenario A: New code, old data (`.dat` only)

```bash
rm -rf translations/   # Remove .mo files
# Ensure gui/themes/translations.dat exists
./scummvm              # Should work with .dat fallback
```

### Scenario B: New code, both formats

```bash
# Restore .mo files AND keep translations.dat
cp /path/to/scummvm-i18n/translations/*.mo translations/
# .mo files should be preferred over .dat
./scummvm
```

### Scenario C: New code, `.mo` only

```bash
mv gui/themes/translations.dat gui/themes/translations.dat.bak
# Only .mo files present
./scummvm              # Should work with .mo files
```

---

## Known Issues

1. **Endianness**: `.mo` files are architecture-specific by default. The reader handles both little-endian and big-endian `.mo` files via magic number detection, but `msgfmt` produces native-endian output. Pre-built `.mo` files in this repo are little-endian (x86). Cross-compilation targets may need regeneration.

2. **Virtual filesystems**: Platforms that use ScummVM's virtual filesystem (e.g., some embedded targets) need the `.mo` files accessible through the archive system. The fallback to `translations.dat` covers these cases during the transition period.

3. **Language codes**: `.mo` filenames must match ScummVM's expected language codes exactly (e.g., `sv_SE.mo`, not `sv.mo`). The existing language code mapping in `TranslationManager` is preserved.

4. **Plural forms**: The `.mo` reader handles standard gettext plural forms. Complex plural rules (e.g., Polish, Arabic) work correctly as they are encoded in the `.mo` file's header.

---

## Reporting Issues

If you encounter problems during testing, please file an issue at:
https://github.com/yeager/scummvm-i18n/issues

Include:
- Platform and architecture
- ScummVM version / git commit
- Which patches were applied
- The specific error or unexpected behavior
- Console output if available
