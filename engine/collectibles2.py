# Save Garage - Copyright (C) 2026 NotHGM - GNU GPL v3 with the additional terms in NOTICE; see LICENSE.
"""Collectibles of the 100% checklist, second pass: the two keyed tables of section e4fcc5fa (Save Garage feature module).

Same interface as collectibles.py (read(b) -> dict, apply(b, choice) -> (bytes, log)); research_notes/
checklist-collectibles2.md has the evidence in full and the PS5 test plan.

THE TABLES (section e4fcc5fa, CodeSaveBlock; unchanged from collectibles.py)
  UniqueCollectibles   0xbc515b02: keys 0x2c99b768 / timestampsSec 0xa7cc5745 (int64) / stateFlags 0xcab27d5f (char)
  InfiniteCollectibles 0xa474d047: the same three columns + foundCounts 0x69e24cfe + 0x9607f9af (0 everywhere)
  722 and 887 entries in every save copy, same keys in the same order; unfound = all zero; found = stateFlags 5.

WHICH KEY IS WHICH (names are joaat of lower-case strings; '#' = members of a numbered family whose prefix is not
cracked, grouped by inverting joaat over the numeric suffix)
  Unique (722 keys: 430 named, bddb04f2 + 3 probable magazines, 146 in the scan family, 142 unidentified)
    basketballhoop0..99 ..................... 100  hoops (hoops.py)
    pinkflamingoslocation001a..107a (+18) ... 125  COCAINE FLAMINGOS
    streetartaholtrashloc001..112 ........... 112  Ahol Street Art (no checklist line)
    collectiblemagazine<topic> x8 ............. 8  MAGAZINES (cars conspiracy fishing fitness guns prepper superrich
                                                   wealth) + bddb04f2 (unnamed, the A1 find) + 3 probable (f0fad292,
                                                   84c90081, 8bfd8fef: the other foreign-bucket keys; not written)
    collectiblelibrarybook001..007 ............ 7  BOOK SWAPS (the guide's 7, part of MAGAZINES, BOOKS & COMICS 30/34)
    watchblancgiroux001..012, watchcrowex001..013, watchnovak001..009
                                               34  LUXURY WATCHES (DISCOVERED STYLES); the 4 found styles are all
                                                   watches: crowex013 + blancgiroux005 (A1), crowex009 (A5),
                                                   blancgiroux003 (A5as)
    uniquelooktattoo001..017 ................. 17  MAGAZINE TATTOOS          (DISCOVERED STYLES)
    uniquelookmakeup001..008 + uniquelookhairstylefemale001..007
                                               15  LUCIA'S MAGAZINE STYLES   (DISCOVERED STYLES)
    uniquelookhairstylemale001..007 ........... 7  JASON'S MAGAZINE STYLES   (DISCOVERED STYLES; the guide counts 13,
                                                   so 6 Jason styles are still unidentified)
    wyman{kitcar,mamba,riata,transgressor,deviant}vehicle
                                                5  Wyman's cars (Ultimate Edition; no checklist line)
    # 73eb3813 + %03d 001..146 .............. 146  holds the UNDERWATER DISCOVERY #046 (found at A0, 2 min before the
                                                   Ocio doubloons); the rest is not split (see REASONS)
    142 others (48 in 15 small one-digit families, 94 un-numbered) .... not identified (the 5 playlist posters,
                                                   6 Jason styles and ~15 magazines, books and comics are among them
                                                   or in the scan family)
  Infinite (887 entries, 886 keys)
    480 keys without numeric suffix ......... 480  COLLECTIBLE CARDS
    golddoubloonlocation001..099 ............. 99  Gold Doubloons pickups (none found in these saves)
    # f69a5e42 + %d 0..3 ...................... 4  N.S. del Ocio doubloon pickups (3 found x foundCount 3 = 9 / 10)
    # d693c97f + %03d 001..303 .............. 303  not identified (bb37d528 = #269 is listed twice)

WHAT apply() WRITES
  magazines  (proven)  8 named + bddb04f2: (0, 0) -> (1, 5), the game's two examples (A0, A1).
  bookswaps  (EXPERIMENTAL, choice['experimental'] has 'bookswaps') collectiblelibrarybook001..007: (1, 5), the
             magazine shape; no book swap was ever read in these saves.
             Both raise totalprogressmade.booksandmagazines to pct32(line + newly found, 30). No counter exists.
  cards      (proven, needs choice['card_items'] == 'skip')  as in collectibles.py: (save time, 5, 1);
             numcollected.collectiblecards and .collectibles += n; soldsportscards = 100 when all 480 are found.
  watches    (proven, needs choice['watch_items'] == 'skip')  (save time, 5), the shape of all four game examples;
             numcollected.collectibles += n (A4 -> A5 12 -> 13, A5 -> A5as 13 -> 16 with two cards);
             totalprogressmade.styles = pct32(line + n, 70) (A4 -> A5 2.857143 -> 4.285715, A5 -> A5as -> 5.714286).
             The game also puts a watch garment in the finder's wardrobe (A5as: Jason, garment_s01_watchblancgiroux_
             mr1_001_001, catalog byte 0 -> 15; A5: Lucia, garment_s01_watchcrowex_fr1_002_001). The garment depends
             on the watch and on the character and is known for 2 of the 34 x 2 cases, so no garment is added.
  magazinestyles (EXPERIMENTAL, choice['experimental'] has 'magazinestyles')  the 39 uniquelook keys: (save time, 5)
             and the same two stats rows as watches. No magazine style was ever scanned in these saves: the timestamp
             convention is taken from the watches, and the store unlock the game text promises ('Scan certain
             magazines with WAiNK to unlock new styles at selected stores') is either derived from the entry or
             stored somewhere not identified.
  flamingos  (EXPERIMENTAL) as in collectibles.py: (save time, 5), no stats row.
  then checklist.refresh_overall(). Entries already found are kept; an entry in any other state is kept and logged.
  Column lengths never change; no other section is touched.

READ
  read() reports every category (entries, found, line value and percentage row, state, reason), the other groups
  (hoops, Ahol, Wyman, gold doubloons, the 303 family) and two readouts for the PS5 tests: other.scanFamily146.
  foundNumbers (which members of the scan family are found) and tables.unidentifiedFoundKeys (found entries
  outside every identified group).

REFUSED (error code -> why; REASONS has the full text)
  underwater split_unknown   the 33 discoveries share one numbered family of 146 keys with other scan targets; only
                             #046 is pinned and nothing in the save tells the others apart.
  waink      split_unknown   no WAiNK key is identified; probably in the same 146-key family.
  playlists  keys_unknown    the 5 posters (4 for The Sniper of La Perle, 1 for The Vault Radio) are not identified.
  kenton     completion_unknown  no set was ever completed; what the game records for a completed set is unknown
                             (the 1,000 test edit set fenced.doubloons = 1000 and the game's re-save A6c_as kept
                             soldkentontreasures at 0.0, so the sale counter alone does not complete a set).

RISK: medium for the proven writes (world pickups marked found stop spawning; card and watch items are not added),
high for the experimental ones. Keep the backup.
"""
import featurelib as fl
import checklist

FEATURE = 'collectibles'
SEC = 0xe4fcc5fa
SPAWN, SCRIPT_BLOCK = 0xec2a7ce9, '$0x24d043f2'           # ScriptInitialSpawn, ScriptSaveBlock
SPAWN_PATH = (SCRIPT_BLOCK, '$0xec2a7ce9', '$0x45a134ec', '$0xdee94c27', '$0xebeb1c7f')   # real save time (Unix s)
K_U, K_I = fl.key('UniqueCollectibles'), fl.key('InfiniteCollectibles')
K_KEYS, K_TIME, K_FLAGS, K_COUNT, K_X = (fl.key('keys'), fl.key('timestampsSec'), fl.key('stateFlags'),
                                         fl.key('foundCounts'), '$0x9607f9af')
COLS = {'U': (K_KEYS, K_TIME, K_FLAGS), 'I': (K_KEYS, K_TIME, K_FLAGS, K_COUNT, K_X)}
N_ENTRIES = {'U': 722, 'I': 887}
DONE = 5
TP = 'totalprogressmade'
NC = 'numcollected'
M32 = 0xffffffff


# ---------------------------------------------------------------------------------------------- joaat state helpers
def _step(h, c):
    h = (h + c) & M32
    h = (h + (h << 10)) & M32
    return h ^ (h >> 6)


def _fin(h):
    h = (h + (h << 3)) & M32
    h ^= h >> 11
    return (h + (h << 15)) & M32


def _from_state(state, suffix):
    """joaat of P + suffix given the internal joaat state of P (no finalisation)."""
    h = state
    for c in suffix.encode():
        h = _step(h, c)
    return _fin(h)


def _family(state, fmt, numbers):
    return [_from_state(state, fmt % n) for n in numbers]


# ---------------------------------------------------------------------------------------------- key sets
HOOPS = [fl.joaat('basketballhoop%d' % n) for n in range(100)]
AHOL = [fl.joaat('streetartaholtrashloc%03d' % n) for n in range(1, 113)]
FLAMINGO_SUFFIXES = (
    '001a 001b 001c 001d 002a 003a 004a 004b 004c 005a 006a 006b 007a 008a 009a 010a 011a 012a 013a 014a 015a 016a '
    '017a 018a 019a 020a 020b 021a 021b 022a 022b 022c 022d 023a 024a 025a 026a 026b 027a 027b 028a 028b 029a 030a '
    '031a 032a 033a 034a 035a 036a 037a 038a 039a 039b 040a 041a 041b 042a 043a 044a 045a 046a 047a 048a 049a 050a '
    '050b 051a 052a 052b 053a 054a 055a 056a 057a 058a 059a 060a 061a 062a 063a 064a 065a 066a 067a 068a 069a 070a '
    '071a 072a 073a 074a 075a 076a 077a 078a 079a 080a 081a 082a 083a 084a 085a 086a 087a 088a 089a 090a 091a 092a '
    '093a 094a 095a 096a 097a 098a 099a 100a 101a 102a 103a 104a 105a 106a 107a').split()
FLAMINGOS = {s: fl.joaat('pinkflamingoslocation' + s) for s in FLAMINGO_SUFFIXES}
# The game's document table lists exactly 11 '<Title> - Issue N' magazines; all 11 keys are collectiblemagazine<topic>
# (the last three cracked in round 16 against the three probable keys, 0 decoy hits: Manly Gaze, Pêche, ¡BOMBAZO!).
MAGAZINE_TOPICS = ('cars', 'conspiracy', 'fishing', 'fitness', 'guns', 'prepper', 'superrich', 'wealth',
                   'maleporno', 'femaleporno', 'spanishgossip')
MAGAZINES = {t: fl.joaat('collectiblemagazine' + t) for t in MAGAZINE_TOPICS}
MAGAZINE_UNNAMED = {'bddb04f2': 0xbddb04f2}               # the A1 find that moved the line 1 -> 2: a book or comic
MAGAZINE_PROBABLE = ()                                    # all three earlier 'probable' keys are named magazines now
BOOKSWAPS = {'%03d' % n: fl.joaat('collectiblelibrarybook%03d' % n) for n in range(1, 8)}
WATCH_BRANDS = (('blancgiroux', 12), ('crowex', 13), ('novak', 9))
WATCHES = {'%s%03d' % (b, n): fl.joaat('watch%s%03d' % (b, n)) for b, k in WATCH_BRANDS for n in range(1, k + 1)}
MAGSTYLE_GROUPS = (('tattoo', 17, 'Magazine Tattoos'), ('makeup', 8, "Lucia's Magazine Styles"),
                   ('hairstylefemale', 7, "Lucia's Magazine Styles"), ('hairstylemale', 7, "Jason's Magazine Styles"))
MAGSTYLES = {'%s%03d' % (g, n): fl.joaat('uniquelook%s%03d' % (g, n)) for g, k, _ in MAGSTYLE_GROUPS for n in range(1, k + 1)}
WYMAN = {c: fl.joaat('wyman%svehicle' % c) for c in ('kitcar', 'mamba', 'riata', 'transgressor', 'deviant')}
SCAN146 = _family(0x73eb3813, '%03d', range(1, 147))      # underwater discoveries + other scan targets (not split)
UNDERWATER_KNOWN = (0xe1551980,)                           # #046, found at A0 two minutes before the Ocio doubloons
DOUBLOONS_OCIO = _family(0xf69a5e42, '%d', range(0, 4))
GOLD_DOUBLOONS = [fl.joaat('golddoubloonlocation%03d' % n) for n in range(1, 100)]
INF303 = _family(0xd693c97f, '%03d', range(1, 304))
CARDS = [int(x, 16) for x in ''.join((
    '00f01fa2 02d39699 0343c784 048d7be0 049e23a3 050c218c 06c445b2 077e70f7 08c8f7c2 08fb3d65 092176f0 0a211716 ',
    '0ae56874 0b5e4e80 0c8425d7 0d803ab7 0da43565 0db76332 0de8779b 0ec8cc84 0f292365 0f489d54 1012f014 10154655 ',
    '106d0e1a 109d60e4 10f2c7c7 133604f0 137b77d0 13947c0a 1400ef20 1448d99e 14bd4f01 14ce6f2d 1510a096 153b7d71 ',
    '154ab3df 15b41cd5 15dd4bcb 165485f2 16d5af68 176224ac 189e765a 18c5df20 1901834a 192e1dd8 19d57817 1a078da5 ',
    '1b8aba5c 1be6ce57 1d4206b7 1d782bea 1db04e77 1ef84be7 1f241309 1f9efe8f 20440a6a 20736295 21224c7f 220e9418 ',
    '22364108 232a8d5d 23be296f 24d59d1c 24de9824 263f5855 2643e352 2703387e 2a1f8754 2a4de7b5 2a7ad729 2b088cfb ',
    '2b282f5d 2bf4af29 2d2fae79 2df1f57b 2e054e23 2e092ba0 2e58cad9 2e5df19d 2e76183b 2ea8a406 2ea8be21 2f888f16 ',
    '2f98ba8e 2fa55a7c 2fdd616b 2feda9f6 2ff95c91 2ffc0d8f 303b5db5 30545cfb 305ea4a2 30996ab4 30c0b846 31934269 ',
    '3271ab33 32e13752 32f3cd36 331a3317 33e24a63 340f43ae 341ce88d 34ddead6 351ae1d5 352aec78 36e3667a 36e8d5b3 ',
    '376eba26 3828bd3a 386388c3 386b274a 398583c2 39e106d7 39fb6a26 3b6d2154 3cb89cae 3dacd128 3df219a7 3f354d82 ',
    '3ff90023 3ffcccce 4050b116 407d7114 40dcd84c 41af7863 41d0bdf5 42343ab7 42eddfca 431072a0 435704f8 43b480e2 ',
    '43f750a4 4405a8d8 4459b221 445f338f 44dae8b3 453d6953 455a340e 45c614ed 46288c46 4657c20f 46a57460 46c45c76 ',
    '470093f0 4850c2f2 48941959 48f7bcd2 4ac7f0df 4af76a4f 4bccff6b 4c36ff68 4cb81f91 4ce552cf 4d01e51d 4d3f38a3 ',
    '4de89038 4e613e05 4ee46f64 4f1062af 4f602f8c 500f931f 50679dce 508153b4 50cdf5cf 50f1e1ad 5140ad28 514a3436 ',
    '514c6370 51f0c6dd 5300b78e 5419be28 55600f1e 56932e79 571f0c03 579de0e2 57bfd80f 57d4bf08 58309dfa 587acc34 ',
    '59c57d17 5b41c467 5bb7ec56 5bc358b9 5be3221a 5bfc8b0a 5c5ff1a6 5c8e41ce 5d52749e 5db33c04 5e5bc632 5eab2610 ',
    '5ecd5d10 5f09452e 5fa2c633 5fc2e954 603cd250 6107c6d0 61928faa 6203180e 620d0c57 627feb34 62a4557c 62afce89 ',
    '62c191a7 64ef2d07 6594783f 6659d2bf 66f11953 673ef516 6789b250 67dc8559 6940ca38 69818e68 6a66b4b9 6a80ceaf ',
    '6b661eaf 6b6f10f7 6b9ec648 6ba59690 6c608f07 6c6e29d4 6d5f84e8 6e1772d4 6f06a3da 6f1cd701 6fc07d27 7020e158 ',
    '708daff3 70aea6d9 71eaf1c2 721099cd 72ee9d8f 7324880e 7329b6ad 7341ab52 73d11232 74314490 7578d8bb 75e96e06 ',
    '763592f8 776dea32 77e5e66a 77f0b5cc 7818f724 78922e61 799ee75e 79a860b4 79c3abc4 7a2ad505 7bff2e99 7c92a41b ',
    '7d4b1705 7e7c2259 7f0a9519 7fb140e2 800d7c8a 814bde98 81c6da2c 8233cd45 828862ba 82e1fe79 830f3ee3 83c356b6 ',
    '841cceb8 855fa773 85ea4553 86b8fb8b 87046b41 87b4e7f1 88b7b6d9 89826a64 8997d8ce 8a0d4170 8a56e7a3 8b433016 ',
    '8c307541 8c87e1d5 8cffb5bf 8d7539a8 8dfec2d8 8e68a5d2 905b2dc8 90e341ef 912ad862 91de8e2a 9243f182 93b99652 ',
    '94169672 9780fc9d 97a50bc8 97c73a3b 9878a8d4 995a0d10 9a0d66b5 9a2458bb 9ac312b5 9b7e440b 9bbd9a9c 9c302718 ',
    '9c327f87 9d541504 9d8a7381 9da2089c 9e5de013 9e8c5f38 9ecc9b92 9f0d8320 9fea54ae a059e3de a12d802f a1397659 ',
    'a18a53f9 a267245f a31a4dd7 a36d8c59 a37bf492 a6eea6bc a7eefdc2 a8870043 a88eb28c a8f8a6b2 a90e42dc a9660de6 ',
    'a9f8ab84 aab63b7d aaf44d24 abdc90aa ac419293 ac7088f0 ad78c423 adcf3fc2 af16bad8 af4edfa8 afa41321 afa50449 ',
    'afc55da3 afd5868d b02cc92c b071fa32 b0eaa998 b1a147ee b20e375c b3760039 b3d1bde1 b4a5d204 b51c2cef b5484e80 ',
    'b59983a5 b60960ed b6e7969f b70f8a81 b7e92849 b95194d0 b994ccef ba057c5c badd9b00 baf7745a bb862ca0 bc824dfc ',
    'bd3486bd bdb9f6d0 bf3ea6e9 bfb94f95 bfd206fb bfdb61e1 c0172b83 c0216890 c12ca6ff c15610e6 c15aa621 c1b9a927 ',
    'c2116bb5 c30be253 c3f6e7a3 c4c45597 c4dde9b0 c573f8fd c6181e1e c6d35567 c6d47706 c6f36a5e c7e45d2f c8d653ae ',
    'c8ea9878 c9053093 c9564945 c95e17b4 c9d2ce29 ca34b660 ca690080 cbbb99ae cca8c342 cce23291 cd135d16 ce29e394 ',
    'ce5e68e1 cf7537e3 cfdb45fa d042a161 d0a624a5 d1c83399 d274f429 d2a4f27f d3a2f817 d41f1c72 d477ad69 d4fbc37a ',
    'd54d51bd d5b89747 d5badc22 d9558bac d98cf3c8 da4ef492 da632e8f dacfae14 db26cc1d dc287a59 dd120c4f dd3d61eb ',
    'dd6228aa ddb0cb10 ddb90a80 df3c54c5 dfdfbb20 e02065d5 e08f15a2 e1b971f4 e1d7e82f e1e95d20 e23e1294 e24d3dec ',
    'e2e8ad2e e31bef60 e33a6d7a e3f4df6e e49629b7 e5ee1416 e7937d92 e7e860ff e8031239 ea22b147 ea68dcf2 eabd9406 ',
    'ebd4f621 ec773775 ed13c814 eea3bcf7 eeb227a7 ef22a845 ef358d87 ef711b98 ef91f4b2 f0531458 f0a0ce00 f0c56036 ',
    'f10cc09c f114c845 f1d4484b f2cc2369 f4b78cdd f4d87bb4 f50a7b2f f55317af f6895f6b f694607c f69a5487 f86da63b ',
    'f8860e6b f9675d91 f96fde74 f9facab0 fa9daf56 fabee403 fb848249 fd33c453 fd41e095 ff358ccb ff938ecf fff7d795 ',
)).split()]   # the 480 InfiniteCollectibles keys with no numeric suffix

# category -> (checklist line key or None, state, refusal code or None)
CATEGORIES = (
    ('magazines', 'magazines', 'proven', None),
    ('bookswaps', 'magazines', 'experimental', 'unproven_format'),
    ('cards', 'cardsets', 'proven', None),
    ('watches', 'styles', 'proven', None),
    ('magazinestyles', 'styles', 'experimental', 'unproven_format'),
    ('flamingos', None, 'experimental', 'unproven_format'),
    ('underwater', 'underwater', 'refused', 'split_unknown'),
    ('waink', 'waink', 'refused', 'split_unknown'),
    ('playlists', None, 'refused', 'keys_unknown'),
    ('kenton', 'kenton', 'refused', 'completion_unknown'),
)
BY_CAT = {c[0]: c for c in CATEGORIES}
WRITABLE = ('magazines', 'cards', 'watches')               # what 'all' means
EXPERIMENTAL = ('bookswaps', 'magazinestyles', 'flamingos')
ALIASES = {'styles': ('watches', 'magazinestyles')}
REASONS = {
    'bookswaps': 'The 7 keys are cracked (collectiblelibrarybook001-007), but no book swap was ever read in these saves: '
                 'the (1, 5) shape is taken from the magazines. Experimental opt-in only.',
    'magazinestyles': 'The 39 keys are cracked (uniquelook<tattoo|makeup|hairstylefemale|hairstylemale>001-0NN), but no '
                      'magazine style was ever scanned in these saves: the (time, 5) shape is taken from the watches, and '
                      'whether the store unlock the game promises is kept anywhere else is unknown. Experimental opt-in only.',
    'flamingos': 'The 125 keys are cracked, but no flamingo was ever destroyed in these saves: the timestamp convention '
                 '(1 or real time) and the percentage row (66d7b9dd or 69ed6abb) are unknown. Experimental opt-in only.',
    'underwater': 'Only 1 of the 33 discoveries is pinned: #046 of a numbered family of 146 keys (prefix state 73eb3813), '
                  'found at A0 two minutes before the N.S. del Ocio doubloons. 146 is more than the 33 discoveries, so the '
                  'family also holds other scan targets (WAiNK locations, by count), and nothing in the save, the game '
                  'text or the archive names tells which numbers are discoveries. The prefix did not crack.',
    'waink': 'No WAiNK key is identified and the game never wrote a WAiNK scan in these saves. By count the 108 WAiNK '
             'locations (31 landmarks, 35 curiosities, 23 sculptures, 4 Peewees billboards, 15 No Flusher tags) fit in '
             'the same 146-key family as the underwater discoveries, but which numbers they are is unknown.',
    'playlists': 'The playlists need 5 scanned posters (4 for The Sniper of La Perle, 1 for The Vault Radio); none of '
                 'them is identified among the unnamed keys, no poster was ever scanned in these saves, and the '
                 'percentage row is one of two unnamed rows (66d7b9dd, 69ed6abb).',
    'kenton': 'No Kenton set was ever completed in these saves, so what the game records for a completed set is unknown. '
              'The line is totalprogressmade.soldkentontreasures (a sale: lifetimemoneyearned.soldkentontreasures, '
              '"Return <wreck> items to Kenton"); the doubloon sale counter is not it (the 1,000 test edit set '
              'fenced.doubloons = 1000 and the game re-saved with the line still 0.0). The 30 treasures of the other wrecks '
              'are inventory items never held in any save (catalog state 0), and only one wreck\'s pickups (the 4 N.S. del '
              'Ocio doubloon pickups, 9 of 10 doubloons) are identified.',
}
LINE_SETS = {'magazines': ('magazines', 'bookswaps'), 'styles': ('watches', 'magazinestyles')}
LINE_LABELS = {'magazines': 'Magazines, books & comics, part of 100% completion',
               'styles': 'Discovered styles, part of 100% completion'}


# ---------------------------------------------------------------------------------------------- table access
def _tables(t):
    """{'U'|'I': {'cols': {column key: (object start, [tokens])}, 'pos': {key: [positions]}}}; checks the layout."""
    root, _ = fl.walk(t, fl.CODE, fl.key(SEC))
    mem = {k: vs for k, vs, ve in fl.members(t, root)}
    out = {}
    for name, tk in (('U', K_U), ('I', K_I)):
        if tk not in mem:
            raise fl.FeatureError('layout_changed')
        cols = {}
        for k, cs, ce in fl.members(t, mem[tk]):
            if k in COLS[name]:
                cols[k] = (cs, fl.typed_values(t, cs)[1])
        if set(cols) != set(COLS[name]) or {len(v[1]) for v in cols.values()} != {N_ENTRIES[name]}:
            raise fl.FeatureError('layout_changed')
        pos = {}
        for i, x in enumerate(cols[K_KEYS][1]):
            pos.setdefault(int(x) & M32, []).append(i)
        out[name] = {'cols': cols, 'pos': pos}
    return out


def _entry(tabs, name, i):
    """(timestamp, flags[, foundCount, 0x9607f9af]) of entry i."""
    return tuple(int(tabs[name]['cols'][c][1][i]) for c in COLS[name][1:])


def _found(tabs, name, keys):
    """(found, other, missing) over keys: found = stateFlags 5, other = any other non-zero state."""
    f = o = m = 0
    for k in keys:
        ps = tabs[name]['pos'].get(k & M32)
        if not ps:
            m += 1
            continue
        e = _entry(tabs, name, ps[0])
        if e[1] == DONE:
            f += 1
        elif any(e):
            o += 1
    return f, o, m


def _save_time(s):
    t = s.text(SPAWN)
    a, e = fl.walk(t, *SPAWN_PATH)
    return int(t[a:e])


def _line(st, key):
    ln = checklist.BY_KEY[key]
    pct = st.value(TP, ln['qual'])
    return {'label': ln['label'], 'percent': pct, 'value': None if pct is None else int(round(pct * ln['of'] / 100.0)),
            'of': ln['of'], 'percentRow': 'totalprogressmade.%s' % (ln['qual'] if isinstance(ln['qual'], str) else fl.hexid(ln['qual']))}


def _unnamed_pct(st):
    return {'66d7b9dd': st.value(TP, 0x66d7b9dd), '69ed6abb': st.value(TP, 0x69ed6abb)}


# ---------------------------------------------------------------------------------------------- read
def _universe(cat):
    """{label: key} of the keys a category writes."""
    if cat == 'magazines':
        return dict(MAGAZINES, **MAGAZINE_UNNAMED)
    if cat == 'bookswaps':
        return dict(BOOKSWAPS)
    if cat == 'cards':
        return {fl.hexid(k): k for k in CARDS}
    if cat == 'watches':
        return dict(WATCHES)
    if cat == 'magazinestyles':
        return dict(MAGSTYLES)
    if cat == 'flamingos':
        return dict(FLAMINGOS)
    raise fl.FeatureError('unknown_category')


def _known_sets():
    u = (set(HOOPS) | set(AHOL) | set(FLAMINGOS.values()) | set(MAGAZINES.values()) | set(MAGAZINE_UNNAMED.values()) |
         set(MAGAZINE_PROBABLE) | set(BOOKSWAPS.values()) | set(WATCHES.values()) | set(MAGSTYLES.values()) |
         set(WYMAN.values()) | set(SCAN146))
    i = set(CARDS) | set(DOUBLOONS_OCIO) | set(GOLD_DOUBLOONS) | set(INF303)
    return u, i


def read(b):
    s = fl.Save(b)
    tabs = _tables(s.text(SEC))
    st = fl.Stats(s.text(fl.STATS))
    U, I = 'U', 'I'
    cats = []

    def cat(key, label, entries, found, line, extra=None):
        state = BY_CAT[key][2]
        d = {'key': key, 'label': label, 'entries': entries, 'found': found[0], 'otherState': found[1], 'missing': found[2],
             'line': line, 'state': state, 'reason': REASONS.get(key) if state != 'proven' else None}
        d.update(extra or {})
        cats.append(d)

    mags = list(MAGAZINES.values()) + list(MAGAZINE_UNNAMED.values())
    fm = _found(tabs, U, mags)
    fb = _found(tabs, U, BOOKSWAPS.values())
    cat('magazines', 'MAGAZINES, BOOKS & COMICS FOUND', len(mags), fm, _line(st, 'magazines'),
        {'named': {n: fl.hexid(k) for n, k in MAGAZINES.items()}, 'unnamed': sorted(MAGAZINE_UNNAMED),
         'probable': [fl.hexid(k) for k in MAGAZINE_PROBABLE], 'probableFound': _found(tabs, U, MAGAZINE_PROBABLE)[0],
         'gameTotal': 34, 'needed': 30, 'identified': len(mags) + len(BOOKSWAPS)})
    cat('bookswaps', 'MAGAZINES, BOOKS & COMICS FOUND (book swaps)', len(BOOKSWAPS), fb, _line(st, 'magazines'),
        {'names': 'collectiblelibrarybook001..007', 'gameTotal': 7})
    cf = _found(tabs, I, CARDS)
    counts = [_entry(tabs, I, tabs[I]['pos'][k][0])[2] for k in CARDS if k in tabs[I]['pos']]
    cat('cards', 'COLLECTIBLE CARD SETS FOUND', len(CARDS), cf, _line(st, 'cardsets'),
        {'foundCountSum': sum(counts), 'counter': st.value(NC, 'collectiblecards'),
         'counterMatches': st.value(NC, 'collectiblecards') == cf[0], 'sets': 18, 'needed': 15,
         'needs': "choice['card_items'] = 'skip' (card items are not added to the inventory)"})
    fw = _found(tabs, U, WATCHES.values())
    cat('watches', 'DISCOVERED STYLES (luxury watches)', len(WATCHES), fw, _line(st, 'styles'),
        {'brands': {b: _found(tabs, U, [v for n, v in WATCHES.items() if n[:-3] == b])[0] for b, _ in WATCH_BRANDS},
         'gameTotal': 34, 'needs': "choice['watch_items'] = 'skip' (watch garments are not added to the wardrobe)"})
    fs = _found(tabs, U, MAGSTYLES.values())
    cat('magazinestyles', 'DISCOVERED STYLES (magazine styles)', len(MAGSTYLES), fs, _line(st, 'styles'),
        {'groups': {g: _found(tabs, U, [v for n, v in MAGSTYLES.items() if n[:-3] == g])[0] for g, _, _ in MAGSTYLE_GROUPS},
         'gameTotal': 45, 'unidentified': 6, 'stylesLineNeeded': 70, 'stylesIdentified': len(WATCHES) + len(MAGSTYLES)})
    cat('flamingos', 'COCAINE FLAMINGOS DESTROYED', len(FLAMINGOS), _found(tabs, U, FLAMINGOS.values()),
        {'label': 'COCAINE FLAMINGOS DESTROYED', 'of': 100, 'percentRowCandidates': _unnamed_pct(st)},
        {'names': 'pinkflamingoslocation<NNN><a-d>', 'needed': 100})
    cat('underwater', 'UNDERWATER DISCOVERIES FOUND', 33, _found(tabs, U, UNDERWATER_KNOWN), _line(st, 'underwater'),
        {'identified': len(UNDERWATER_KNOWN), 'family146Found': _found(tabs, U, SCAN146)[0]})
    cat('waink', 'WAiNK LOCATIONS SCANNED', 108, (0, 0, 0), _line(st, 'waink'), {'identified': 0, 'needed': 100})
    cat('playlists', 'UNIQUE PLAYLISTS COMPLETED', 5, (0, 0, 0),
        {'label': 'UNIQUE PLAYLISTS COMPLETED', 'of': 2, 'percentRowCandidates': _unnamed_pct(st)},
        {'identified': 0, 'posters': {'The Sniper of La Perle': 4, 'The Vault Radio': 1}})
    dbl = [_entry(tabs, I, tabs[I]['pos'][k][0]) for k in DOUBLOONS_OCIO]
    cat('kenton', 'KENTON SETS COMPLETED', 7, (0, 0, 0), _line(st, 'kenton'),
        {'doubloonPickupsOcio': {'entries': 4, 'found': sum(1 for e in dbl if e[1] == DONE),
                                 'doubloons': sum(e[2] for e in dbl), 'of': 10}, 'needed': 5})
    gd = [_entry(tabs, I, tabs[I]['pos'][k][0]) for k in GOLD_DOUBLOONS]
    other = {
        'hoops': {'entries': 100, 'found': _found(tabs, U, HOOPS)[0], 'module': 'hoops'},
        'aholStreetArt': {'entries': 112, 'found': _found(tabs, U, AHOL)[0], 'checklistLine': None},
        'wymanCars': {'entries': 5, 'found': _found(tabs, U, WYMAN.values())[0], 'checklistLine': None},
        'scanFamily146': {'entries': 146, 'found': _found(tabs, U, SCAN146)[0],
                          'foundNumbers': [n for n, k in enumerate(SCAN146, 1) if _entry(tabs, U, tabs[U]['pos'][k][0])[1] == DONE]},
        'goldDoubloons': {'entries': 99, 'found': sum(1 for e in gd if e[1] == DONE), 'doubloons': sum(e[2] for e in gd)},
        'infinite303': {'entries': 303, 'found': _found(tabs, I, INF303)[0], 'listedTwice': 'bb37d528'},
    }
    known_u, known_i = _known_sets()
    unk_u = [k for k in tabs[U]['pos'] if k not in known_u]
    unk_i = [k for k in tabs[I]['pos'] if k not in known_i]
    found_unk_keys = [fl.hexid(k) for k in unk_u if _entry(tabs, U, tabs[U]['pos'][k][0]) != (0, 0)] + \
        [fl.hexid(k) for k in unk_i if any(_entry(tabs, I, tabs[I]['pos'][k][0]))]
    found_unk = len(found_unk_keys)
    styles_found = fw[0] + fs[0]
    return {'feature': FEATURE, 'saveTime': _save_time(s), 'categories': cats, 'other': other,
            'lines': {'magazines': {'identifiedFound': fm[0] + fb[0], 'line': _line(st, 'magazines')},
                      'styles': {'identifiedFound': styles_found, 'line': _line(st, 'styles')}},
            'tables': {'unique': N_ENTRIES['U'], 'infinite': N_ENTRIES['I'], 'infiniteKeys': len(tabs[I]['pos']),
                       'unidentifiedUnique': len(unk_u), 'unidentifiedInfinite': len(unk_i), 'unidentifiedFound': found_unk,
                       'unidentifiedFoundKeys': found_unk_keys},
            'possible': [c['key'] for c in cats if c['state'] == 'proven' and c['found'] < c['entries']],
            'risk': 'medium',
            'notes': ['Proven: magazines (9 of 34), cards (480), luxury watches (34; garments not added). Experimental: '
                      'book swaps (7), magazine styles (39), flamingos (125). Refused: underwater, WAiNK, playlists, Kenton.',
                      'DISCOVERED STYLES reaches 70 / 70 only with the watches and the experimental magazine styles (73 keys).',
                      'Marking pickups found may stop them spawning in the world; keep the backup.']}


# ---------------------------------------------------------------------------------------------- apply
def _select(sel, universe, code):
    """'all' or a list of names/hex ids -> [(label, key)] in a fixed order."""
    if sel == 'all':
        return list(universe.items())
    if isinstance(sel, str) or not isinstance(sel, (list, tuple)):
        raise fl.FeatureError('bad_request')
    by_hex = {fl.hexid(k): (n, k) for n, k in universe.items()}
    out = []
    for x in sel:
        x = str(x).lower()
        if x in universe:
            out.append((x, universe[x]))
        elif x.replace('0x', '') in by_hex:
            out.append(by_hex[x.replace('0x', '')])
        else:
            raise fl.FeatureError(code)
    return list(dict.fromkeys(out))


def _mark(tabs, name, keys, new, edits, log, what):
    """Entries of keys that are still all-zero get the column values in new ({column: int}); returns how many."""
    n = 0
    for label, k in keys:
        ps = tabs[name]['pos'].get(k & M32)
        if not ps:
            raise fl.FeatureError('layout_changed')
        for i in ps:
            cur = _entry(tabs, name, i)
            if cur[1] == DONE:
                continue
            if any(cur):
                log.append({'what': 'entry_kept', 'category': what, 'key': fl.hexid(k), 'value': list(cur)})
                continue
            if i in edits.get((name, K_FLAGS), {}):
                continue
            for col, v in new.items():
                edits.setdefault((name, col), {})[i] = b'%d' % v
            n += 1
    return n


def _write(t, tabs, edits):
    spans = []
    for (name, col), changes in edits.items():
        span, cur = fl.typed_values(t, tabs[name]['cols'][col][0])
        if span is None or len(cur) != N_ENTRIES[name]:
            raise fl.FeatureError('verify_failed')
        toks = list(cur)
        for i, tok in changes.items():
            toks[i] = tok
        spans.append((span, toks))
    for (a, e), toks in sorted(spans, key=lambda x: -x[0][0]):      # later spans first keep earlier offsets valid
        t = t[:a] + b','.join(toks) + t[e:]
    return t


def _categories(choice):
    cats = choice.get('categories', 'all')
    if cats == 'all':
        cats = list(WRITABLE)
    if isinstance(cats, str) or not isinstance(cats, (list, tuple)):
        raise fl.FeatureError('bad_request')
    out = []
    for c in cats:
        out.extend(ALIASES.get(c, (c,)))
    return list(dict.fromkeys(out))


SEL_CODES = {'magazines': 'unknown_magazine', 'bookswaps': 'unknown_bookswap', 'cards': 'unknown_card',
             'watches': 'unknown_watch', 'magazinestyles': 'unknown_style', 'flamingos': 'unknown_flamingo'}
SHAPES = {'magazines': ('U', 'one'), 'bookswaps': ('U', 'one'), 'cards': ('I', 'card'), 'watches': ('U', 'now'),
          'magazinestyles': ('U', 'now'), 'flamingos': ('U', 'now')}


def apply(b, choice=None):
    """choice: {'categories': 'all' | [category, ...],   'all' = magazines + cards + watches; 'styles' = watches +
                                                          magazinestyles
               'card_items': 'skip',                    required for cards (no card items are added)
               'watch_items': 'skip',                   required for watches (no watch garments are added)
               'experimental': ['bookswaps', 'magazinestyles', 'flamingos'],   required for those
               '<category>': 'all' | [name | hex, ...]} -> (new bytes, log).
    Refused categories raise their code (see REASONS)."""
    choice = choice or {}
    cats = _categories(choice)
    exp = set(choice.get('experimental') or ())
    for c in cats:
        if c not in BY_CAT:
            raise fl.FeatureError('unknown_category')
        if BY_CAT[c][2] == 'refused':
            raise fl.FeatureError(BY_CAT[c][3])
        if BY_CAT[c][2] == 'experimental' and c not in exp:
            raise fl.FeatureError('unproven_format')
    if 'cards' in cats and choice.get('card_items') != 'skip':
        raise fl.FeatureError('card_items_unknown')
    if 'watches' in cats and choice.get('watch_items') != 'skip':
        raise fl.FeatureError('watch_items_unknown')
    sels = {c: _select(choice.get(c, 'all'), _universe(c), SEL_CODES[c]) for c in cats}

    s = fl.Save(b)
    t = s.text(SEC)
    tabs = _tables(t)
    now = _save_time(s)
    st = fl.Stats(s.text(fl.STATS))
    edits, log, marked = {}, [], {}
    for c in cats:
        table, shape = SHAPES[c]
        if shape == 'one':
            new = {K_TIME: 1, K_FLAGS: DONE}
        elif shape == 'now':
            new = {K_TIME: now, K_FLAGS: DONE}
        else:
            new = {K_TIME: now, K_FLAGS: DONE, K_COUNT: 1}
        marked[c] = _mark(tabs, table, sels[c], new, edits, log, c)
        entry = [new[K_TIME], DONE] + ([1, 0] if table == 'I' else [])
        item = {'what': c, 'marked': marked[c], 'entry': entry}
        if BY_CAT[c][2] == 'experimental':
            item['experimental'] = True
        log.append(item)

    # stats: the two lines that have no counter follow the number of entries newly found
    for line, members in LINE_SETS.items():
        n = sum(marked.get(c, 0) for c in members)
        if n:
            ln = _line(st, line)
            if ln['percent'] is None:
                raise fl.FeatureError('layout_changed')
            st.set(TP, checklist.BY_KEY[line]['qual'], fl.pct32(ln['value'] + n, ln['of']), LINE_LABELS[line])
    n_coll = marked.get('cards', 0) + marked.get('watches', 0) + marked.get('magazinestyles', 0)
    if n_coll:
        cur = st.value(NC, 'collectibles')
        if cur is None:
            raise fl.FeatureError('layout_changed')
        st.set(NC, 'collectibles', cur + n_coll, 'numcollected.collectibles')
    if marked.get('cards'):
        cur = st.value(NC, 'collectiblecards')
        if cur is None:
            raise fl.FeatureError('layout_changed')
        st.set(NC, 'collectiblecards', cur + marked['cards'], 'numcollected.collectiblecards')
        left = [k for k in CARDS for i in tabs['I']['pos'][k]
                if _entry(tabs, 'I', i)[1] != DONE and i not in edits.get(('I', K_FLAGS), {})]
        if not left:
            st.set(TP, 'soldsportscards', fl.pct32(15, 15), 'Collectible card sets, part of 100% completion')
        else:
            log.append({'what': 'card_set_percent_unchanged', 'cardsStillUnfound': len(left)})
        log.append({'what': 'card_items_not_added', 'cards': marked['cards']})
    if marked.get('watches'):
        log.append({'what': 'watch_items_not_added', 'watches': marked['watches']})
    if marked.get('magazinestyles'):
        log.append({'what': 'store_unlocks_not_verified', 'styles': marked['magazinestyles']})
    if marked.get('flamingos') is not None:
        log.append({'what': 'flamingo_percent_not_written', 'note': 'percentage rows 66d7b9dd/69ed6abb not identified'})

    if edits:
        s.set_text(SEC, _write(t, tabs, edits))
    if checklist.refresh_overall(st) is None:
        raise fl.FeatureError('layout_changed')
    txt, slog = st.apply()
    if not edits and not slog:
        return b, []
    s.set_text(fl.STATS, txt)
    return s.build(), log + slog
