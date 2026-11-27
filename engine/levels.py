# Save Garage - Copyright (C) 2026 NotHGM - GNU GPL v3 with the additional terms in NOTICE; see LICENSE.
"""Lucia's and Jason's strength, cardio and focus levels (Save Garage feature module, shown on the World tab).

The names are the game's own: its text has "Strength Leveled Up", "Cardio Leveled Up" and "Focus Leveled Up".

WHY TWO PLACES
  The game keeps each of these levels twice. A level changed only in the stats comes back as it was once the save
  loads, because the game takes the copy in ScriptCharacterPhysique (reported by ShujiJaeger in
  HelloMoon-1/save-garage#4). So both copies are set together.

WHAT IT CHANGES (each value is replaced in place after its old token is checked; everything else stays as written)
  * ScriptCharacterPhysique, script section 46f14889, at ScriptSaveBlock $0x24d043f2 / $0x46f14889 / $0x45a134ec: one
    record per character, $0x149f1b42 Lucia and $0x6e3c5198 Jason. Each holds three level/points pairs as plain ints:
    strength $0x2c4379f2 / $0x6d5fdcac, cardio $0x381bd0ae / $0xbbacaf36 and focus $0xd3de8c6b / $0x168792d9. The
    chosen level is written, and when it changes its points go to 0, the start of the level, as after a level-up in
    the game. Leaving them would keep progress made toward a different level (focus points reach 156 within level
    1), which could move the level again as soon as the game counts them. The floats, timestamps and lists beside
    them stay as the game wrote them.
  * Stats section 0635cbd9: currentlevel.muscle, currentlevel.cardio and currentlevel.focus for charlucia and charjason.
    For cardio and focus numlevelups is set too, so that currentlevel = numlevelups - numleveldowns stays true, as it
    is in every game save. Strength is set straight by the story in places (that rule doesn't hold for it), so its
    counters are left alone.

EVIDENCE (dev_scratch/check_levels_module.py: the 22 distinct game saves of the research set, 44 character records)
  * Cardio and focus agree between the two copies in all 44 records, strength in 40. The other four are Jason's
    strength (physique 1 or 2 where the stats say 3 or 0); which copy the game shows there isn't known, so both are
    set alike here.
  * The level/points pairs: the points fall back when a level goes up (Lucia's cardio 1 with 55 points, then 2 with
    0) and are always 0 for strength.
  * Levels count from 0. The reporter of HelloMoon-1/save-garage#4 checked the menus: five strength levels, four of
    cardio and focus, so the highest values are 4, 3 and 3 (Lucia's story-set strength 4 shows as full). Game saves
    hold strength 0 to 4, cardio and focus 0 to 2.
  * $0x149f1b42 is Lucia and $0x6e3c5198 Jason: the levels line up with charlucia's and charjason's stats that way
    round in every save, and only strength ever goes down (numleveldowns is 0 for cardio and focus in every save).

REFUSED (FeatureError, nothing written): levels_layout (a record, level or stat isn't where or what this module
  expects), out_of_range, bad_request, verify_failed.

RISK: experimental. Not tested on a PS5 yet.
"""
import json
import re

import featurelib as fl

FEATURE = 'levels'
SEC = 0x46f14889                                     # ScriptCharacterPhysique
PATH = ('$0x24d043f2', fl.key(SEC), '$0x45a134ec')   # ScriptSaveBlock / the section / the per-character records
RECORD = {'lucia': '$0x149f1b42', 'jason': '$0x6e3c5198'}
OWNER = {'lucia': 'charlucia', 'jason': 'charjason'}
NAME = {'lucia': 'Lucia', 'jason': 'Jason'}
ATTRS = ('muscle', 'cardio', 'focus')
LEVEL = {'muscle': '$0x2c4379f2', 'cardio': '$0x381bd0ae', 'focus': '$0xd3de8c6b'}
POINTS = {'muscle': '$0x6d5fdcac', 'cardio': '$0xbbacaf36', 'focus': '$0x168792d9'}
LEVEL_MAX = {'muscle': 4, 'cardio': 3, 'focus': 3}   # counted from 0: five strength levels, four of cardio and focus
LABEL = {'muscle': 'Strength', 'cardio': 'Cardio', 'focus': 'Focus'}
KEEP_COUNTS = ('cardio', 'focus')                    # currentlevel = numlevelups - numleveldowns
_INT = re.compile(rb'-?(?:0|[1-9][0-9]*)')


def _token(t, who, k):
    try:
        s, e = fl.walk(t, *PATH, RECORD[who], k)
    except (fl.FeatureError, IndexError):
        raise fl.FeatureError('levels_layout')
    if not _INT.fullmatch(t[s:e]):
        raise fl.FeatureError('levels_layout')
    return (s, e), int(t[s:e])


def _physique(t):
    """{character: {attribute: {'level': (span, value), 'points': (span, value)}}}, or levels_layout."""
    return {who: {a: {'level': _token(t, who, LEVEL[a]), 'points': _token(t, who, POINTS[a])} for a in ATTRS}
            for who in RECORD}


def _load(b):
    """(Save, physique tokens, Stats) or levels_layout."""
    s = fl.Save(b)
    try:
        t = s.text(SEC)
    except fl.money.SaveError:                       # no ScriptCharacterPhysique section
        raise fl.FeatureError('levels_layout')
    ph = _physique(t)
    st = fl.Stats(s.text(fl.STATS))
    if any(st.row('currentlevel', a, o) is None for a in ATTRS for o in OWNER.values()):
        raise fl.FeatureError('levels_layout')
    return s, ph, st


def read(b):
    try:
        _, ph, st = _load(b)
        problem = None
    except fl.FeatureError as e:
        ph, st, problem = None, None, str(e)
    chars = []
    for who in RECORD:
        lv = {}
        if not problem:
            for a in ATTRS:
                lv[a] = {'value': ph[who][a]['level'][1], 'stat': st.value('currentlevel', a, OWNER[who]),
                         'max': LEVEL_MAX[a]}
        chars.append({'key': who, 'name': NAME[who], 'levels': lv})
    return {'feature': FEATURE, 'characters': chars, 'max': LEVEL_MAX, 'problem': problem, 'risk': 'experimental'}


def _checked(choice):
    """choice: {'lucia': {'muscle': 0-4, 'cardio': 0-3, 'focus': 0-3}, 'jason': {...}}; any part may be left out."""
    if not isinstance(choice, dict) or not choice or set(choice) - set(RECORD):
        raise fl.FeatureError('bad_request')
    out = {}
    for who, c in choice.items():
        if not isinstance(c, dict) or set(c) - set(ATTRS):
            raise fl.FeatureError('bad_request')
        for a, v in c.items():
            if isinstance(v, bool) or not isinstance(v, int):
                raise fl.FeatureError('bad_request')
            if not 0 <= v <= LEVEL_MAX[a]:
                raise fl.FeatureError('out_of_range')
            out.setdefault(who, {})[a] = v
    return out


def apply(b, choice):
    """choice as _checked takes it -> (new bytes, log). Both copies of each chosen level are set; a level that already
    holds the chosen value in both is left alone, so applying the same choice again changes nothing."""
    want = _checked(choice)
    s, ph, st = _load(b)
    t = s.text(SEC)
    edits, log = [], []
    for who, c in want.items():
        o = OWNER[who]
        for a, v in c.items():
            (span, now), (pspan, points) = ph[who][a]['level'], ph[who][a]['points']
            label = '%s level (%s)' % (LABEL[a], NAME[who])
            stat_now = st.value('currentlevel', a, o)
            if now != v:
                edits.append((span, v))
                if points:
                    edits.append((pspan, 0))
            st.set('currentlevel', a, v, label, owner=o)
            if a in KEEP_COUNTS:
                ups, downs = st.value('numlevelups', a, o), st.value('numleveldowns', a, o)
                if ups is not None and downs is not None and ups - downs != v:
                    st.set('numlevelups', a, v + downs, label, owner=o)
            if now != v or stat_now != v:
                log.append({'what': 'world', 'label': label, 'from': now + 1, 'to': v + 1})
    if not log:
        return b, []
    for (vs, ve), v in sorted(edits, reverse=True):      # from the end, so the earlier spans stay valid
        t = fl.splice(t, vs, ve, b'%d' % v)
    json.loads(t)
    s.set_text(SEC, t)
    txt, _ = st.apply()
    s.set_text(fl.STATS, txt)
    out = s.build()
    after = read(out)                                     # read back: both copies hold the chosen levels
    if after['problem']:
        raise fl.FeatureError('verify_failed')
    for ch in after['characters']:
        for a, v in want.get(ch['key'], {}).items():
            if ch['levels'][a]['value'] != v or ch['levels'][a]['stat'] != v:
                raise fl.FeatureError('verify_failed')
    return out, log
