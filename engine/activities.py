"""Meditation spots: the 100% checklist line 'MEDITATION SPOTS COMPLETED x / 15' (Save Garage feature module).

WHAT IT CHANGES
  Stats section 0635cbd9:
    * a74bee3d.<spot>/story000 (BoolData) false -> true for each chosen spot not yet completed (18 spot rows). The
      base name is not cracked; the family is identified by its values (see EVIDENCE).
    * uniquemeditations/story000 (UInt8) += spots newly completed ('MEDITATION SPOTS COMPLETED');
    * totalmeditations/story000 and totalmeditations/<character> (UInt32) += the same ('MEDITATIONS' and
      'SOLO MEDITATIONS (Lucia / Jason)'); the character is choice['character'], Lucia by default;
    * totalprogressmade.uniquemeditations = float32(min(spots, 15) / 15) * 100, the line's cached percentage;
    * totalprogressmade (no qualifier), the overall 100% figure, recomputed with checklist.refresh_overall.
  Challenges section 3000010d: every incomplete tracker whose source is totalmeditations/story000 or
  uniquemeditations/story000 and whose score equals the old counter gets the new counter as its score (in the saves:
  reward tracker 5ae6671e in set d6d53427). The same rule as challenges.py; trackers are not completed.
  Counters change by the number of spots completed, not by recounting, so values edited earlier are kept.

EVIDENCE
  * A4 -> A5 (playthrough A): Lucia completed three spots. These rows moved: a74bee3d.2eeb9ddd, .c7a54f5a and
    .ea10142f false -> true; uniquemeditations 1 -> 4; totalmeditations/story000 1 -> 4 and /charlucia 0 -> 3;
    totalprogressmade.uniquemeditations 6.666667 -> 26.666668 (4 / 15); tracker 5ae6671e 1 -> 4. The 67.5% stats
    screens show 'MEDITATION SPOTS COMPLETED 4 / 15' and 'MEDITATIONS 4'.
  * A0: one spot (8335543e) done with the partner: uniquemeditations 1, totalmeditations/story000 1 and
    /withpartner 1, Lucia and Jason 0. So story000 = Lucia + Jason + with partner, which this module keeps.
  * In all 20 saves the number of true a74bee3d flags equals uniquemeditations, and the cached percentage equals
    pct32(uniquemeditations, 15). The 18 spot hashes occur in no other section.
  * The 1,000 test: the PS5 kept totalmeditations = 1000 and its re-save left the tracker at 4, so the game neither
    recounts these rows on load nor re-syncs the tracker; only a real meditation moves it.

LIMITS / UNCERTAIN
  * 18 spot rows exist and the checklist asks for 15 (like 80 / 70 challenges, 100 / 90 hoops, 397 / 300 stunts).
    Whether the game ignores any of the 18 is unknown, so 'all' marks all 18 and the counter then reads 18 (the
    percentage caps at 100). The game text describes 9 spots and names 5; no text key matches a spot hash.
  * Rewards are not given: meditating trains focus, and the character attributes are left alone.

RISK: low-medium. Stats plus one tracker score; the rows and values the game itself wrote for real spots.
"""
import challenges
import checklist
import featurelib as fl

FEATURE = 'activities'
SPOT_BASE = 0xa74bee3d
SPOTS = (0x2eeb9ddd, 0x4e7cb866, 0x555feac5, 0x64a7f37a, 0x67c08f86, 0x7c6a1448, 0x8335543e, 0x8c9bb4ab, 0x9132e266,
         0xa0cfdd13, 0xa3088621, 0xaaacf0cd, 0xb448a8a1, 0xba2d8fce, 0xc37fa272, 0xc7a54f5a, 0xe7db6b29, 0xea10142f)
FOR_100 = 15
UNIQUE = ('uniquemeditations', 0)
TOTAL = 'totalmeditations'
PCT = ('totalprogressmade', 'uniquemeditations')
CHARACTERS = {'lucia': 'charlucia', 'jason': 'charjason'}
ST = fl.joaat('story000')
MIRRORED = {fl.joaat(TOTAL): TOTAL, fl.joaat(UNIQUE[0]): UNIQUE[0]}      # tracker sources (base, no qualifier, story000)


def _trackers(t):
    """[(record, score_start, score_end, counter name)] of incomplete challenge trackers fed by the meditation counters."""
    out = []
    for r in challenges._records(t):
        if r['done']:
            continue
        for a, z, (bb, ii, oo) in challenges._scores(t, *r['param']):
            if bb in MIRRORED and ii == 0 and oo == ST:
                out.append((r, a, z, MIRRORED[bb]))
    return out


def read(b):
    s = fl.Save(b)
    st = fl.Stats(s.text(fl.STATS))
    spots = []
    for i, hh in enumerate(SPOTS):
        row = st.row(SPOT_BASE, hh)
        spots.append({'id': fl.hexid(hh), 'n': i + 1, 'label': 'Meditation spot %d' % (i + 1),
                      'present': row is not None, 'done': bool(row and row['value'])})
    done = sum(1 for x in spots if x['done'])
    unique = st.value(*UNIQUE)
    t = s.text(challenges.SEC)
    trackers = [{'challenge': fl.hexid(r['id']), 'set': fl.hexid(r['set']), 'counter': name, 'score': t[a:z].decode()}
                for r, a, z, name in _trackers(t)]
    counters = {'unique': unique, 'total': st.value(TOTAL), 'lucia': st.value(TOTAL, 0, 'charlucia'),
                'jason': st.value(TOTAL, 0, 'charjason'), 'withPartner': st.value(TOTAL, 0, 'withpartner')}
    counters['consistent'] = unique == done
    pct = st.value(*PCT)
    return {'feature': FEATURE,
            'meditation': {'spots': spots, 'done': done, 'total': len(SPOTS), 'for100': FOR_100, 'counters': counters,
                           'percent': pct, 'percentConsistent': pct is not None and unique is not None and
                           abs(pct - fl.pct32(unique, FOR_100)) <= 2e-6, 'trackers': trackers},
            'checklist': {'label': 'MEDITATION SPOTS COMPLETED', 'value': unique, 'of': FOR_100},
            'overall': st.value(*checklist.OVERALL),
            'possible': [x['id'] for x in spots if x['present'] and not x['done']],
            'risk': 'low-medium',
            'notes': ['Marks meditation spots completed the way the game records a meditation, with the spot count, the meditation '
                      'counters, the 100% row and the overall figure in step.',
                      '18 spots exist and 15 are needed; all 18 are marked by default.',
                      'Meditation rewards (focus training) are not given.']}


def apply(b, choice=None):
    """choice: {'spots': 'all' | [hex ids], 'character': 'lucia' | 'jason'} -> (new bytes, log)."""
    choice = choice or {}
    want = choice.get('spots', 'all')
    if want == 'all':
        ids = list(SPOTS)
    else:
        if isinstance(want, (str, bytes)) or not hasattr(want, '__iter__'):
            raise fl.FeatureError('bad_request')
        ids = []
        for x in want:
            hh = fl.h(x if isinstance(x, int) else ('0x' + x if not x.lower().startswith('0x') else x))
            if hh not in SPOTS:
                raise fl.FeatureError('unknown_spot')
            ids.append(hh)
    char = choice.get('character', 'lucia')
    if char not in CHARACTERS:
        raise fl.FeatureError('bad_request')
    s = fl.Save(b)
    st = fl.Stats(s.text(fl.STATS))
    new = []
    for hh in dict.fromkeys(ids):
        row = st.row(SPOT_BASE, hh)
        if row is None:
            raise fl.FeatureError('layout_changed')
        if not row['value']:
            new.append(hh)
    if not new:
        return b, []
    n = len(new)
    for hh in new:
        st.set(SPOT_BASE, hh, True, 'Meditation spot %s completed' % fl.hexid(hh))
    olds = {}
    for name, (base, qual, owner) in (('unique', UNIQUE + ('story000',)), ('total', (TOTAL, 0, 'story000')),
                                      ('character', (TOTAL, 0, CHARACTERS[char]))):
        cur = st.value(base, qual, owner)
        if cur is None:
            raise fl.FeatureError('layout_changed')
        olds[name] = cur
        st.set(base, qual, cur + n, {'unique': 'Meditation spots completed', 'total': 'Meditations',
                                     'character': 'Solo meditations (%s)' % char.capitalize()}[name], owner)
    st.set(PCT[0], PCT[1], fl.pct32(olds['unique'] + n, FOR_100), 'Meditation spots, part of 100% completion')
    checklist.refresh_overall(st)
    log = [{'what': 'meditation_spot', 'spot': fl.hexid(hh)} for hh in new]
    # tracker mirrors in the challenges section (scores equal to the old counter follow it)
    t = s.text(challenges.SEC)
    newval = {TOTAL: (olds['total'], olds['total'] + n), UNIQUE[0]: (olds['unique'], olds['unique'] + n)}
    edits = []
    for r, a, z, name in _trackers(t):
        old, nv = newval[name]
        if t[a:z] != b'%d' % old:
            log.append({'what': 'tracker_kept', 'challenge': fl.hexid(r['id']), 'score': t[a:z].decode(), 'counter': old})
            continue
        edits.append((a, z, b'%d' % nv))
        log.append({'what': 'tracker_score', 'challenge': fl.hexid(r['id']), 'set': fl.hexid(r['set']), 'from': old, 'to': nv})
    if edits:
        for a, z, tok in sorted(edits, key=lambda x: -x[0]):
            t = t[:a] + tok + t[z:]
        s.set_text(challenges.SEC, t)
    txt, slog = st.apply()
    s.set_text(fl.STATS, txt)
    return s.build(), log + slog
