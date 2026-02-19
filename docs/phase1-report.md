# ScummVM i18n Phase 1 — Kartläggning av översättningssystemet

**Datum:** 2026-02-19
**Status:** Komplett analys + PoC

---

## 1. Översikt: `_s()` / `_sc()` strängar per engine

**Totalt:** 1048 `_s()`-strängar, 0 `_sc()`-strängar i engines/
**Engines med strängar:** 76 av 117
**Engines utan strängar:** 41

### Top 20 engines (flest strängar)

| # | Engine | Antal |
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

### Engines utan `_s()`/`_sc()` (41 st)

access, agds, ags, asylum, avalanche, bbvs, chamber, composer, cryo, dgds, dm, dragons, gnap, hadesch, hpl1, icb, illusions, immortal, kingdom, lab, lastexpress, lilliput, macventure, mediastation, neverhood, ngi, pegasus, petka, pink, playground3d, plumbers, qdengine, saga2, sludge, startrek, sword1, titanic, touche, tsage, tucker, watchmaker

### POTFILES-status

**Inga individuella engine-kataloger finns i `po/POTFILES`!**

POTFILES refererar bara till `engines/*.cpp` (shared files: achievements.cpp, advancedDetector.cpp, dialogs.cpp, engine.cpp, game.cpp, metaengine.cpp, savestate.cpp). Alla 76 engines med `_s()`-strängar saknas alltså i POTFILES, vilket innebär att **engine-specifika strängar aldrig extraheras till .po-filer och aldrig översätts**.

---

## 2. translations.dat binärformat (v4)

### Filstruktur

```
Offset  Type         Beskrivning
0x00    char[12]     Magic: "TRANSLATIONS"
0x0C    uint8        Version (TRANSLATIONS_DAT_VER = 4)
0x0D    uint16BE     N = antal språk

// Block-storlekar (för random access)
0x0F    uint32BE     Storlek: språkbeskrivningar
+4      uint32BE     Storlek: originalmeddelanden (engelska)
+4×N    uint32BE[]   Storlek per översättningsblock

// Block 1: Språklista (N entries)
        [uint16BE len][char[] lang_code]    // t.ex. "sv_SE\0"
        [uint16BE len][char[] lang_name]    // t.ex. "Svenska\0"

// Block 2: Originalmeddelanden
        uint16BE     Antal meddelanden (M)
        M × [uint16BE len][char[] msgid]

// Block 3..N+2: Översättningsblock (ett per språk)
        uint16BE     Antal översatta meddelanden (K)
        K × {
            uint16BE    msgid-index (refererar till Block 2)
            [uint16BE len][char[] msgstr]
            [uint16BE len][char[] msgctxt]  // kan vara tom (len=0)
        }
```

### Strängformat
Varje sträng föregås av `uint16BE length` (inkl. NUL-terminator), följt av `length` bytes data.

### Laddningsflöde
1. `loadTranslationsInfoDat()` — läser header, alla blockstorlekar, språklista, alla original-msgids
2. `loadLanguageDat(index)` — öppnar filen igen, beräknar skip-offset via blockstorlekar, läser enbart det valda språkets block
3. `getTranslation()` — binärsökning på msgid i `_currentTranslationMessages` (sorterade på msgid-index)

---

## 3. Runtime-analys

### Entry points (definierade i `common/translation.h`)

| Makro | Expansion (USE_TRANSLATION) | Expansion (utan) |
|-------|---------------------------|-------------------|
| `_(str)` | `TransMan.getTranslation(str)` | `U32String(str)` |
| `_c(str, ctx)` | `TransMan.getTranslation(str, ctx)` | `U32String(str)` |
| `_s(str)` | `str` (identity — markör för xgettext) | `str` |
| `_sc(str, ctx)` | `str` (identity — markör för xgettext) | `str` |

**Viktigt:** `_s()` och `_sc()` är **bara markörer** — de returnerar strängen oförändrad. De är till för att `xgettext` ska kunna extrahera dem. Översättning sker först när strängen passerar `_()` vid runtime.

### TranslationManager::getTranslation()

- Binärsökning i `_currentTranslationMessages` (sorterat på msgid)
- Context-hantering: hittar alla entries med samma msgid, letar sedan linjärt efter rätt context
- Fallback: returnerar första översättningen om context inte matchar
- Om ingen översättning hittas: returnerar original-msgid som U32String

### Singleton-mönster
`MainTranslationManager` ärver `TranslationManager` + `Singleton`. Instanseras via `TransMan`-makrot.

---

## 4. Proof of Concept: .mo-reader

**Filer:** `/tmp/scummvm-i18n/poc/mo_reader.cpp` + `mo_reader.h`
**Status:** Kompilerar utan fel (C++17)

### Funktionalitet
- Läser .mo-filer (LE och BE)
- Parsear magic, revision, strängtabeller
- Stödjer context via `msgctxt\x04msgid`-encoding (standard gettext)
- Hash-map-baserad lookup (O(1) vs ScummVM:s O(log n) binärsökning)
- 100 rader implementation

### Skillnader mot ScummVM:s TranslationManager
| Aspekt | translations.dat | .mo-fil |
|--------|-----------------|---------|
| Format | Proprietärt binärt | GNU gettext standard |
| Verktyg | create_translations | msgfmt (standard) |
| Alla språk i en fil | Ja | Nej (en .mo per språk) |
| Build-steg | Kräver custom tool | Standard gettext-toolchain |
| Storlek | Kompakt (delad msgid-tabell) | Något större (duplicerade msgids) |

---

## 5. Migrationsförslag

### Steg 1: Fixa POTFILES (lågt hängande frukt)
Lägg till alla 76 engine-kataloger med `_s()`-strängar i `po/POTFILES`. Detta gör att engine-strängar extraheras och kan översättas med befintligt system. **Ingen kodändring behövs.**

Prioritetsordning (efter antal strängar):
1. ultima (319) — ensam ansvarig för 30% av alla engine-strängar
2. mm, scumm, sci, twp, kyra (totalt ~225)
3. Resten batch-vis

### Steg 2: Migrera till standard .mo-filer
1. **Ersätt translations.dat med per-språk .mo-filer** i data/
2. **Byt TranslationManager** att använda MoReader-logik istället för custom binärformat
3. **Ta bort devtools/create_translations/** — ersätts av standard `msgfmt`
4. **Behåll `_s()`/`_sc()` makrona** — de fungerar redan som xgettext-markörer

### Steg 3: Per-engine översättning (framtid)
- Separata .po/.mo per engine (t.ex. `po/engines/ultima/sv.po`)
- Lazy-loading av engine-översättningar vid engine-start
- Möjliggör community-bidrag per engine utan att röra GUI-översättningar

### Risker
- **translations.dat stödjer alla språk i en fil** — .mo kräver en fil per språk, mer I/O
- **Retrokompatibilitet** — äldre ScummVM-versioner förväntar sig translations.dat
- **Binärformat-skillnad** — .mo har ingen context i offsettabellen, context kodas i nyckeln

---

## Sammanfattning

| Mätvärde | Resultat |
|----------|----------|
| Totalt engines | 117 |
| Engines med `_s()` | 76 |
| Totalt `_s()`-strängar | 1048 |
| Engine-strängar i POTFILES | **0** (alla saknas!) |
| translations.dat version | 4 |
| PoC mo_reader | ✅ Kompilerar, ~100 rader |
