# Save Garage - Copyright (C) 2026 NotHGM - GNU GPL v3 with the additional terms in NOTICE; see LICENSE.
"""Time of day, health and armour.

Time of day lives in three places that the game always keeps equal: the clock in SimpleVariables, a copy of the clock
in Persistence, and ScriptInitialSpawn's LastTimeOfDay (the in-game clock as seconds since 1970). Only the hour, minute
and second change here; the date stays as it is, because moving it would leave the game's timers (cooldowns, expiries)
in the wrong place.

Health is PlayerPed's fHealth for the character the save was made as. The game writes values up to 250 while
fMaxHealth stays 100 (overpowered health), so edits stay within 1..250. Armour is fArmour on each armour part of both
characters' saved outfits, up to that part's fMaxArmour.
"""
import calendar
import json

import featurelib as fl

import jsonedit as je
import money
import physique

CODE, SCRIPT = '$0x7a47cb05', '$0x24d043f2'
SIMPLE, PERSIST, SPAWN, PED, LOOKS = 0x765fb4e3, 0x5399d3f4, 0xec2a7ce9, 0xe528fe31, 0x9653b39d
K = {'hour': '$0xc8893d05', 'minute': '$0xfb8c5018', 'second': '$0xae65d6cb', 'day': '$0xdbcb068b', 'month': '$0xbb64a995',
     'year': '$0x9ebbbabf'}
SPAWN_DATA, LAST_TIME = '$0xdee94c27', '$0x98775f68'
HEALTH, MAX_HEALTH = '$0x0834e1d0', '$0x4802abf7'
OUTFITS, ARMOUR_PARTS, ARMOUR, MAX_ARMOUR = '$0x32fe6867', '$0x5e8a4ee1', '$0x45b925e3', '$0x9f8e2fa0'
HEALTH_MAX = 250.0


class WorldError(Exception):
    pass


def _code(h):
    return [CODE, '$0x%08x' % h]


def _spawn():
    return [SCRIPT, '$0x%08x' % SPAWN, '$0x45a134ec', SPAWN_DATA]


def _num(raw):
    return float(raw) if b'.' in raw else int(raw)


CAPACITY = {'healthmax': (0, 'Health capacity'), 'staminamax': (1, 'Stamina capacity'),
            'meleestaminamax': (2, 'Melee stamina capacity'), 'specialabilitymax': (3, 'Focus capacity')}
CHARACTER = 0x22a87829
OWNERS = {'lucia': 0xb3634b85, 'jason': 0x25350e5c}


def growth_rows(character, stats):
    """Locate all four copies, including old saves in which their values disagree."""
    rows = {}
    prefix = _code(CHARACTER) + [fl.key('attributeSet')]
    players = json.loads(character)[CODE][fl.key(CHARACTER)].get(fl.key('attributeSet'), [])
    names = [p.get(fl.key('Name'), {}).get('$data') for p in players]
    for i, player in enumerate(players):
        for name, owner in OWNERS.items():
            if names[i] != fl.key(name)[1:] or names.count(names[i]) != 1:
                continue
            values = player.get(fl.key('attributes'), {}).get('$data', [])
            for qual, (index, label) in CAPACITY.items():
                if len(values) <= index + 30:
                    continue
                copies = (values[index], values[index + 30], stats.value('points', qual, owner), stats.value('rank', qual, owner))
                if not all(type(v) is int and 0 <= v <= 100 for v in copies):
                    continue
                rows[name + '_' + qual] = (copies, label, prefix + [i, fl.key('attributes'), '$data'], index, qual, owner)
    return rows


def read(b):
    ents, secs, gaps, head, tail = money._load(b)
    sec = lambda h: secs[money._sec(ents, h)]
    clock = {k: _num(je.get(sec(SIMPLE), _code(SIMPLE) + [v])) for k, v in K.items()}
    clock['month'] += 1                                    # the save counts months from 0
    ped = sec(PED)
    health = _num(je.get(ped, _code(PED) + [HEALTH]))
    looks = sec(LOOKS)
    parts = []
    for c, _ in je.members(looks, _code(LOOKS) + [OUTFITS]):
        for p, _ in je.members(looks, _code(LOOKS) + [OUTFITS, c, ARMOUR_PARTS]):
            base = _code(LOOKS) + [OUTFITS, c, ARMOUR_PARTS, p]
            parts.append({'character': c, 'part': p, 'armour': _num(je.get(looks, base + [ARMOUR])),
                          'max': _num(je.get(looks, base + [MAX_ARMOUR]))})
    stats = fl.Stats(sec(fl.STATS))
    capacities = growth_rows(sec(CHARACTER), stats)
    parts_phys = [secs[i] for i, entry in enumerate(ents) if entry[0] == physique.SECTION]
    levels = physique.read(parts_phys[0], stats) if len(parts_phys) == 1 else []
    return {'attributeLevels': levels, 'capacities': {k: {'value': v[0][0], 'copies': v[0], 'label': v[1]} for k, v in capacities.items()}, 'clock': clock, 'health': health, 'healthMax': HEALTH_MAX,
            'armour': sum(x['armour'] for x in parts), 'armourMax': sum(x['max'] for x in parts)}


def apply(b, edit):
    """edit: {'time': {'hour': h, 'minute': m}, 'health': value, 'armour': 'full'}; any key may be missing."""
    ents, secs, gaps, head, tail = money._load(b)
    log = []
    i_simple, i_persist, i_spawn = money._sec(ents, SIMPLE), money._sec(ents, PERSIST), money._sec(ents, SPAWN)
    if edit.get('time'):
        h, m = int(edit['time'].get('hour', -1)), int(edit['time'].get('minute', -1))
        s = int(edit['time'].get('second', 0))
        if not (0 <= h <= 23 and 0 <= m <= 59 and 0 <= s <= 59):
            raise WorldError('bad_time')
        now = {k: _num(je.get(secs[i_simple], _code(SIMPLE) + [v])) for k, v in K.items()}
        for i, h_sec in ((i_simple, SIMPLE), (i_persist, PERSIST)):
            t = secs[i]
            for k, v in (('hour', h), ('minute', m), ('second', s)):
                t = je.put(t, _code(h_sec) + [K[k]], je.fmt_int(v))
            secs[i] = t
        epoch = calendar.timegm((now['year'], now['month'] + 1, now['day'], h, m, s))
        secs[i_spawn] = je.put(secs[i_spawn], _spawn() + [LAST_TIME], je.fmt_int(epoch))
        log.append({'what': 'world', 'label': 'Time of day', 'from': '%02d:%02d' % (now['hour'], now['minute']), 'to': '%02d:%02d' % (h, m)})
    if edit.get('health') is not None:
        v = float(edit['health'])
        if not 1 <= v <= HEALTH_MAX:
            raise WorldError('out_of_range')
        i = money._sec(ents, PED)
        old = _num(je.get(secs[i], _code(PED) + [HEALTH]))
        secs[i] = je.put(secs[i], _code(PED) + [HEALTH], je.fmt_float(v))
        log.append({'what': 'world', 'label': 'Health', 'from': old, 'to': v})
    if edit.get('armour') == 'full':
        i = money._sec(ents, LOOKS)
        t = secs[i]
        before = after = 0.0
        for c, _ in je.members(t, _code(LOOKS) + [OUTFITS]):
            for p, _ in je.members(t, _code(LOOKS) + [OUTFITS, c, ARMOUR_PARTS]):
                base = _code(LOOKS) + [OUTFITS, c, ARMOUR_PARTS, p]
                cur, mx = _num(je.get(t, base + [ARMOUR])), _num(je.get(t, base + [MAX_ARMOUR]))
                before += cur; after += max(cur, mx)
                if mx > cur:
                    t = je.put(t, base + [ARMOUR], je.fmt_float(mx))
        secs[i] = t
        log.append({'what': 'world', 'label': 'Armour', 'from': before, 'to': after})
    wanted = {k: v for k, v in edit.items() if '_' in k and k.partition('_')[0] in OWNERS}
    if wanted:
        ci, si = money._sec(ents, CHARACTER), money._sec(ents, fl.STATS)
        stats = fl.Stats(secs[si])
        available = growth_rows(secs[ci], stats)
        for key, value in wanted.items():
            if key not in available or type(value) is not int or not 0 <= value <= 100:
                raise WorldError('bad_request')
            old, label, path, index, qual, owner = available[key]
            if all(v == value for v in old):
                continue
            for offset in (index, index + 30):
                secs[ci] = je.put(secs[ci], path + [offset], je.fmt_int(value))
            for field in ('points', 'rank'):
                stats.set(field, qual, value, label, owner)
            log.append({'what': 'world', 'label': key.split('_')[0].title() + ' / ' + label, 'from': ' / '.join(map(str, old)), 'to': value})
        secs[si], _ = stats.apply()
    if not log:
        return b, log
    return money._rebuild(head, ents, secs, gaps, tail, len(b)), log
