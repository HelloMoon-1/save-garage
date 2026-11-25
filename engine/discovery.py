"""Discover every location of a map category (Save Garage feature module).

WHAT IT CHANGES (section 940e954d Discovery only)
  Discovery = {Discovered: [names], 0x713b0597: [records], LegacyDiscovered, FlagState, DiscoveryOrder, bool}.
  A record is {Name, Hash, Discovered: {"$bits": N, "$content": "int_array", "$data": ["0x........", ...]}}, one bit
  per location of the category (LSB first within each 32-bit word, written as upper-case hex).
  * mode 'move' (default, what the game does): the category's record is removed from 0x713b0597 and its Name is
    appended to Discovered as {"$data":"0x%08x"}. A category with no record yet ('not started') just gets its Name
    appended to Discovered, the same end state.
  * mode 'bits': bits 0..N-1 of the record are set and the record stays (words full, the last one masked, so bits
    at or above $bits stay clear). The game never leaves a full record in a save, so 'move' is the default.
  FlagState (per-location state), DiscoveryOrder (recent list), FogOfWar and stats are not touched.

EVIDENCE FROM THE SAVES
  * Across 15 game-written saves no record is ever full, and every record that disappeared between two saves was in
    Discovered in the later save: 23/23 (A0->A1), 4/4, 1/1, 1/1, 8/8 (A4->A5). Records keep their $bits and Hash.
  * Discovered is not kept in insertion order (new names appear at any position), so the game treats it as a set;
    appending at the end is safe for it to re-order on its next save.
  * Bit padding: in every record the bits at or above $bits are clear and the word count is ceil($bits / 32).
  * Categories are named by joaat of venue words (bar, deli, kiosk, gasstation, payandspray, ...: 28 'place'
    names cracked from a 258k-word vocabulary built from known names and game text).

BLOCKED (never edited)
  * 'stunt' categories (130 stunt jumps, 202 under-the-bridge, 40 knife flights, 25 base jumps): their popcount
    equals stats numfound.<stunt type> in every save, so they belong to the stunt feature (per-stunt 'found' rows).
  * 'gang' categories (Kingfishers, San4San, Final Chapter, La Polilla Negra, Kolt & Associates, two unnamed gangs,
    Other criminals, Fronts): their popcount equals stats ganglocationsdiscovered.<gang> (the screen's 'OPERATIONS
    DISCOVERED 2 / 3' for Kingfishers); gang operations are out of scope.
  * 'unknown' categories (31 unnamed or weakly named) are only edited with choice['allow_unknown'] = True; some
    small ones could be gang or story related.

LIMITS / UNCERTAIN
  * Map blips and per-location FlagState entries are separate; the game may add FlagState entries as you visit.
  * No stat mirrors were found for 'place' categories (SHOPS DISCOVERED on the stats screen is not a stats row and
    is not reproduced from these bits; it is probably computed by the menu).
  * Category sizes ($bits) for 'not started' categories come from other saves of this console (stable per Name).

RISK: medium for 'place' categories (same end state the game writes), high for 'unknown'.
"""
import featurelib as fl

FEATURE = 'discovery'
SEC = 0x940e954d
K_DISCOVERED, K_RECORDS = fl.key('Discovered'), '$0x713b0597'
K_NAME, K_HASH, K_BITS = fl.key('Name'), fl.key('Hash'), fl.key('Discovered')

# name hash: (name or None, $bits, label or None, kind). Sizes from records seen in this console's saves.
CATEGORIES = {
    0x2cddda1c: (None, 287, None, 'unknown'),
    0x0f25b442: (None, 202, 'Under the bridge', 'stunt'),
    0xc5c374dc: (None, 188, None, 'unknown'),
    0xfab2dbe2: (None, 168, None, 'unknown'),
    0x07b59c95: (None, 130, 'Stunt jumps', 'stunt'),
    0x5a5d0eac: (None, 127, None, 'unknown'),
    0xa452f0bf: (None, 122, None, 'unknown'),
    0x200384af: (None, 99, None, 'unknown'),
    0x359a0e32: ('deli', 79, 'Delis', 'place'),
    0xfcc7049b: ('kiosk', 78, 'Kiosks', 'place'),
    0xe4c5d48d: (None, 75, 'Ambient bars? (barambient, unconfirmed)', 'unknown'),
    0x0a1d2e2d: ('convenience', 70, 'Convenience stores', 'place'),
    0x6a0bf12f: ('gasstation', 57, 'Gas stations', 'place'),
    0x7cb6fc16: (None, 49, None, 'unknown'),
    0x71e580f6: (None, 48, None, 'unknown'),
    0x96ea6837: (None, 46, None, 'unknown'),
    0xaa91f7c1: ('foodtruck', 45, 'Food trucks', 'place'),
    0xc8c1866f: (None, 40, 'Knife flights', 'stunt'),
    0x19b39fbd: ('counter', 37, 'Food counters', 'place'),
    0x80409109: ('bar', 37, 'Bars', 'place'),
    0x55862f48: (None, 35, None, 'unknown'),
    0x453c1e7c: (None, 25, None, 'unknown'),
    0xec841e35: (None, 25, 'Base jumps', 'stunt'),
    0x3a15db98: ('bank', 22, 'Banks', 'place'),
    0xd85c6e4d: ('jewelry', 20, 'Jewelry stores', 'place'),
    0x3da6786c: ('payandspray', 19, "Pay 'n' Spray", 'place'),
    0xb68e74bd: ('shoe', 17, 'Shoe stores', 'place'),
    0xc2286f01: ('clothing', 17, 'Clothing stores', 'place'),
    0x8c1a765c: ('drivethru', 16, 'Drive-thrus', 'place'),
    0xe69efb52: ('fastfooddrivethru', 16, 'Fast food drive-thrus', 'place'),
    0x049177fe: ('electronics', 14, 'Electronics stores', 'place'),
    0xf2d189b2: ('liquor', 14, 'Liquor stores', 'place'),
    0x6ddc7642: ('souvenir', 13, 'Souvenir shops', 'place'),
    0xae8a0040: ('pawn', 13, 'Pawn shops', 'place'),
    0x43d760cb: ('tattoo', 11, 'Tattoo parlors', 'place'),
    0x10710633: ('othercriminals', 10, 'Other criminals', 'gang'),
    0x286fa610: (None, 10, None, 'unknown'),
    0x047430ea: ('gym', 9, 'Gyms', 'place'),
    0xbe77c0fd: (None, 9, None, 'unknown'),
    0x49729722: (None, 8, None, 'unknown'),
    0xb8650d01: ('loan', 7, 'Loan stores', 'place'),
    0x48d6f312: (None, 6, None, 'unknown'),
    0x51029d88: ('pawnweapon', 6, 'Pawn shops (weapons)', 'place'),
    0x78f795d4: (None, 6, None, 'unknown'),
    0x83444fce: (None, 6, None, 'unknown'),
    0x9978380b: ('carwash', 6, 'Car washes', 'place'),
    0x15ec0179: ('koltandassociates', 5, 'Kolt & Associates', 'gang'),
    0x908033a2: (None, 5, 'Barbers and makeup? (barbermakeup, unconfirmed)', 'unknown'),
    0x973f529a: ('barber', 5, 'Barbers', 'place'),
    0xa3855b81: ('fastfood', 5, 'Fast food restaurants', 'place'),
    0xd3044985: ('fronts', 5, 'Fronts', 'gang'),
    0xdd94c23e: (None, 5, None, 'unknown'),
    0x018c64b6: (None, 4, None, 'unknown'),
    0x20cee0c9: (None, 4, 'Faux shops? (fauxshops, unconfirmed)', 'unknown'),
    0x3a6b47cb: ('finalchapter', 4, 'Final Chapter', 'gang'),
    0x4bb8431d: ('san4san', 4, 'San4San', 'gang'),
    0x809630e3: (None, 4, None, 'unknown'),
    0xf2011a8f: (None, 4, None, 'unknown'),
    0x0f9c45d3: (None, 3, 'Gang 0f9c45d3', 'gang'),
    0x7f850cc4: ('kingfishers', 3, 'Kingfishers', 'gang'),
    0x0869eb84: ('lapolillanegra', 2, 'La Polilla Negra', 'gang'),
    0x741cf5a0: (None, 2, None, 'unknown'),
    0x8515596a: ('nightclub', 2, 'Nightclubs', 'place'),
    0x9386ea4c: (None, 2, 'Gang 9386ea4c', 'gang'),
    0x96da0717: (None, 2, None, 'unknown'),
    0xc5a7de66: (None, 2, None, 'unknown'),
    0xce2c423e: ('bargainstore', 2, 'Bargain stores', 'place'),
    0xff992f08: ('shootingrange', 2, 'Shooting ranges', 'place'),
}
BLOCKED = {'stunt': 'linked to the per-stunt stats; use the stunts feature', 'gang': 'gang operations are not edited'}


def _label(hh, n):
    meta = CATEGORIES.get(hh)
    if meta and meta[2]:
        return meta[2]
    return 'Category %08x (%d locations)' % (hh, n) if n else 'Category %08x' % hh


def full_words(bits):
    words = ['0xFFFFFFFF'] * (bits // 32)
    if bits % 32:
        words.append('0x%08X' % ((1 << (bits % 32)) - 1))
    return words


def _state(t):
    """-> (discovered names in order, {name: record info})"""
    root, _ = fl.walk(t, fl.CODE, fl.key(SEC))
    mem = {k: (vs, ve) for k, vs, ve in fl.members(t, root)}
    ds, _ = mem[K_DISCOVERED]
    names = []
    for s, e in fl.elements(t, ds):
        obj = dict((k, (vs, ve)) for k, vs, ve in fl.members(t, s))
        vs, ve = obj['$data']
        names.append(int(t[vs + 1:ve - 1], 16) & fl.M32)
    rs, _ = mem[K_RECORDS]
    recs = {}
    for i, (s, e) in enumerate(fl.elements(t, rs)):
        obj = {k: (vs, ve) for k, vs, ve in fl.members(t, s)}
        vs, ve = obj[K_NAME]
        name_obj = {k: (a, z) for k, a, z in fl.members(t, vs)}
        a, z = name_obj['$data']
        hh = int(t[a + 1:z - 1], 16) & fl.M32
        bs, be = obj[K_BITS]
        bobj = {k: (a, z) for k, a, z in fl.members(t, bs)}
        n = int(t[bobj['$bits'][0]:bobj['$bits'][1]])
        span, words = fl.typed_values(t, bs)
        w = [int(x.strip(b'"'), 16) for x in words]
        recs[hh] = {'index': i, 'bits': n, 'words': w, 'found': sum(bin(x).count('1') for x in w), 'span': (s, e), 'bits_obj': bs}
    return names, recs


def read(b):
    t = fl.Save(b).text(SEC)
    names, recs = _state(t)
    done = set(names)
    cats = []
    seen = set()
    for hh, r in sorted(recs.items(), key=lambda x: -x[1]['bits']):
        meta = CATEGORIES.get(hh, (None, r['bits'], None, 'unknown'))
        cats.append({'id': fl.hexid(hh), 'name': meta[0], 'label': _label(hh, r['bits']), 'kind': meta[3], 'locations': r['bits'],
                     'found': r['found'], 'state': 'partial', 'editable': meta[3] in ('place', 'unknown'),
                     'blocked': BLOCKED.get(meta[3]), 'padOk': len(r['words']) == (r['bits'] + 31) // 32 and
                     (r['bits'] % 32 == 0 or r['words'][-1] >> (r['bits'] % 32) == 0)})
        seen.add(hh)
    for hh, meta in sorted(CATEGORIES.items(), key=lambda x: -x[1][1]):
        if hh in seen:
            continue
        state = 'complete' if hh in done else 'not_started'
        cats.append({'id': fl.hexid(hh), 'name': meta[0], 'label': _label(hh, meta[1]), 'kind': meta[3], 'locations': meta[1],
                     'found': meta[1] if state == 'complete' else 0, 'state': state, 'editable': meta[3] in ('place', 'unknown'),
                     'blocked': BLOCKED.get(meta[3])})
    other = [n for n in names if n not in CATEGORIES]
    return {'feature': FEATURE, 'categories': cats,
            'counts': {'complete': sum(1 for c in cats if c['state'] == 'complete'), 'partial': sum(1 for c in cats if c['state'] == 'partial'),
                       'notStarted': sum(1 for c in cats if c['state'] == 'not_started')},
            'possible': [c['id'] for c in cats if c['state'] != 'complete' and c['kind'] == 'place'],
            'otherDiscovered': len(other), 'risk': 'medium',
            'notes': ["Completing a category marks all of its map locations discovered, the way the game records a finished category.",
                      'Stunt and gang categories are shown but never edited.',
                      'Unnamed categories need allow_unknown.']}


def _resolve(c):
    if isinstance(c, int):
        return c & fl.M32
    if isinstance(c, str):
        for hh, meta in CATEGORIES.items():
            if meta[0] == c:
                return hh
        hexdigits = c[2:] if c.lower().startswith('0x') else c
        if (c.lower().startswith('0x') or len(c) == 8) and hexdigits and all(ch in '0123456789abcdef' for ch in hexdigits.lower()):
            return int(hexdigits, 16) & fl.M32
        return fl.joaat(c)
    raise fl.FeatureError('bad_request')


def apply(b, choice):
    """choice: {'categories': 'all' | [name / hex id / int], 'mode': 'move' | 'bits', 'allow_unknown': False,
    'include_not_started': True} -> (new bytes, log). 'all' means every 'place' category (plus 'unknown' ones when
    allow_unknown is set)."""
    choice = choice or {}
    mode = choice.get('mode', 'move')
    if mode not in ('move', 'bits'):
        raise fl.FeatureError('bad_request')
    allow_unknown = bool(choice.get('allow_unknown'))
    s = fl.Save(b)
    t = s.text(SEC)
    names, recs = _state(t)
    want = choice.get('categories', 'all')
    if want == 'all':
        ids = [hh for hh, meta in CATEGORIES.items() if meta[3] == 'place' or (allow_unknown and meta[3] == 'unknown')]
        ids += [hh for hh in recs if hh not in CATEGORIES and allow_unknown]
    else:
        ids = []
        for c in want:
            hh = _resolve(c)
            kind = CATEGORIES.get(hh, (None, 0, None, 'unknown'))[3]
            if kind in BLOCKED and not (kind == 'stunt' and choice.get('allow_stunt')):
                raise fl.FeatureError('blocked_' + kind)
            if kind == 'unknown' and not allow_unknown:
                raise fl.FeatureError('unknown_category')
            ids.append(hh)
    include_new = choice.get('include_not_started', True)
    done = set(names)
    log, to_move, to_fill, to_add = [], [], [], []
    for hh in dict.fromkeys(ids):
        if hh in done:
            continue
        if hh in recs:
            if mode == 'move':
                to_move.append(hh)
            elif recs[hh]['found'] < recs[hh]['bits']:
                to_fill.append(hh)
        elif include_new and hh in CATEGORIES:
            to_add.append(hh)
    if not (to_move or to_fill or to_add):
        return b, log
    # 1) fill bitsets (same-length tokens per word count, so do them one by one from the end of the text)
    for hh in sorted(to_fill, key=lambda x: -recs[x]['span'][0]):
        r = recs[hh]
        span, words = fl.typed_values(t, r['bits_obj'])
        new = full_words(r['bits'])
        if len(new) != len(words):
            raise fl.FeatureError('layout_changed')
        t = t[:span[0]] + b','.join(b'"%s"' % w.encode() for w in new) + t[span[1]:]
        log.append({'what': 'discovery_bits', 'category': fl.hexid(hh), 'label': _label(hh, r['bits']), 'from': r['found'], 'to': r['bits']})
    # 2) remove moved records, last first so earlier offsets stay valid
    if to_move:
        root, _ = fl.walk(t, fl.CODE, fl.key(SEC))
        rs, re_ = fl.member(t, root, K_RECORDS)
        els = fl.elements(t, rs)
        drop = sorted((recs[hh]['index'] for hh in to_move), reverse=True)
        keep = [i for i in range(len(els)) if i not in set(drop)]
        new_list = b'[' + b','.join(t[els[i][0]:els[i][1]] for i in keep) + b']'
        t = t[:rs] + new_list + t[re_:]
        for hh in to_move:
            log.append({'what': 'discovery_move', 'category': fl.hexid(hh), 'label': _label(hh, recs[hh]['bits']),
                        'from': recs[hh]['found'], 'to': recs[hh]['bits']})
    # 3) append names to Discovered
    add = to_move + to_add
    if add:
        root, _ = fl.walk(t, fl.CODE, fl.key(SEC))
        ds, de = fl.member(t, root, K_DISCOVERED)
        toks = b','.join(b'{"$data":"0x%08x"}' % hh for hh in add)
        t = t[:de - 1] + (b',' if de - ds > 2 else b'') + toks + t[de - 1:]
        for hh in to_add:
            log.append({'what': 'discovery_add', 'category': fl.hexid(hh), 'label': _label(hh, CATEGORIES[hh][1]), 'to': CATEGORIES[hh][1]})
    s.set_text(SEC, t)
    return s.build(), log
