# Save Garage - Copyright (C) 2026 NotHGM - GNU GPL v3 with the additional terms in NOTICE; see LICENSE.
"""Fenced-goods lines of the 100% checklist: NARCOTICS FENCED $x / $100,000, JEWELRY FENCED $x / $100,000,
MARKED BILLS FENCED $x / $250,000 and VEHICLES FENCED $x / $200,000 (Save Garage feature module).

WHERE THE GAME KEEPS IT (stats section 0635cbd9, base lifetimemoneyearned, int64 dollars)
  Per category X = solddrugs / soldjewelry / soldcash / soldvehicles, three kinds of owner:
    * story000 (the checklist line and the Earnings page), charlucia / charjason (the character pages), and
    * the fence contact who paid: brian, donnie, dunk, moses, pilotpete, randy, raul, tyrone, yasmani.
  In every save X/story000 = X/charlucia + X/charjason = the sum over the nine contacts (A6b narcotics:
  70,180 = 43,460 + 26,720 = Yasmani 13,700 + Brian 3,600 + Dunk 4,680 + Donnie 1,400 + Tyrone 46,800).
  soldfence (by the same owners) adds the four categories up for story000 and each character; a contact's soldfence
  also holds sales outside the four categories (Tyrone 72,900 = 59,400 in the four + 13,500).
  The line's cached percentage is totalprogressmade.X = pct32(X, total) (checklist.py), weight 2 each.

WHAT A SALE CHANGES (game-written: A5 -> A5as, one drop-off at Tyrone by Lucia, $33,600 narcotics + $12,600 bills)
  solddrugs/story000, /charlucia, /tyrone +33,600; soldcash/story000, /charlucia, /tyrone +12,600;
  soldfence/story000, /charlucia, /tyrone +46,200; lifetimemoneyearned/story000 (TOTAL EARNED) and /charlucia (MONEY
  EARNED) +46,720 = 46,200 + 520 found in the world (pickups +520 in the same interval); buckme/story000 and /charlucia
  (BUCKME EARNED: the drop-off pays into the BuckMe account) +46,200; totalprogressmade.solddrugs 36.579998 -> 70.18,
  .soldcash 82.223999 -> 87.264. Vehicle sales also count one vehicle: A5as -> A6as soldvehicles/randy +6,815 and
  fenced.vehicle/randy 10 -> 11, fenced.vehicle/story000 17 -> 18. TOTAL EARNED moved by the sale in every interval
  where it could be isolated (A2 -> A3: 10,000 task + 9,075 sales = +19,075; A4 -> A5 Jason: +28,365 sales inside
  +307,754). Reward tracker 5428c585 (set d6d53427) follows soldvehicles/story000 (198,165 in A6b) and 93c167e8
  follows soldfence/story000 (completed between A3 and A4, between 194,005 and 276,465).

WHAT IT CHANGES (apply), for each chosen line below its total, with D = total - current:
  * lifetimemoneyearned.X for story000, the character (choice['character'], Lucia by default) and the fence +D;
  * lifetimemoneyearned.soldfence for the same three owners +D;
  * lifetimemoneyearned (no qualifier) for story000 and the character +D (TOTAL EARNED, MONEY EARNED);
  * lifetimemoneyearned.buckme for story000 and the character +D (BUCKME EARNED);
  * vehicles only: fenced.vehicle/story000 and /fence +1 (one vehicle sold);
  * totalprogressmade.X = pct32(new, total), then the overall figure through checklist.refresh_overall;
  * challenge trackers (incomplete only) whose score source is one of the story000 rows above and whose score equals
    the old value get the new value; trackers are never completed (as in challenges.py / activities.py).
  The fence is choice['fences'][line] or, by default, the contact who already bought the most of that category in
  this save (narcotics Tyrone, jewelry and marked bills Yasmani, vehicles Randy in A6b). Only contacts seen buying the
  category, or named for it in the game text, are accepted.

NOT REPRODUCED: no money is added (the BuckMe balance, ScriptBankLedger and money stats are untouched; Save Garage's
money editor can add the proceeds), no item leaves the inventory (no marked bills, jewelry or narcotics are needed),
no vehicle is removed, the fence's own state is untouched (ScriptFence timestamps and flags, numcompleted.fencemissions,
ScriptPartnerFencing), and no reward tracker is completed.

RISK: medium-low. Stats only (plus at most two tracker scores), rows and increments the game itself writes for a sale.
The earnings totals then include a sale that never paid out; if a reward tracker's threshold is reached (soldvehicles
reaches exactly 200,000), the game may grant its reward the next time it checks.
"""
import challenges
import checklist
import featurelib as fl

FEATURE = 'fencing'
LME = 'lifetimemoneyearned'
TP = 'totalprogressmade'
ST = 'story000'
CHARACTERS = {'lucia': 'charlucia', 'jason': 'charjason'}
# key: (qualifier, total, label)
LINES = {
    'narcotics': ('solddrugs', 100000, 'NARCOTICS FENCED'),
    'jewelry': ('soldjewelry', 100000, 'JEWELRY FENCED'),
    'markedbills': ('soldcash', 250000, 'MARKED BILLS FENCED'),
    'vehicles': ('soldvehicles', 200000, 'VEHICLES FENCED'),
}
LINE_ORDER = ('narcotics', 'jewelry', 'markedbills', 'vehicles')
FENCES = {'brian': 'Brian', 'donnie': 'Donnie', 'dunk': 'Dunk', 'moses': 'Moses', 'pilotpete': 'Pilot Pete',
          'randy': 'Randy', 'raul': 'Raul', 'tyrone': 'Tyrone', 'yasmani': 'Yasmani'}
# Contacts who buy each category: seen buying it in the saves, or named for it in the game text ('Donnie / Brian will
# pay for any narcotics, jewelry and marked bills', 'Yasmani will buy stolen goods ... jewelry and marked bills').
BUYERS = {
    'narcotics': ('tyrone', 'yasmani', 'dunk', 'brian', 'donnie'),
    'jewelry': ('yasmani', 'dunk', 'brian', 'donnie'),
    'markedbills': ('yasmani', 'tyrone', 'brian', 'donnie'),
    'vehicles': ('randy', 'moses'),
}
STORY_H = fl.joaat(ST)


def _default_fence(st, key):
    """The contact who already bought the most of this category (ties and all-zero: first in BUYERS)."""
    q = LINES[key][0]
    best = None
    for f in BUYERS[key]:
        v = st.value(LME, q, f) or 0
        if best is None or v > best[1]:
            best = (f, v)
    return best[0]


def _trackers(t, sources):
    """[(record, score_start, score_end, (base, item))] of incomplete challenge scores fed by story000 rows in sources."""
    out = []
    for r in challenges._records(t):
        if r['done']:
            continue
        for a, z, (bb, ii, oo) in challenges._scores(t, *r['param']):
            if oo == STORY_H and (bb, ii) in sources:
                out.append((r, a, z, (bb, ii)))
    return out


def _sources():
    """Story000 rows a sale moves, as (base hash, qualifier hash) -> readable name."""
    src = {(fl.joaat(LME), fl.joaat(q)): q for q, _, _ in LINES.values()}
    src[(fl.joaat(LME), fl.joaat('soldfence'))] = 'soldfence'
    src[(fl.joaat(LME), 0)] = 'lifetimemoneyearned'
    src[(fl.joaat(LME), fl.joaat('buckme'))] = 'buckme'
    src[(fl.joaat('fenced'), fl.joaat('vehicle'))] = 'fenced.vehicle'
    return src


def read(b):
    s = fl.Save(b)
    st = fl.Stats(s.text(fl.STATS))
    lines = []
    for key in LINE_ORDER:
        q, total, label = LINES[key]
        v = st.value(LME, q)
        chars = {c: st.value(LME, q, o) for c, o in CHARACTERS.items()}
        fences = {f: st.value(LME, q, f) for f in FENCES}
        pct = st.value(TP, q)
        lines.append({'key': key, 'label': label, 'value': v, 'of': total, 'missing': None if v is None else max(0, total - v),
                      'percent': pct, 'percentConsistent': None if pct is None or v is None else abs(pct - fl.pct32(v, total)) <= 2e-6,
                      'byCharacter': chars, 'byFence': {f: x for f, x in fences.items() if x},
                      'charactersConsistent': None not in chars.values() and v == sum(chars.values()),
                      'fencesConsistent': None not in fences.values() and v == sum(fences.values()),
                      'defaultFence': _default_fence(st, key), 'buyers': list(BUYERS[key]),
                      'done': v is not None and v >= total})
    fence_total = st.value(LME, 'soldfence')
    t = s.text(challenges.SEC)
    src = _sources()
    trackers = [{'challenge': fl.hexid(r['id']), 'set': fl.hexid(r['set']), 'row': src[k], 'score': t[a:z].decode()}
                for r, a, z, k in _trackers(t, src)]
    return {'feature': FEATURE, 'lines': lines,
            'soldfence': {'value': fence_total, 'consistent': fence_total == sum(x['value'] or 0 for x in lines)},
            'earned': {'total': st.value(LME, 0), 'lucia': st.value(LME, 0, 'charlucia'), 'jason': st.value(LME, 0, 'charjason'),
                       'buckme': st.value(LME, 'buckme'), 'buckmeLucia': st.value(LME, 'buckme', 'charlucia'),
                       'buckmeJason': st.value(LME, 'buckme', 'charjason')},
            'vehiclesFencedCount': st.value('fenced', 'vehicle'), 'trackers': trackers,
            'overall': st.value(*checklist.OVERALL),
            'possible': [x['key'] for x in lines if not x['done']],
            'risk': 'medium-low',
            'notes': ['Records one fence sale per unfinished line, worth exactly what is missing, with every earnings total that a real '
                      'sale moves (category, Total Earned, Money Earned, BuckMe Earned, the fence and the character).',
                      'No money is added and no goods leave the inventory; use the money editor if you want the proceeds.',
                      'The fence defaults to the contact who already bought most of that category.']}


def apply(b, choice=None):
    """choice: {'lines': 'all' | [keys], 'character': 'lucia' | 'jason', 'fences': {line key: contact}} -> (new bytes, log).
    Each chosen line below its total gets one sale worth exactly what is missing; lines already complete are left alone."""
    choice = choice or {}
    keys = choice.get('lines', 'all')
    if keys == 'all':
        keys = list(LINE_ORDER)
    elif isinstance(keys, (str, bytes)) or not hasattr(keys, '__iter__') or set(keys) - set(LINE_ORDER):
        raise fl.FeatureError('unknown_line')
    char = choice.get('character', 'lucia')
    if char not in CHARACTERS:
        raise fl.FeatureError('bad_request')
    fences = choice.get('fences') or {}
    if not isinstance(fences, dict) or set(fences) - set(LINE_ORDER):
        raise fl.FeatureError('bad_request')
    st = fl.Stats(fl.Save(b).text(fl.STATS))
    sales = []
    for key in LINE_ORDER:
        if key not in keys:
            continue
        q, total, _ = LINES[key]
        cur = st.value(LME, q)
        if cur is None:
            raise fl.FeatureError('layout_changed')
        if cur < total:
            sales.append((key, total - cur, char, fences.get(key) or _default_fence(st, key)))
    return apply_sales(b, sales)


def apply_sales(b, sales):
    """Record explicit sales [(line key, dollars, 'lucia' | 'jason', contact)] the way the game records a drop-off
    (also used by the tests to replay the game's own sales). -> (new bytes, log)."""
    if not sales:
        return b, []
    s = fl.Save(b)
    st = fl.Stats(s.text(fl.STATS))
    delta, log = {}, []

    def add(base, qual, own, n):
        delta[(base, qual, own)] = delta.get((base, qual, own), 0) + n

    for key, d, char, fence in sales:
        if key not in LINES or char not in CHARACTERS:
            raise fl.FeatureError('bad_request')
        if fence not in BUYERS[key]:
            raise fl.FeatureError('unknown_fence')
        if isinstance(d, bool) or not isinstance(d, int) or d <= 0:
            raise fl.FeatureError('bad_value')
        q, _, label = LINES[key]
        owner = CHARACTERS[char]
        for own in (ST, owner, fence):
            add(LME, q, own, d)
            add(LME, 'soldfence', own, d)
        for own in (ST, owner):
            add(LME, 0, own, d)
            add(LME, 'buckme', own, d)
        if key == 'vehicles':
            add('fenced', 'vehicle', ST, 1)
            add('fenced', 'vehicle', fence, 1)
        log.append({'what': 'sale', 'line': key, 'label': label, 'amount': d, 'fence': fence, 'character': char})
    olds = {}
    for (base, qual, own), n in delta.items():
        cur = st.value(base, qual, own)
        if cur is None:
            raise fl.FeatureError('layout_changed')
        olds[(base, qual, own)] = cur
        st.set(base, qual, cur + n, '%s.%s/%s' % (base, qual or '-', own), own)
    for key in dict.fromkeys(x[0] for x in sales):
        q, total, label = LINES[key]
        if st.row(TP, q) is None:
            raise fl.FeatureError('layout_changed')
        st.set(TP, q, fl.pct32(st.value(LME, q), total), '%s, part of 100%% completion' % label.capitalize())
    checklist.refresh_overall(st)
    # tracker mirrors (story000 rows only), applied from the end of the text backwards
    t = s.text(challenges.SEC)
    src = _sources()
    changed = {}
    for (base, qual, own), n in delta.items():
        if own == ST:
            changed[(fl.joaat(base), fl.joaat(qual) if qual else 0)] = (olds[(base, qual, own)], olds[(base, qual, own)] + n)
    edits = []
    for r, a, z, k in _trackers(t, src):
        if k not in changed:
            continue
        old, new = changed[k]
        if t[a:z] != b'%d' % old:
            log.append({'what': 'tracker_kept', 'challenge': fl.hexid(r['id']), 'score': t[a:z].decode(), 'counter': old})
            continue
        edits.append((a, z, b'%d' % new))
        log.append({'what': 'tracker_score', 'challenge': fl.hexid(r['id']), 'set': fl.hexid(r['set']), 'row': src[k], 'from': old, 'to': new})
    if edits:
        for a, z, tok in sorted(edits, key=lambda x: -x[0]):
            t = t[:a] + tok + t[z:]
        s.set_text(challenges.SEC, t)
    txt, slog = st.apply()
    s.set_text(fl.STATS, txt)
    return s.build(), log + slog
