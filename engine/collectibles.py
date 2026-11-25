"""Collectibles of the 100% checklist: the two keyed tables of section e4fcc5fa (Save Garage feature module).

THE TABLES (section e4fcc5fa, CodeSaveBlock)
  UniqueCollectibles   0xbc515b02: keys 0x2c99b768 (int) / timestampsSec 0xa7cc5745 (int64) / stateFlags 0xcab27d5f (char)
  InfiniteCollectibles 0xa474d047: the same three columns + foundCounts 0x69e24cfe (int) + 0x9607f9af (int, 0 everywhere)
  * 722 and 887 entries in all 20 save copies, both playthroughs, with the same keys in the same order: every
    collectible has an entry from the start, an unfound one is (0, 0) / (0, 0, 0, 0). Nothing is ever appended.
  * The order is atMap order: 2053 buckets, key % 2053 ascending, except 11 Unique keys sitting in foreign buckets
    (8 of them crack as collectiblemagazine<topic>, see below). InfiniteCollectibles lists key bb37d528 twice.
  * Done = stateFlags 5. Every game-written change in playthrough A (5 intervals) is one of:
      Unique   (1, 5)          magazines (4b05caad at A0, bddb04f2 at A1) and the scored hoop 59 (A4 -> A5);
      Unique   (real time, 5)  styles (A1 x2, A5, A5as) and the underwater discovery e1551980 (A0);
      Infinite (real time, 5, foundCount 1, 0)  cards (A3 -> A4 one, A5 -> A5as two);
      Infinite (real time, 5, foundCount 3, 0)  three doubloon pickups (A0), 'DOUBLOONS FOUND 9 / 10'.
    Real times are Unix seconds, the same clock as ScriptInitialSpawn 0xebeb1c7f (real save time).
  * No other section holds any of the 1,608 keys (all sections scanned in decimal and hex); only the 100 hoop keys
    also appear, as stats qualifiers.

WHICH KEY IS WHICH (names are joaat of lower-case strings; families were found by inverting joaat over numeric
suffixes, which groups keys P+'001', P+'002' ... on the internal state of P without knowing P)
  Unique (722)
    basketballhoop0..99 ............................. 100  hoops (hoops.py)
    pinkflamingoslocation001a..107a (+18 b/c/d) ..... 125  COCAINE FLAMINGOS (public guides: 125, 100 needed)
    streetartaholtrashloc001..112 ................... 112  Ahol Street Art (archive photo_collectibles_..112)
    collectiblemagazine<topic> ...................... 8 named + 3 probable + bddb04f2 = MAGAZINES, BOOKS & COMICS
        cars conspiracy fishing fitness guns prepper superrich wealth; the 3 probable are the other foreign-bucket
        keys; bddb04f2 is unnamed but is the A1 find that moved the line 1 -> 2.
    state 73eb3813 + '%03d' 001..146 ................ 146  holds the underwater discovery (#046); probably also the
        other 32 UNDERWATER DISCOVERIES and the 112 WAiNK scans (31+35+23+23 in the guides) + 1, split unknown
    state ecd44954 / 7f3b71ce / 9187a71c + '%02d' ... 17 / 13 / 12  styles (the 4 found styles are #13, #09 of the
        13-family and #05, #03 of the 12-family; the watch garment Jason received at A5as came with #03)
    20 small one-digit families (86) and 99 other un-numbered keys ........ not identified
  Infinite (887 entries, 886 keys)
    480 keys with no numeric suffix ................. 480  COLLECTIBLE CARDS (18 sets / 480 cards in the guides;
        the 3 found cards are in it: e33a6d7a = General Surgeon - Pink, A3 -> A4; 31934269 and 351ae1d5 = Leroy
        Rook - Silver and Anthony Herndon - Silver, A5 -> A5as, the same intervals as the inventory items)
    state f69a5e42 + '0'..'3' ....................... 4    doubloon pickups of N.S. del Ocio (3 found x 3 = 9 / 10)
    state d693c97f + '%03d' 001..303 ................ 303  not identified (bb37d528 = #269 is listed twice)
    state 13b8eb2a + '%02d' 01..99 .................. 99   not identified

WHAT apply() WRITES (only for categories whose entries and write format are proven)
  magazines: each named magazine key (and bddb04f2) still (0, 0) -> (1, 5), exactly the game's two examples;
             totalprogressmade.booksandmagazines = pct32(line + newly found, 30). There is no counter.
  cards:     each card entry still (0, 0, 0) -> (save time, 5, 1), the game's three examples;
             numcollected.collectiblecards and numcollected.collectibles += cards newly found (the game did +1 per
             card: 0 -> 1 and 11 -> 12 at A3 -> A4, 1 -> 3 at A5 -> A5as);
             totalprogressmade.soldsportscards = 100.0 only when all 480 entries end up found (18 sets >= 15).
             Requires choice['card_items'] == 'skip': the game also puts each card item in Lucia's pocket slot
             (inventory 0, slot dfb35a06) and the key -> item mapping is known for 3 cards only, so no items are
             added; the per-county card challenge trackers are not touched either.
  flamingos: EXPERIMENTAL, only with choice['experimental'] = ['flamingos']: (save time, 5). No flamingo was ever
             destroyed in these saves, so the timestamp convention (1 or real time) is a guess, and which of the
             two unnamed percentages (66d7b9dd, 69ed6abb) is this line is unknown, so no stats row is written.
  then checklist.refresh_overall() recomputes the 100% figure. Entries already found are kept as they are; an entry
  in any other state is kept and logged. Column lengths never change.

REFUSED (error code -> why)
  styles     side_effects_unknown  a style also grants wardrobe items (the A5as watch) or store unlocks; 37 of
                                   the 79 keys are not identified.
  underwater keys_unknown          1 of 33 keys known; the other 32 hide among 145 keys shared with WAiNK.
  waink      keys_unknown          no WAiNK key identified and no game-written example.
  playlists  keys_unknown          no key identified, no example; its percentage row is not identified.
  kenton     completion_unknown    what completes a set is not in the save data: the row is soldkentontreasures and
                                   the text says 'Return <wreck> items to Kenton', so probably a sale to Kenton;
                                   only one wreck's 4 doubloon pickups are identified.

RISK: medium. Marking world pickups found can make them stop spawning, so keep the backup; PS5 behaviour of the
card line without the card items, and of the experimental flamingo write, is untested
(research_notes/checklist-collectibles.md has the test plan).
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
M32 = 0xffffffff


# ---------------------------------------------------------------- joaat state helpers
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


# ---------------------------------------------------------------- key sets
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
MAGAZINE_TOPICS = ('cars', 'conspiracy', 'fishing', 'fitness', 'guns', 'prepper', 'superrich', 'wealth')
MAGAZINES = {t: fl.joaat('collectiblemagazine' + t) for t in MAGAZINE_TOPICS}
MAGAZINE_UNNAMED = {'bddb04f2': 0xbddb04f2}               # the A1 find that moved the line 1 -> 2
MAGAZINE_PROBABLE = (0xf0fad292, 0x84c90081, 0x8bfd8fef)   # the other foreign-bucket keys: not written
SCAN146 = _family(0x73eb3813, '%03d', range(1, 147))      # underwater discoveries + (probably) WAiNK
UNDERWATER_KNOWN = (0xe1551980,)                           # #046, found at A0 two minutes before the doubloons
STYLE_FAMILIES = {'f17': _family(0xecd44954, '%02d', range(1, 18)), 'f13': _family(0x7f3b71ce, '%02d', range(1, 14)),
                  'f12': _family(0x9187a71c, '%02d', range(1, 13))}
DOUBLOONS_OCIO = _family(0xf69a5e42, '%d', range(0, 4))
INF303 = _family(0xd693c97f, '%03d', range(1, 304))
INF99 = _family(0x13b8eb2a, '%02d', range(1, 100))
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

# checklist line -> (checklist key, how this module treats it, refusal code or None)
CATEGORIES = (
    ('magazines', 'magazines', 'proven', None),
    ('cards', 'cardsets', 'proven', None),
    ('flamingos', None, 'experimental', 'unproven_format'),
    ('styles', 'styles', 'refused', 'side_effects_unknown'),
    ('underwater', 'underwater', 'refused', 'keys_unknown'),
    ('waink', 'waink', 'refused', 'keys_unknown'),
    ('playlists', None, 'refused', 'keys_unknown'),
    ('kenton', 'kenton', 'refused', 'completion_unknown'),
)
BY_CAT = {c[0]: c for c in CATEGORIES}
WRITABLE = ('magazines', 'cards')
EXPERIMENTAL = ('flamingos',)
REASONS = {
    'styles': "A style also grants wardrobe items (Jason's watch arrived with the A5as style) or store unlocks, which "
              'cannot be reproduced; 37 of the 79 style keys are not identified.',
    'underwater': 'Only 1 of the 33 keys is known (e1551980); the other 32 are among 145 keys of one family shared '
                  'with the WAiNK scans, and nothing in the save tells them apart.',
    'waink': 'No WAiNK key is identified (probably 112 of the 146-key family, which also holds the underwater '
             'discoveries) and no WAiNK scan was ever written by the game in these saves.',
    'playlists': 'No playlist flyer or poster key is identified, no example exists, and the percentage row is one of '
                 'two unnamed rows.',
    'kenton': 'What completes a Kenton set is not in the save data: the percentage row is soldkentontreasures, a money '
              'row lifetimemoneyearned.soldkentontreasures exists and the text says "Return <wreck> items to Kenton", '
              'so probably a sale to Kenton. Only one wreck\'s 4 doubloon pickups are identified.',
    'flamingos': 'The 125 keys are cracked, but no flamingo was ever destroyed in these saves: the timestamp convention '
                 '(1 or real time) and the percentage row (66d7b9dd or 69ed6abb) are unknown. Experimental opt-in only.',
}


# ---------------------------------------------------------------- table access
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


# ---------------------------------------------------------------- read
def read(b):
    s = fl.Save(b)
    tabs = _tables(s.text(SEC))
    st = fl.Stats(s.text(fl.STATS))
    U, I = 'U', 'I'
    cats = []

    def cat(key, label, entries, found, line, state, extra=None):
        d = {'key': key, 'label': label, 'entries': entries, 'found': found[0], 'otherState': found[1], 'missing': found[2],
             'line': line, 'state': state, 'reason': REASONS.get(key) if state != 'proven' else None}
        d.update(extra or {})
        cats.append(d)

    mags = list(MAGAZINES.values()) + list(MAGAZINE_UNNAMED.values())
    cat('magazines', 'MAGAZINES, BOOKS & COMICS FOUND', len(mags), _found(tabs, U, mags), _line(st, 'magazines'), 'proven',
        {'named': {n: fl.hexid(k) for n, k in MAGAZINES.items()}, 'probable': [fl.hexid(k) for k in MAGAZINE_PROBABLE],
         'probableFound': _found(tabs, U, MAGAZINE_PROBABLE)[0], 'gameTotal': 34, 'needed': 30,
         'writableNow': len(mags) - _found(tabs, U, mags)[0]})
    cf = _found(tabs, I, CARDS)
    counts = [_entry(tabs, I, tabs[I]['pos'][k][0])[2] for k in CARDS if k in tabs[I]['pos']]
    cat('cards', 'COLLECTIBLE CARD SETS FOUND', len(CARDS), cf, _line(st, 'cardsets'), 'proven',
        {'foundCountSum': sum(counts), 'counter': st.value('numcollected', 'collectiblecards'),
         'counterMatches': st.value('numcollected', 'collectiblecards') == cf[0], 'sets': 18, 'needed': 15,
         'needs': "choice['card_items'] = 'skip' (card items are not added to the inventory)"})
    cat('flamingos', 'COCAINE FLAMINGOS DESTROYED', len(FLAMINGOS), _found(tabs, U, FLAMINGOS.values()),
        {'label': 'COCAINE FLAMINGOS DESTROYED', 'of': 100, 'percentRowCandidates':
         {'66d7b9dd': st.value(TP, 0x66d7b9dd), '69ed6abb': st.value(TP, 0x69ed6abb)}}, 'experimental',
        {'names': 'pinkflamingoslocation<NNN><a-d>', 'needed': 100})
    sk = [k for v in STYLE_FAMILIES.values() for k in v]
    cat('styles', 'DISCOVERED STYLES', 79, _found(tabs, U, sk), _line(st, 'styles'), 'refused',
        {'identified': len(sk), 'families': {n: _found(tabs, U, v)[0] for n, v in STYLE_FAMILIES.items()}})
    cat('underwater', 'UNDERWATER DISCOVERIES FOUND', 33, _found(tabs, U, UNDERWATER_KNOWN), _line(st, 'underwater'),
        'refused', {'identified': len(UNDERWATER_KNOWN), 'family146Found': _found(tabs, U, SCAN146)[0]})
    cat('waink', 'WAiNK LOCATIONS SCANNED', 112, (0, 0, 0), _line(st, 'waink'), 'refused', {'identified': 0})
    cat('playlists', 'UNIQUE PLAYLISTS COMPLETED', None, (0, 0, 0),
        {'label': 'UNIQUE PLAYLISTS COMPLETED', 'of': 2, 'percentRowCandidates':
         {'66d7b9dd': st.value(TP, 0x66d7b9dd), '69ed6abb': st.value(TP, 0x69ed6abb)}}, 'refused', {'identified': 0})
    dbl = [_entry(tabs, I, tabs[I]['pos'][k][0]) for k in DOUBLOONS_OCIO]
    cat('kenton', 'KENTON SETS COMPLETED', 7, (0, 0, 0), _line(st, 'kenton'), 'refused',
        {'doubloonPickupsOcio': {'entries': 4, 'found': sum(1 for e in dbl if e[1] == DONE),
                                 'doubloons': sum(e[2] for e in dbl)}, 'needed': 5})
    other = {
        'hoops': {'entries': 100, 'found': _found(tabs, U, HOOPS)[0], 'module': 'hoops'},
        'aholStreetArt': {'entries': 112, 'found': _found(tabs, U, AHOL)[0], 'checklistLine': None},
        'scanFamily146': {'entries': 146, 'found': _found(tabs, U, SCAN146)[0]},
        'infinite303': {'entries': 303, 'found': _found(tabs, I, INF303)[0], 'listedTwice': 'bb37d528'},
        'infinite99': {'entries': 99, 'found': _found(tabs, I, INF99)[0]},
    }
    known_u = set(HOOPS) | set(AHOL) | set(FLAMINGOS.values()) | set(mags) | set(MAGAZINE_PROBABLE) | set(SCAN146) | set(sk)
    known_i = set(CARDS) | set(DOUBLOONS_OCIO) | set(INF303) | set(INF99)
    unk_u = [k for k in tabs[U]['pos'] if k not in known_u]
    unk_i = [k for k in tabs[I]['pos'] if k not in known_i]
    found_unk = sum(1 for k in unk_u if _entry(tabs, U, tabs[U]['pos'][k][0]) != (0, 0)) + \
        sum(1 for k in unk_i if any(_entry(tabs, I, tabs[I]['pos'][k][0])))
    return {'feature': FEATURE, 'saveTime': _save_time(s), 'categories': cats, 'other': other,
            'tables': {'unique': N_ENTRIES['U'], 'infinite': N_ENTRIES['I'], 'infiniteKeys': len(tabs[I]['pos']),
                       'unidentifiedUnique': len(unk_u), 'unidentifiedInfinite': len(unk_i), 'unidentifiedFound': found_unk},
            'possible': [c['key'] for c in cats if c['state'] == 'proven' and c['found'] < c['entries']],
            'risk': 'medium',
            'notes': ['Proven: magazines (9 identified of 34) and cards (all 480). Flamingos: keys known, write format '
                      'unproven (experimental opt-in). Styles, underwater, WAiNK, playlists and Kenton are refused.',
                      'Marking pickups found may stop them spawning in the world; keep the backup.']}


# ---------------------------------------------------------------- apply
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


def apply(b, choice=None):
    """choice: {'categories': 'all' | ['magazines', 'cards', 'flamingos'], 'card_items': 'skip',
               'experimental': ['flamingos'], 'magazines': 'all' | [topic | hex], 'cards': 'all' | [hex],
               'flamingos': 'all' | ['001a', ...]} -> (new bytes, log).
    'all' means every proven category (magazines, cards). Refused categories raise their code (see REASONS)."""
    choice = choice or {}
    cats = choice.get('categories', 'all')
    if cats == 'all':
        cats = list(WRITABLE)
    if isinstance(cats, str) or not isinstance(cats, (list, tuple)):
        raise fl.FeatureError('bad_request')
    cats = list(dict.fromkeys(cats))
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

    s = fl.Save(b)
    t = s.text(SEC)
    tabs = _tables(t)
    now = _save_time(s)
    st = fl.Stats(s.text(fl.STATS))
    edits, log = {}, []

    if 'magazines' in cats:
        sel = _select(choice.get('magazines', 'all'), dict(MAGAZINES, **MAGAZINE_UNNAMED), 'unknown_magazine')
        n = _mark(tabs, 'U', sel, {K_TIME: 1, K_FLAGS: DONE}, edits, log, 'magazines')
        if n:
            ln = _line(st, 'magazines')
            if ln['percent'] is None:
                raise fl.FeatureError('layout_changed')
            st.set(TP, 'booksandmagazines', fl.pct32(ln['value'] + n, ln['of']), 'Magazines, books & comics, part of 100% completion')
        log.append({'what': 'magazines', 'marked': n, 'entry': [1, DONE]})

    if 'cards' in cats:
        universe = {fl.hexid(k): k for k in CARDS}
        sel = _select(choice.get('cards', 'all'), universe, 'unknown_card')
        n = _mark(tabs, 'I', sel, {K_TIME: now, K_FLAGS: DONE, K_COUNT: 1}, edits, log, 'cards')
        if n:
            for q in ('collectiblecards', 'collectibles'):
                cur = st.value('numcollected', q)
                if cur is None:
                    raise fl.FeatureError('layout_changed')
                st.set('numcollected', q, cur + n, 'numcollected.%s' % q)
            left = [k for k in CARDS for i in tabs['I']['pos'][k]
                    if _entry(tabs, 'I', i)[1] != DONE and i not in edits.get(('I', K_FLAGS), {})]
            if not left:
                st.set(TP, 'soldsportscards', fl.pct32(15, 15), 'Collectible card sets, part of 100% completion')
            else:
                log.append({'what': 'card_set_percent_unchanged', 'cardsStillUnfound': len(left)})
        log.append({'what': 'cards', 'marked': n, 'entry': [now, DONE, 1, 0]})
        if n:
            log.append({'what': 'card_items_not_added', 'cards': n})

    if 'flamingos' in cats:
        sel = _select(choice.get('flamingos', 'all'), FLAMINGOS, 'unknown_flamingo')
        n = _mark(tabs, 'U', sel, {K_TIME: now, K_FLAGS: DONE}, edits, log, 'flamingos')
        log.append({'what': 'flamingos_experimental', 'marked': n, 'entry': [now, DONE],
                    'note': 'unproven timestamp convention; percentage rows 66d7b9dd/69ed6abb not written'})

    if edits:
        s.set_text(SEC, _write(t, tabs, edits))
    if checklist.refresh_overall(st) is None:
        raise fl.FeatureError('layout_changed')
    txt, slog = st.apply()
    if not edits and not slog:
        return b, []
    s.set_text(fl.STATS, txt)
    return s.build(), log + slog
