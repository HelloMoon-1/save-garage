"""Basketball hoops found and scored (Save Garage feature module). Checklist line 'BASKETBALL HOOPS x / 90'.

WHAT IT CHANGES
  Stats section 0635cbd9 (owner story000):
    * hoopfound.basketballhoopN / hoopscored.basketballhoopN (BoolData, N = 0..99) -> true for the chosen hoops;
    * hoopfound / hoopscored.basketballhoopalllocations (UInt32) += hoops newly marked; the checklist line reads the
      scored one;
    * hoopfound / hoopscored.basketballhoops<county>county (UInt32, five counties) += hoops newly marked in that county
      ('Vice-Dale Hoops x / y' and so on on the SPORTS page);
    * totalprogressmade.basketballhoopalllocations = float32(min(scored, 90) / 90) * 100;
    * totalprogressmade (no qualifier), the overall 100% figure, through checklist.refresh_overall.
  Section e4fcc5fa, table UniqueCollectibles (keys / timestampsSec / stateFlags): each newly scored hoop whose entry is
  still (0, 0) becomes (1, 5), the value the game wrote for the one hoop it scored.
  Challenges section 3000010d: incomplete trackers whose score is a counter equal to the old value follow it (none
  in the saves; the SPORTS challenge 9f75f7b8 holds per-county 'true' conditions, which are left for the game).

EVIDENCE FROM THE SAVES
  * A4 -> A5 (playthrough A): hoopfound 42 and 59 -> true, hoopscored 59 -> true; hoopfound.alllocations 0 -> 2 and
    hoopscored.alllocations 0 -> 1; hoopfound.vicedale 0 -> 2, hoopscored.vicedale 0 -> 1 (the other counties stay 0);
    totalprogressmade.basketballhoopalllocations 0 -> 1.111111 (= 1/90 in float32); the stats screen showed
    'BASKETBALL HOOPS 1 / 90'. In e4fcc5fa the key joaat('basketballhoop59') went from (0, 0) to (1, 5); the found-only
    hoop 42 kept (0, 0). All later game saves keep exactly this state.
  * The game text names the counters ('~b~Vice-Dale Hoops~b~ ~1~ / ~2~', Mariana, Lummox, Kelly, Leonard), the trophy
    'Score a basketball shot at all 100 hoops in Leonida', and the checklist asks for 90. The totals (~2~) are filled
    in at run time and are not in the save or the text.

COUNTY OF EACH HOOP (not in the save; public guides, 25 Nov 2026, searched with game terms only)
  * Per-hoop mapping: three hoop maps number the hoops 0..99 (the game's own basketballhoopN numbering: 0-based, and
    scattered across counties, unlike the guides' page order) and agree on every hoop they list: retrobroker.com
    (all 100), mapmaster.io (90 numbered, 9 named) and tracker.gg (search excerpt: Lummox 2, 24, 39, 65, 97). It is a
    partition of 0..99 into Vice-Dale 49, Mariana 18, Kelly 14, Leonard 14, Lummox 5.
  * Totals: PowerPyx lists the 100 hoops in its own page order under 'Mariana County (18)', 'Vice-Dale County (49)',
    'Leonard County (14)', 'Kelly County (14)', 'Lummox County (5)': the same five totals, counted independently.
  * Check against the save: the two hoops the game recorded (42, 59) are both Vice-Dale in the mapping, as the game's
    county counters say. That is the only save-side check (a 24% chance by luck alone), so the mapping is graded
    'likely'. 'all' only needs the totals: every county counter ends at its total whatever the per-hoop split.

LIMITS
  * The (1, 5) table value is copied from the one scored hoop; the meaning of timestamp 1 is unknown.
  * 'county_counters': 'skip' (the old behaviour) leaves every county counter unchanged.

RISK: medium (two sections; per-hoop counties from third-party maps, checked against one game-written example).
"""
import challenges
import checklist
import featurelib as fl

FEATURE = 'hoops'
SEC_TABLES = 0xe4fcc5fa
N_HOOPS = 100
FOR_100 = 90
ALL = 'basketballhoopalllocations'
COUNTIES = (('basketballhoopsmarianacounty', 'Mariana'), ('basketballhoopsvicedalecounty', 'Vice-Dale'),
            ('basketballhoopslummoxcounty', 'Lummox'), ('basketballhoopskellycounty', 'Kelly'),
            ('basketballhoopsleonardcounty', 'Leonard'))
LABEL = dict(COUNTIES)
_BY_COUNTY = {
    'basketballhoopsvicedalecounty': (0, 3, 8, 10, 14, 15, 16, 17, 18, 19, 20, 23, 25, 26, 27, 28, 29, 32, 34, 36, 42, 52, 54,
                                      55, 57, 58, 59, 62, 63, 64, 67, 69, 71, 72, 73, 74, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88,
                                      89, 94, 98),
    'basketballhoopsmarianacounty': (1, 5, 6, 9, 11, 13, 33, 35, 37, 40, 41, 43, 44, 47, 48, 60, 95, 96),
    'basketballhoopskellycounty': (4, 7, 22, 31, 45, 50, 53, 68, 75, 77, 90, 91, 92, 93),
    'basketballhoopsleonardcounty': (12, 21, 30, 38, 46, 49, 51, 56, 61, 66, 70, 76, 78, 99),
    'basketballhoopslummoxcounty': (2, 24, 39, 65, 97),
}
COUNTY_OF = {n: q for q, ns in _BY_COUNTY.items() for n in ns}
COUNTY_TOTALS = {q: len(ns) for q, ns in _BY_COUNTY.items()}     # 49 / 18 / 14 / 14 / 5 (PowerPyx headings agree)
GAME_WRITTEN_COUNTY = {42: 'basketballhoopsvicedalecounty', 59: 'basketballhoopsvicedalecounty'}   # A4 -> A5
KNOWN_COUNTY = COUNTY_OF                  # kept for callers of the old interface
SCORED_ENTRY = (1, 5)                     # (timestampsSec, stateFlags) the game wrote for the scored hoop 59
K_UNIQUE, K_KEYS, K_TIME, K_FLAGS = fl.key('UniqueCollectibles'), fl.key('keys'), fl.key('timestampsSec'), fl.key('stateFlags')


def hoop_name(n):
    return 'basketballhoop%d' % n


def _table(t):
    """Positions and values of the UniqueCollectibles columns: {col: (obj_start, tokens)}."""
    s, _ = fl.walk(t, fl.CODE, fl.key(SEC_TABLES), K_UNIQUE)
    cols = {}
    for k, vs, ve in fl.members(t, s):
        if k in (K_KEYS, K_TIME, K_FLAGS):
            cols[k] = (vs, fl.typed_values(t, vs)[1])
    if len(cols) != 3 or len({len(v[1]) for v in cols.values()}) != 1:
        raise fl.FeatureError('layout_changed')
    return cols


def _hoop_index(cols):
    keys = [int(x) & fl.M32 for x in cols[K_KEYS][1]]
    pos = {k: i for i, k in enumerate(keys)}
    return {n: pos.get(fl.joaat(hoop_name(n))) for n in range(N_HOOPS)}


def read(b):
    s = fl.Save(b)
    st = fl.Stats(s.text(fl.STATS))
    t = s.text(SEC_TABLES)
    cols = _table(t)
    idx = _hoop_index(cols)
    hoops = []
    for n in range(N_HOOPS):
        i = idx[n]
        entry = None if i is None else [int(cols[K_TIME][1][i]), int(cols[K_FLAGS][1][i])]
        hoops.append({'n': n, 'name': hoop_name(n), 'found': bool(st.value('hoopfound', hoop_name(n), default=False)),
                      'scored': bool(st.value('hoopscored', hoop_name(n), default=False)), 'table': entry,
                      'county': LABEL[COUNTY_OF[n]]})
    counters = {}
    for kind in ('hoopfound', 'hoopscored'):
        flag = 'found' if kind == 'hoopfound' else 'scored'
        c = {'all': st.value(kind, ALL)}
        per = {}
        for q, label in COUNTIES:
            c[label] = st.value(kind, q)
            per[label] = sum(1 for x in hoops if x[flag] and COUNTY_OF[x['n']] == q)
        n_true = sum(1 for x in hoops if x[flag])
        c['consistent'] = c['all'] == n_true and c['all'] == sum(c[label] or 0 for _, label in COUNTIES)
        c['countiesMatchMap'] = all(c[label] == per[label] for _, label in COUNTIES)
        counters[flag] = c
    scored = counters['scored']['all']
    return {'feature': FEATURE, 'hoops': hoops,
            'found': sum(1 for x in hoops if x['found']), 'scored': sum(1 for x in hoops if x['scored']), 'total': N_HOOPS,
            'possible': [x['n'] for x in hoops if not (x['found'] and x['scored'])],
            'counters': counters, 'countyTotals': {LABEL[q]: n for q, n in COUNTY_TOTALS.items()},
            'checklist': {'label': 'BASKETBALL HOOPS', 'value': scored, 'of': FOR_100},
            'percent': st.value('totalprogressmade', ALL),
            'countyKnown': sorted(COUNTY_OF), 'countySource': 'public hoop maps (likely); 42 and 59 checked against the save',
            'risk': 'medium',
            'notes': ['Scoring every hoop gives the 100% checklist row (90 needed), the all-hoops total and every county total.',
                      "Each hoop's county comes from public hoop maps (they agree with each other and with the two hoops the "
                      'game recorded); the county totals 49/18/14/14/5 are confirmed by an independent guide.']}


def apply(b, choice):
    """choice: {'hoops': 'all' | [N...], 'scored': True, 'county_counters': 'update' | 'skip'} -> (new bytes, log).
    'scored': False marks hoops found only. 'skip' leaves the county counters unchanged (logged)."""
    choice = choice or {}
    want = choice.get('hoops', 'all')
    if want != 'all' and (isinstance(want, (str, bytes)) or not hasattr(want, '__iter__')):
        raise fl.FeatureError('bad_request')
    nums = list(range(N_HOOPS)) if want == 'all' else sorted({int(x) for x in want})
    if any(not 0 <= n < N_HOOPS for n in nums):
        raise fl.FeatureError('unknown_hoop')
    mode = choice.get('county_counters', 'update')
    if mode not in ('update', 'skip'):
        raise fl.FeatureError('bad_request')
    do_score = choice.get('scored', True)
    s = fl.Save(b)
    st = fl.Stats(s.text(fl.STATS))
    new_found = [n for n in nums if not st.value('hoopfound', hoop_name(n), default=False)]
    new_scored = [n for n in nums if do_score and not st.value('hoopscored', hoop_name(n), default=False)]
    if not new_found and not new_scored:
        return b, []
    log, moved = [], {}

    def put(kind, q, new, label):
        old = st.value(kind, q)
        st.set(kind, q, new, label)
        moved[(fl.joaat(kind), fl.joaat(q), fl.joaat('story000'))] = (old, new)

    for kind, new in (('hoopfound', new_found), ('hoopscored', new_scored)):
        for n in new:
            if not st.set(kind, hoop_name(n), True, '%s %d' % (kind, n)):
                raise fl.FeatureError('layout_changed')
        if not new:
            continue
        put(kind, ALL, st.value(kind, ALL) + len(new), kind + ': all locations')
        if mode == 'skip':
            log.append({'what': 'county_counters_skipped', 'kind': kind, 'hoops': len(new)})
            continue
        by_county = {}
        for n in new:
            by_county[COUNTY_OF[n]] = by_county.get(COUNTY_OF[n], 0) + 1
        for q, add in sorted(by_county.items()):
            put(kind, q, st.value(kind, q) + add, '%s: %s hoops' % (kind, LABEL[q]))
    if new_scored:
        st.set('totalprogressmade', ALL, fl.pct32(st.value('hoopscored', ALL), FOR_100), 'Basketball hoops, part of 100% completion')
    checklist.refresh_overall(st)
    # incomplete challenge trackers on the moved counters (activities2 rule)
    import activities2
    ct = s.text(challenges.SEC)
    ct2, tlog = activities2.mirror_trackers(ct, moved)
    if ct2 != ct:
        s.set_text(challenges.SEC, ct2)
    log += tlog
    txt, slog = st.apply()
    s.set_text(fl.STATS, txt)
    log += slog
    # the e4fcc5fa entry of every newly scored hoop: both columns rewritten once, old tokens checked
    t = s.text(SEC_TABLES)
    cols = _table(t)
    idx = _hoop_index(cols)
    times, flags = list(cols[K_TIME][1]), list(cols[K_FLAGS][1])
    changed = False
    for n in new_scored:
        i = idx[n]
        if i is None:
            log.append({'what': 'table_entry_missing', 'hoop': n})
            continue
        cur = (int(times[i]), int(flags[i]))
        if cur == SCORED_ENTRY:
            continue
        if cur != (0, 0):
            log.append({'what': 'table_entry_kept', 'hoop': n, 'value': list(cur)})
            continue
        times[i], flags[i] = b'%d' % SCORED_ENTRY[0], b'%d' % SCORED_ENTRY[1]
        changed = True
        log.append({'what': 'table_entry', 'hoop': n, 'to': list(SCORED_ENTRY)})
    if changed:
        spans = []
        for k, toks in ((K_TIME, times), (K_FLAGS, flags)):
            span, old = fl.typed_values(t, cols[k][0])
            if len(old) != len(toks):
                raise fl.FeatureError('verify_failed')
            spans.append((span, toks))
        for (a, e), toks in sorted(spans, key=lambda x: -x[0][0]):     # later span first keeps earlier offsets valid
            t = t[:a] + b','.join(toks) + t[e:]
        s.set_text(SEC_TABLES, t)
    return s.build(), log
