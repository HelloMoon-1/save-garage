"""Complete challenges (Save Garage feature module).

THE 212 SAVED CHALLENGES (section 3000010d Challenges: codeVersion + savedChallengeSets[11])
  * 8 sets x 10 = the 80 challenges of the CHALLENGES menu, in menu order (category order is alphabetical, as on
    screen): f5d004cf COMBAT, 073d2400 CRIMINAL, 8d42de3f EXPLORATION, b246908b FITNESS, 10ee1f26 SHOPPING,
    c7cd04f0 SPORTS, afab26e8 SURVIVAL, fa3d2fd7 VEHICLE. Each has a stats counter challengescompleted.<set id>.
    Evidence: the first challenge of every category matches the screenshots' done/not-done state (Speed Kills done,
    Mugging not, ...), FITNESS #1 'Gym Member' completed exactly when the first gym membership was bought (A0->A1),
    and the linked progress stats fit the categories (holdups -> CRIMINAL, vehicle mods -> SHOPPING, a hoop row ->
    SPORTS, fish and animals -> SURVIVAL, wheelies and top speed -> VEHICLE).
  * 348d4be2 (54): profile-wide awards. A fresh playthrough (B7as_a) starts with exactly the 23 completions of the
    other playthrough, so these follow the console profile (very likely the trophy mirror). Not edited.
  * e7c89bfd (16): per-save goals with per-character progress (swim/run distances since a baseline). Not edited.
  * d6d53427 (62): per-save reward trackers ('Spawns a Bravado Banshee. To unlock: Complete all combat
    challenges.' and so on: 5-of-10 and all-10 per category, one for all challenges, plus others linked to stunt,
    money and collection stats). Not completed by this module; see MIRRORS.

WHAT IT CHANGES
  For each chosen menu challenge that is not complete (section 3000010d):
    * isComplete false -> true;
    * pSaveParam -> {"$type":"0x209f39e2"} (the empty parameter). In all 3,240 challenge records of the 20 saves
      every complete challenge has exactly this parameter, and in every completion seen the game replaced the
      progress parameter with it.
  Stats (0635cbd9, owner story000):
    * challengescompleted.<set> += completed in that set; challengescompleted (no qualifier) += total completed.
      In every game save the set counters equal the completed records and the total equals their sum.
    * totalprogressmade.challengescompleted = float32(total / 70) * 100, capped at 100 ('CHALLENGES COMPLETED
      x / 70' on the 100% checklist; 70 of the 80 are needed).
  MIRRORS: any incomplete tracker whose (sub-)parameter points at challengescompleted.<set or total>/story000 and
  whose score equals the old counter gets the new counter as its score (216 of 216 such scores in the saves equal
  the counter). The trackers themselves are not completed.
  Counters change by the number completed rather than being recomputed, so values edited earlier are kept (the PS5
  kept an edited total of 1000 as-is).

NOT CHANGED: the progress stats a challenge watched (kills, mods, distances...), challengecompletedbits (mission
challenges), the three non-menu sets, rewards, and the overall 100% figure (its weights can't be derived).

RISK: medium-high. Completion flags and counters are exactly what the game writes, but the category rewards (vehicle
spawns) are granted by the game's own completion event and may not unlock; the game might also re-check a tracker
only when its stat changes again.
"""
import featurelib as fl

FEATURE = 'challenges'
SEC = 0x3000010d
FOR_100 = 70
TOTAL = 80
EMPTY_PARAM = b'{"$type":"0x209f39e2"}'
K_SETS, K_SETID, K_LIST = fl.key('savedChallengeSets'), fl.key('challengeSetId'), fl.key('savedChallenges')
K_PARAM, K_ID, K_DONE = fl.key('pSaveParam'), fl.key('challengeId'), fl.key('isComplete')
K_SCORE, K_SRC, K_SUB = fl.key('score'), fl.key('sourceId'), fl.key('saveParams')
K_BASE, K_ITEM, K_SCOPE = fl.key('BaseId'), fl.key('ItemId'), fl.key('Scope')
B_COUNTER = fl.joaat('challengescompleted')
STORY = fl.joaat('story000')

CATEGORIES = (
    (0xf5d004cf, 'combat', 'Combat'), (0x073d2400, 'criminal', 'Criminal'), (0x8d42de3f, 'exploration', 'Exploration'),
    (0xb246908b, 'fitness', 'Fitness'), (0x10ee1f26, 'shopping', 'Shopping'), (0xc7cd04f0, 'sports', 'Sports'),
    (0xafab26e8, 'survival', 'Survival'), (0xfa3d2fd7, 'vehicle', 'Vehicle'),
)
CATEGORY_OF = {sid: (k, label) for sid, k, label in CATEGORIES}
OTHER_SETS = {
    0x348d4be2: ('profile_awards', 'Profile-wide awards (carried into new playthroughs; likely the trophy mirror)'),
    0xe7c89bfd: ('goals', 'Per-save goals with per-character progress'),
    0xd6d53427: ('reward_trackers', 'Per-save reward trackers (vehicle spawn unlocks and others)'),
}
# First challenge of each category, from the stats screens (title, description).
KNOWN = {
    0x624b005d: ('Speed Kills', 'Kill 3 enemies in under 30 seconds.'),
    0x9cc2329b: ('Mugging', 'Rob 5 pedestrians.'),
    0x8244cf1e: ('WAiNK Locations', 'Scan any 4 landmarks, curiosities, or sculptures with WAiNK.'),
    0xd5dae49d: ('Gym Member', 'Become a member at any gym.'),
    0xc58c59c7: ('Vehicle Modder', 'Make 5 modifications to your vehicle using a mod shop.'),
    0xa3649639: ('Basketball Rookie', 'Score a basketball shot at 3 different hoops in a day.'),
    0x2621d002: ('Alligator Kills', 'Kill 3 wild alligators.'),
    0x450d7231: ('Vehicle Discovery', 'Examine or discover 6 different vehicles.'),
}
REWARDS = {   # game text: 'Spawns a <vehicle>. To unlock: Complete 5 / all <category> challenges.'
    'combat': ('Speeder 700 GT', 'Bravado Banshee'), 'criminal': ('Maibatsu Sanchez', 'Western Zombie Bobber'),
    'exploration': ('Nagasaki Sea Sparrow', 'Nagasaki Carbon RS'), 'fitness': ('Tuff BMX', "'65 Vapid Dominator"),
    'shopping': ('Maibatsu Boomazoom', 'Truffade Thrax'), 'sports': ('Vapid Stanier G2 Taxi', 'Brimstone Golfer'),
    'survival': ('Airboat 09', 'Hauners Rhino Tank'), 'vehicle': ('Lapwing Mallard', 'Progen Emerus'),
    'all': ('Hauners P-996 LAZER',),
}


def _hexval(t, s, e):
    """Value of {"$data":"0x...."} at t[s:e]."""
    for k, a, z in fl.members(t, s):
        if k == '$data':
            return int(t[a + 1:z - 1], 16) & fl.M32
    raise fl.FeatureError('layout_changed')


def _scores(t, ps, pe):
    """Score spans inside a pSaveParam object: [(score_start, score_end, (base, item, scope))]."""
    out = []
    if t[ps] != ord('{'):
        return out
    mem = {k: (a, z) for k, a, z in fl.members(t, ps)}
    if K_SUB in mem:
        for a, z in fl.elements(t, mem[K_SUB][0]):
            out += _scores(t, a, z)
    if K_SCORE in mem and K_SRC in mem and t[mem[K_SRC][0]] == ord('{'):
        src = {k: (a, z) for k, a, z in fl.members(t, mem[K_SRC][0])}
        if K_BASE in src:
            key = tuple(_hexval(t, *src[k]) for k in (K_BASE, K_ITEM, K_SCOPE))
            out.append((mem[K_SCORE][0], mem[K_SCORE][1], key))
    return out


def _records(t):
    """[{set, index, id, done, rec, param, done_span}] in text order."""
    s, _ = fl.walk(t, fl.CODE, fl.key(SEC), K_SETS)
    out = []
    for a, z in fl.elements(t, s):
        mem = {k: (x, y) for k, x, y in fl.members(t, a)}
        sid = _hexval(t, *mem[K_SETID])
        for i, (ra, rz) in enumerate(fl.elements(t, mem[K_LIST][0])):
            rm = {k: (x, y) for k, x, y in fl.members(t, ra)}
            done = t[rm[K_DONE][0]:rm[K_DONE][1]]
            if done not in (b'true', b'false'):
                raise fl.FeatureError('layout_changed')
            out.append({'set': sid, 'index': i, 'id': _hexval(t, *rm[K_ID]), 'done': done == b'true', 'rec': (ra, rz),
                        'param': rm[K_PARAM], 'done_span': rm[K_DONE]})
    return out


def _label(r):
    if r['id'] in KNOWN:
        return KNOWN[r['id']][0]
    cat = CATEGORY_OF.get(r['set'])
    return '%s challenge %d' % (cat[1], r['index'] + 1) if cat else 'Challenge %08x' % r['id']


def read(b):
    s = fl.Save(b)
    t = s.text(SEC)
    st = fl.Stats(s.text(fl.STATS))
    recs = _records(t)
    cats = []
    for sid, k, label in CATEGORIES:
        rs = [r for r in recs if r['set'] == sid]
        items = []
        for r in rs:
            sc = _scores(t, *r['param'])
            prog = None
            if sc and not r['done']:
                a, z, (bb, ii, oo) = sc[0]
                prog = {'score': t[a:z].decode(), 'stat': '%08x/%08x/%08x' % (bb, ii, oo)}
            items.append({'id': fl.hexid(r['id']), 'n': r['index'] + 1, 'title': _label(r),
                          'description': KNOWN.get(r['id'], (None, None))[1], 'done': r['done'], 'progress': prog})
        done = sum(1 for r in rs if r['done'])
        counter = st.value(B_COUNTER, sid)
        cats.append({'id': fl.hexid(sid), 'key': k, 'label': label, 'done': done, 'of': len(rs), 'counter': counter,
                     'consistent': counter == done, 'rewards': REWARDS.get(k), 'challenges': items})
    total = st.value(B_COUNTER, 0)
    other = []
    for sid, (k, label) in OTHER_SETS.items():
        rs = [r for r in recs if r['set'] == sid]
        other.append({'id': fl.hexid(sid), 'key': k, 'label': label, 'done': sum(1 for r in rs if r['done']), 'of': len(rs), 'editable': False})
    return {'feature': FEATURE, 'categories': cats,
            'done': sum(c['done'] for c in cats), 'of': TOTAL,
            'possible': [i['id'] for c in cats for i in c['challenges'] if not i['done']],
            'counter': {'value': total, 'consistent': total == sum(c['counter'] or 0 for c in cats)},
            'checklist': {'label': 'CHALLENGES COMPLETED', 'value': total, 'of': FOR_100},
            'percent': st.value('totalprogressmade', 'challengescompleted'),
            'otherSets': other, 'records': len(recs), 'risk': 'medium-high',
            'notes': ['Completes menu challenges the way the game records them and keeps the counters and the 100% row in step.',
                      'Category rewards (vehicle spawns) are granted by the game when it completes a challenge itself; they may not unlock.',
                      'Only the eight menu categories are editable; the profile awards, goals and reward trackers are read-only.']}


def apply(b, choice):
    """choice: {'challenges': [hex ids]} or {'categories': ['combat', ...] | 'all'} -> (new bytes, log)."""
    choice = choice or {}
    s = fl.Save(b)
    t = s.text(SEC)
    recs = _records(t)
    menu = [r for r in recs if r['set'] in CATEGORY_OF]
    if 'challenges' in choice:
        want = {fl.h(x if isinstance(x, int) else ('0x' + x if not x.startswith('0x') else x)) for x in choice['challenges']}
        known_ids = {r['id'] for r in recs}
        if want - known_ids:
            raise fl.FeatureError('unknown_challenge')
        if any(r['id'] in want and r['set'] not in CATEGORY_OF for r in recs):
            raise fl.FeatureError('not_editable')
        targets = [r for r in menu if r['id'] in want]
    else:
        cats = choice.get('categories', 'all')
        keys = {k for _, k, _ in CATEGORIES} if cats == 'all' else set(cats)
        if keys - {k for _, k, _ in CATEGORIES}:
            raise fl.FeatureError('unknown_category')
        targets = [r for r in menu if CATEGORY_OF[r['set']][0] in keys]
    targets = [r for r in targets if not r['done']]
    if not targets:
        return b, []
    st = fl.Stats(s.text(fl.STATS))
    per_set = {}
    for r in targets:
        per_set[r['set']] = per_set.get(r['set'], 0) + 1
    new_counter, log = {}, []
    for sid, n in per_set.items():
        cur = st.value(B_COUNTER, sid)
        if cur is None:
            raise fl.FeatureError('layout_changed')
        new_counter[sid] = (cur, cur + n)
        st.set(B_COUNTER, sid, cur + n, 'Challenges completed: ' + CATEGORY_OF[sid][1])
    cur = st.value(B_COUNTER, 0)
    new_counter[0] = (cur, cur + len(targets))
    st.set(B_COUNTER, 0, cur + len(targets), 'Challenges completed')
    st.set('totalprogressmade', 'challengescompleted', fl.pct32(cur + len(targets), FOR_100), 'Challenges, part of 100% completion')
    # text edits: completed records, then mirrored tracker scores; applied from the end of the text backwards
    edits = []
    done_ids = {r['id'] for r in targets}
    for r in targets:
        edits.append((r['done_span'][0], r['done_span'][1], b'true'))
        edits.append((r['param'][0], r['param'][1], EMPTY_PARAM))
        log.append({'what': 'challenge', 'id': fl.hexid(r['id']), 'category': CATEGORY_OF[r['set']][0], 'n': r['index'] + 1, 'title': _label(r)})
    for r in recs:
        if r['done'] or r['id'] in done_ids:
            continue
        for a, z, (bb, ii, oo) in _scores(t, *r['param']):
            if bb != B_COUNTER or oo != STORY or ii not in new_counter:
                continue
            old, new = new_counter[ii]
            tok = t[a:z]
            if tok != b'%d' % old:
                log.append({'what': 'tracker_kept', 'id': fl.hexid(r['id']), 'score': tok.decode(), 'counter': old})
                continue
            edits.append((a, z, b'%d' % new))
            log.append({'what': 'tracker_score', 'id': fl.hexid(r['id']), 'set': fl.hexid(r['set']), 'from': old, 'to': new})
    edits.sort(key=lambda x: -x[0])
    last = len(t) + 1
    for a, z, new in edits:
        if z > last:
            raise fl.FeatureError('layout_changed')
        t = t[:a] + new + t[z:]
        last = a
    s.set_text(SEC, t)
    txt, slog = st.apply()
    s.set_text(fl.STATS, txt)
    return s.build(), log + slog
