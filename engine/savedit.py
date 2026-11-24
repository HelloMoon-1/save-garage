"""Editing for decrypted GTA VI story saves beyond money: ammo and stats.

Works the same way as money.py: values are replaced in place inside a section's JSON text, so everything else
stays byte-for-byte as the game wrote it, and every edit is checked against the value it replaces.
All edits for a slot are applied together to the ORIGINAL decrypted file (money first, through money.patch),
so applying the same set twice gives the same file.

Stats section layout (worked out from real saves, see research notes):
  $0x7a47cb05.$0x0635cbd9.<group> holds four parallel arrays per typed group:
    $0x92f37a48 base-name index, $0x4d20ff5b qualifier index, $0x46be9d78 owner index, $0x450ce2f0 value.
  $0x50983a95 / $0x592f1d24 / $0xe93457ea are the base / qualifier / owner name tables (joaat hashes).
  Owner 0 is the game-wide total, 1 is Lucia, 2 is Jason. For most counters total = Lucia + Jason.
  Floats are written with six decimals ("32.670002"), bools as true/false.
"""
import json, math, re
from collections import namedtuple

import money
import statnames

M32 = 0xffffffff
joaat = money.joaat


class SaveError(money.SaveError):
    pass


# ---------------------------------------------------------------- stats
STAT_PATH = ('$0x7a47cb05', '$0x0635cbd9')
K_BASE, K_QUAL, K_OWNER, K_VAL = '$0x92f37a48', '$0x4d20ff5b', '$0x46be9d78', '$0x450ce2f0'
T_BASE, T_QUAL, T_OWNER = '$0x50983a95', '$0x592f1d24', '$0xe93457ea'
GROUP_TYPES = {
    '$0x085ee24c': 'int32', '$0x0d49085d': 'float', '$0x77096582': 'bool', '$0x21b27639': 'bool',
    '$0x456ae73c': 'u8', '$0xa17a2c2b': 'int16', '$0x40ee3695': 'u32', '$0x97232209': 'int64', '$0x35e4daa8': 'int64',
}
# Values are kept non-negative: no stat in a real save is negative, and counters below zero make no sense.
TYPE_RANGE = {'int32': (0, 2**31 - 1), 'u32': (0, 2**32 - 1), 'int64': (0, 2**63 - 1), 'int16': (0, 2**15 - 1),
              'u8': (0, 127), 'float': (0.0, 1e12)}
# Rows that money.py keeps in sync with the bank, savings and cash balances: never edited here.
MONEY_GROUP = '$0x97232209'
MONEY_BASES = (money.STAT_CHECKING, money.STAT_CASH_PLUS_CHECKING, money.STAT_SAVINGS, 265)
VAL_RE = re.compile(rb'"\$0x450ce2f0":(?:\{"\$content":"[a-z0-9_]+","\$data":)?\[')

_BASE_NAMES = {joaat(n): n for n in statnames.BASE_NAMES}
_QUAL_NAMES = {joaat(n): n for n in statnames.QUALIFIER_NAMES}
_OWNER_NAMES = {joaat(n): n for n in statnames.OWNER_NAMES}


def _arr(x):
    if isinstance(x, dict):
        return x.get('$data') or []
    return x or []


def stat_rows(sec_txt):
    """-> (groups, tables). groups: {key: {type, base, qual, owner, value}}; tables: {base, qual, owner} hash lists."""
    root = json.loads(sec_txt)[STAT_PATH[0]][STAT_PATH[1]]
    groups = {}
    for g, t in GROUP_TYPES.items():
        v = root.get(g)
        if not isinstance(v, dict):
            continue
        cols = [_arr(v.get(k)) for k in (K_BASE, K_QUAL, K_OWNER, K_VAL)]
        if any(len(c) != len(cols[0]) for c in cols):
            raise SaveError('layout_changed')
        groups[g] = {'type': t, 'base': cols[0], 'qual': cols[1], 'owner': cols[2], 'value': cols[3]}
    tables = {k: [h & M32 for h in _arr(root.get(key))] for k, key in (('base', T_BASE), ('qual', T_QUAL), ('owner', T_OWNER))}
    return groups, tables


def table_names(tables):
    """Readable names for the three name tables (None where unknown) and which of them are inferred."""
    base = [_BASE_NAMES.get(h) or statnames.INFERRED_BASE.get(h) for h in tables['base']]
    qual = [_QUAL_NAMES.get(h) or statnames.INFERRED_QUALIFIER.get(h) for h in tables['qual']]
    owner = [statnames.OWNER_LABELS.get(i) or _OWNER_NAMES.get(h) for i, h in enumerate(tables['owner'])]
    inferred = {'base': [i for i, h in enumerate(tables['base']) if h not in _BASE_NAMES and h in statnames.INFERRED_BASE],
                'qual': [i for i, h in enumerate(tables['qual']) if h not in _QUAL_NAMES and h in statnames.INFERRED_QUALIFIER]}
    return {'base': base, 'qual': qual, 'owner': owner, 'inferred': inferred}


def is_protected(group, base_index):
    return group == MONEY_GROUP and base_index in MONEY_BASES


def _fmt(t, v):
    if t == 'bool':
        return b'true' if v else b'false'
    if t == 'float':
        return b'%.6f' % v
    return b'%d' % v


def _parse_tok(t, tok):
    tok = tok.strip()
    if t == 'bool':
        if tok in (b'true', b'false'):
            return tok == b'true'
        raise SaveError('verify_failed')
    return float(tok) if t == 'float' else int(tok)


def _same(t, a, b):
    if t == 'bool':
        return bool(a) == bool(b)
    if t == 'float':
        return abs(float(a) - float(b)) <= max(1e-6, abs(float(b)) * 1e-6)
    return int(a) == int(b)


def coerce(t, v):
    """Check a new value against the stat's type and return it in the right Python type."""
    if t == 'bool':
        if isinstance(v, bool):
            return v
        if v in (0, 1):
            return bool(v)
        raise SaveError('bad_value')
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise SaveError('bad_value')
    lo, hi = TYPE_RANGE[t]
    if t == 'float':
        f = float(v)
        if not math.isfinite(f) or not lo <= f <= hi:
            raise SaveError('out_of_range')
        return f
    if isinstance(v, float) and not v.is_integer():
        raise SaveError('bad_value')
    i = int(v)
    if not lo <= i <= hi:
        raise SaveError('out_of_range')
    return i


def _val_span(txt, group, count):
    """(start, end) of the value array of one stats group inside the section text."""
    key = b'"%s":' % group.encode()
    g = txt.find(key)
    if g < 0 or txt.find(key, g + 1) >= 0:
        raise SaveError('layout_changed')
    k = txt.find(b'"$0x450ce2f0":', g)
    m = VAL_RE.match(txt, k) if k >= 0 else None
    if not m:
        raise SaveError('layout_changed')
    s = m.end()
    e = txt.index(b']', s)
    if (txt[s:e].count(b',') + 1 if e > s else 0) != count:
        raise SaveError('layout_changed')
    return s, e


def _apply_stats(txt, changes):
    groups, _ = stat_rows(txt)
    final, explicit_total, log = {}, set(), []
    for ch in changes:
        g = ch.get('group')
        G = groups.get(g)
        r = int(ch['row'])
        if not G or not 0 <= r < len(G['value']):
            raise SaveError('stale_item')
        if (G['base'][r], G['qual'][r], G['owner'][r]) != (int(ch['base']), int(ch['qual']), int(ch['owner'])):
            raise SaveError('stale_item')
        if not _same(G['type'], G['value'][r], ch['value']):
            raise SaveError('stale_item')
        if is_protected(g, G['base'][r]):
            raise SaveError('protected_stat')
        nv = coerce(G['type'], ch['newValue'])
        if _same(G['type'], nv, G['value'][r]):
            continue
        final[(g, r)] = nv
        if G['owner'][r] == 0:
            explicit_total.add((g, r))
        log.append({'what': 'stat', 'group': g, 'row': r, 'label': ch.get('label') or '', 'from': G['value'][r], 'to': nv})

    # Keep the game-wide total (owner 0) equal to Lucia + Jason, but only where it was equal before the edit.
    where = {}
    for g, G in groups.items():
        for r in range(len(G['value'])):
            where[(g, G['base'][r], G['qual'][r], G['owner'][r])] = r
    for (g, r) in list(final):
        G = groups[g]
        if G['type'] == 'bool' or G['owner'][r] not in (1, 2):
            continue
        k = (g, G['base'][r], G['qual'][r])
        r0, r1, r2 = (where.get(k + (o,)) for o in (0, 1, 2))
        if None in (r0, r1, r2) or (g, r0) in explicit_total:
            continue
        v0, v1, v2 = (G['value'][x] for x in (r0, r1, r2))
        if not _same(G['type'], v0, v1 + v2):
            continue
        total = coerce(G['type'], final.get((g, r1), v1) + final.get((g, r2), v2))
        if not _same(G['type'], total, v0):
            final[(g, r0)] = total
            log.append({'what': 'stat_total', 'group': g, 'row': r0, 'from': v0, 'to': total})

    for g in sorted({g for g, _ in final}):
        G = groups[g]
        s, e = _val_span(txt, g, len(G['value']))
        toks = txt[s:e].split(b',')
        for (gg, r), nv in final.items():
            if gg != g:
                continue
            if not _same(G['type'], _parse_tok(G['type'], toks[r]), G['value'][r]):
                raise SaveError('verify_failed')
            toks[r] = _fmt(G['type'], nv)
        txt = txt[:s] + b','.join(toks) + txt[e:]
    return txt, log


# ---------------------------------------------------------------- ammo
AMMO_TYPES = ('pistol', 'revolver', 'smg', 'rifle', 'shotgun', 'sniper', 'marksman', 'mg', 'minigun', 'sporting',
              'thrown_grenade')
AMMO_ITEMS = {joaat('ammo_' + t): t for t in AMMO_TYPES}
SLOT_AMMO = joaat('slotid_ammo')
# Highest amounts seen in real saves. The game probably cuts anything above its own limit back on load.
AMMO_SEEN_MAX = {'rifle': 300, 'smg': 300, 'minigun': 300, 'sporting': 200, 'marksman': 120, 'pistol': 100,
                 'revolver': 100, 'shotgun': 100}
AMMO_MAX = 9999


def ammo(sec_txt):
    """Ammo rows the two protagonists currently carry. inv 0 = Lucia, inv 1 = Jason."""
    root = json.loads(sec_txt)['$0x7a47cb05']['$0xd3f59a5e']['$0x789bdd41']
    out = []
    for n in range(min(2, len(root))):
        v = money._inventory(sec_txt, n)
        for r, item in enumerate(v['item']):
            if item & M32 in AMMO_ITEMS and v['slot'][r] & M32 == SLOT_AMMO:
                out.append({'inv': n, 'idx': r, 'type': AMMO_ITEMS[item & M32], 'value': v['qty'][r]})
    return out


def _apply_ammo(txt, changes):
    current = {(a['inv'], a['idx']): a for a in ammo(txt)}
    log = []
    for ch in changes:
        a = current.get((int(ch['inv']), int(ch['idx'])))
        if not a or a['value'] != ch['value']:
            raise SaveError('stale_item')
        nv = ch['newValue']
        if isinstance(nv, bool) or not isinstance(nv, (int, float)) or (isinstance(nv, float) and not nv.is_integer()):
            raise SaveError('bad_value')
        nv = int(nv)
        if not 1 <= nv <= AMMO_MAX:
            raise SaveError('out_of_range')
        if nv == a['value']:
            continue
        txt = money._set(txt, money._qty_span(txt, a['inv']), a['idx'], a['value'], nv)
        log.append({'what': 'ammo', 'inv': a['inv'], 'type': a['type'], 'from': a['value'], 'to': nv})
    return txt, log


# ---------------------------------------------------------------- whole-file
def apply(b, edits):
    """edits: {'money': [...], 'ammo': [...], 'stats': [...]} applied to the original file -> (bytes, log)."""
    log = []
    if edits.get('money'):
        try:
            b, mlog = money.patch(b, edits['money'])
        except money.SaveError as e:
            raise SaveError(str(e))
        log += [dict(x, what='money' if x.get('what') == 'inventory' else x.get('what')) for x in mlog]
    if not edits.get('ammo') and not edits.get('stats'):
        return b, log
    ents, secs, gaps, head, tail = money._load(b)
    try:
        if edits.get('ammo'):
            i = money._sec(ents, money.SEC_INV)
            secs[i], alog = _apply_ammo(secs[i], edits['ammo'])
            log += alog
        if edits.get('stats'):
            i = money._sec(ents, money.SEC_STAT)
            secs[i], slog = _apply_stats(secs[i], edits['stats'])
            log += slog
        return money._rebuild(head, ents, secs, gaps, tail, len(b)), log
    except (KeyError, ValueError, IndexError, TypeError) as e:
        raise SaveError('bad_request') from e


def section(b, sec_hash):
    ents, secs, _, _, _ = money._load(b)
    return secs[money._sec(ents, sec_hash)]


# ---------------------------------------------------------------- featured stats for the editor UI
Spec = namedtuple('Spec', 'id category label help risk unit base qual owners')
LUCIA_JASON = (0, 1, 2)
STARS = lambda n: '%d star%s' % (n, '' if n == 1 else 's')
TROPHY_NOTE = ''          # the shared warning for trophy counters is shown once, in the UI's section intro
FEATURED = [
    Spec('story_pct', 'progress', 'Story completion', 'The percentage on the stats screen. Changing it does not unlock or skip missions.', 'caution', 'percent', 0xd3526971, 'story', (0,)),
    Spec('styles_pct', 'progress', 'Second completion percentage', 'Shown next to story completion. Likely outfits and styles collected.', 'caution', 'percent', 0xd3526971, 'styles', (0,)),
    Spec('side_tasks', 'progress', 'Side tasks completed', 'Side tasks finished.', 'caution', 'count', 'sidetaskscompleted', 0, LUCIA_JASON),
    Spec('health_level', 'fitness', 'Health level', 'Health skill level. Tested on PS5: the game keeps an edited level.', 'tested', 'level', 0xdef0d42f, 'health', LUCIA_JASON),
    Spec('stamina_level', 'fitness', 'Stamina level', 'Stamina skill level. Tested on PS5: the game keeps an edited level.', 'tested', 'level', 0xdef0d42f, 'stamina', LUCIA_JASON),
    Spec('health_points', 'fitness', 'Health points', 'Points earned toward the next health level.', 'tested', 'count', 0x53f5b035, 'health', LUCIA_JASON),
    Spec('stamina_points', 'fitness', 'Stamina points', 'Points earned toward the next stamina level.', 'caution', 'count', 0x53f5b035, 'stamina', LUCIA_JASON),
    Spec('workouts', 'fitness', 'Workouts completed', 'Gym workouts finished.', 'caution', 'count', 'numworkoutscompleted', 0, LUCIA_JASON),
    Spec('meditations', 'fitness', 'Meditations', 'Meditation sessions.', 'caution', 'count', 'totalmeditations', 0, LUCIA_JASON),
    Spec('time_onfoot', 'time', 'Time on foot', 'Time spent out of vehicles.', 'caution', 'ms', 'time', 'travelledfoot', LUCIA_JASON),
    Spec('time_invehicle', 'time', 'Time in vehicles', 'Time spent in any vehicle.', 'caution', 'ms', 'time', 'invehicle', LUCIA_JASON),
    Spec('dist_total', 'time', 'Distance travelled', 'All distance, on foot and in vehicles.', 'caution', 'distance', 'dist', 'travelled', LUCIA_JASON),
    Spec('dist_onfoot', 'time', 'Distance on foot', 'Distance covered out of vehicles.', 'caution', 'distance', 'dist', 'travelledfoot', LUCIA_JASON),
    Spec('dist_invehicle', 'time', 'Distance in vehicles', 'Distance covered in any vehicle.', 'caution', 'distance', 'dist', 'invehicle', LUCIA_JASON),
] + [Spec('time_' + q, 'time', 'Time spent ' + label, 'Recorded time for this activity.', 'caution', 'ms', 'time', q, LUCIA_JASON)
     for q, label in (('walking', 'walking'), ('jogging', 'jogging'), ('running', 'running'), ('sprinting', 'sprinting'),
                      ('swimming', 'swimming'), ('underwater', 'underwater'), ('aircraft', 'flying'), ('watercraft', 'on boats'),
                      ('stealth', 'in stealth'), ('cover', 'in cover'), ('parachute', 'parachuting'), ('dancing', 'dancing'))] + [
    Spec('earned_' + q, 'earnings', label, 'A record of money earned. It does not add money: use the Money tab for that.', 'tested', 'money', 0xd5188146, q, LUCIA_JASON)
    for q, label in (('buckme', 'Earned through BuckMe'), ('tasks', 'Earned from tasks'), ('robberies', 'Earned from robberies'),
                     ('safe', 'Taken from safes'), ('till', 'Taken from tills'), ('pickups', 'Picked up'))] + [
    Spec('wanted_any', 'wanted', 'Wanted levels escaped', 'How often you got away from the police.', 'caution', 'count', 'evadedwantedlevel', 'any', LUCIA_JASON),
] + [Spec('wanted_l%d' % n, 'wanted', 'Escaped at ' + STARS(n), 'How often you got away at this wanted level.', 'caution', 'count', 'evadedwantedlevel', 'level%d' % n, LUCIA_JASON) for n in range(1, 7)] + [
    Spec('wanted_time_any', 'wanted', 'Time wanted', 'Total time with a wanted level.', 'caution', 'ms', 'timeinwantedlevel', 'any', LUCIA_JASON),
] + [Spec('wanted_time_l%d' % n, 'wanted', 'Time at ' + STARS(n), 'Total time spent at this wanted level.', 'caution', 'ms', 'timeinwantedlevel', 'level%d' % n, LUCIA_JASON) for n in range(1, 7)] + [
    Spec('kills', 'records', 'Kills', 'Combat record.', 'caution', 'count', 'kills', 0, LUCIA_JASON),
    Spec('headshots', 'records', 'Headshots', 'Combat record.', 'caution', 'count', 'headshots', 0, LUCIA_JASON),
    Spec('shots', 'records', 'Shots fired', 'Combat record.', 'caution', 'count', 'shots', 0, LUCIA_JASON),
    Spec('deaths', 'records', 'Deaths', 'How often you were killed.', 'caution', 'count', 'deaths', 0, LUCIA_JASON),
    Spec('busted', 'records', 'Times busted', 'How often you were arrested.', 'caution', 'count', 'busted', 0, LUCIA_JASON),
    Spec('carjackings', 'records', 'Carjackings', 'Vehicle record.', 'caution', 'count', 'carjackings', 0, LUCIA_JASON),
    Spec('holdups', 'records', 'Holdups', 'Store holdups.', 'caution', 'count', 'holdups', 0, LUCIA_JASON),
    Spec('fish', 'records', 'Fish caught', 'Fishing record.', 'caution', 'count', 'kills', 'fish', LUCIA_JASON),
    Spec('photo_animal', 'records', 'Animals photographed', 'Wildlife photos taken.', 'caution', 'count', 'photographed', 'animal', LUCIA_JASON),
    Spec('rentals', 'records', 'Vehicle rentals', 'Vehicles rented.', 'caution', 'count', 'numpurchased', 'rentals', LUCIA_JASON),
    Spec('taxis', 'records', 'Taxi rides', 'Taxis paid for.', 'caution', 'count', 'numpurchased', 'taxis', LUCIA_JASON),
    Spec('masks', 'records', 'Masks used', 'How often you put on a mask.', 'caution', 'count', 'numtimesused', 'masks', LUCIA_JASON),
    Spec('armor', 'records', 'Armor used', 'How often you put on body armor.', 'caution', 'count', 'numtimesused', 'armor', LUCIA_JASON),
    Spec('fenced_packages', 'records', 'Packages fenced', 'Items sold to fences.', 'caution', 'count', 'fenced', 'packages', LUCIA_JASON),
    Spec('fenced_doubloons', 'records', 'Doubloons fenced', 'Items sold to fences.', 'caution', 'count', 'fenced', 'doubloons', LUCIA_JASON),
    Spec('fenced_meteorites', 'records', 'Meteorites fenced', 'Items sold to fences.', 'caution', 'count', 'fenced', 'meteorites', LUCIA_JASON),
    Spec('stunts_total', 'trophies', 'Stunts completed', 'All stunts together.' + TROPHY_NOTE, 'danger', 'count', 'stuntscompleted', 'totalstunts', (0,)),
    Spec('stunt_jumps', 'trophies', 'Stunt jumps', 'Stunt jumps completed.' + TROPHY_NOTE, 'danger', 'count', 'stuntscompleted', 'stuntjumps', (0,)),
    Spec('base_jumps', 'trophies', 'Base jumps', 'Base jumps completed.' + TROPHY_NOTE, 'danger', 'count', 'stuntscompleted', 'basejumps', (0,)),
    Spec('knife_flights', 'trophies', 'Knife flights', 'Knife flights completed.' + TROPHY_NOTE, 'danger', 'count', 'stuntscompleted', 'knifeflights', (0,)),
    Spec('challenges', 'trophies', 'Challenges completed', 'All challenges together.' + TROPHY_NOTE, 'danger', 'count', 'challengescompleted', 0, (0,)),
    Spec('discoverables', 'trophies', 'Discoverables found', 'Places and things discovered.' + TROPHY_NOTE, 'danger', 'count', 'discoverablesfound', 0, (0,)),
    Spec('collectibles', 'trophies', 'Collectibles collected', 'The collectibles counter.' + TROPHY_NOTE, 'danger', 'count', 'numcollected', 'collectibles', (0,)),
    Spec('collectible_cards', 'trophies', 'Collectible cards', 'Cards collected.' + TROPHY_NOTE, 'danger', 'count', 'numcollected', 'collectiblecards', (0,)),
    Spec('collectible_sets', 'trophies', 'Complete collectible sets', 'Finished collectible sets.' + TROPHY_NOTE, 'danger', 'count', 'numcollected', 'allsets', (0,)),
    Spec('vaults', 'trophies', 'Vaults robbed', 'Vaults robbed so far.' + TROPHY_NOTE, 'danger', 'count', 'robbedvaults', 0, (0,)),
] + [Spec('gadget_' + q, 'gadgets', label, 'Marks the gadget as obtained. It may not put the gadget in your inventory.', 'tested' if q == 'headphones' else 'caution', 'flag', 'acquired', q, (0, 1, 2))
     for q, label in (('metaldetector', 'Metal detector'), ('binoculars', 'Binoculars'), ('flashlight', 'Flashlight'),
                      ('masks', 'Masks'), ('headphones', 'Headphones'))]


# ---------------------------------------------------------------- weapons each character carries (read only)
import itemnames
_ITEMS = {joaat(n): n for n in itemnames.ITEM_NAMES}
_WEAPON_GROUP = {'pistol': 'pistol', 'revolver': 'revolver', 'smg': 'SMG', 'autorifle': 'rifle', 'tacrifle': 'tactical rifle', 'shotgun': 'shotgun',
                 'sniper': 'sniper rifle', 'launched': 'launcher'}
_WEAPON_WORD = {'fiftycal': '.50', 'combatpdw': 'combat PDW', 'combatmg': 'combat MG', 'pumpaction': 'pump-action', 'sbs': 'short-barrel',
                'hunter': 'hunting', 'unarmed': 'fists'}


def weapon_label(name):
    """weaponspec_autorifle_assault_default -> 'Assault rifle'."""
    parts = name.split('_')
    if len(parts) < 3 or parts[0] != 'weaponspec':
        return name
    group, word = parts[1], parts[2] if len(parts) > 3 or parts[1] != 'unarmed' else 'unarmed'
    variant = parts[3] if len(parts) > 3 else 'default'
    text = ' '.join(x for x in (_WEAPON_WORD.get(word, word), _WEAPON_GROUP.get(group, '')) if x)
    if variant not in ('default', group):
        text += ' (%s)' % variant
    return text[:1].upper() + text[1:]


def weapons(sec_txt):
    """Weapons in each protagonist's weapon list: [{inv, id, name, label}]. inv 0 = Lucia, inv 1 = Jason."""
    root = json.loads(sec_txt)['$0x7a47cb05']['$0xd3f59a5e']['$0x789bdd41']
    out = []
    for n in range(min(2, len(root))):
        seen = set()
        for it in _arr((root[n].get('$0xc500ddf4') or {}).get('$0xbe8e255c')):
            h = it & M32
            if h in seen:
                continue
            seen.add(h)
            name = _ITEMS.get(h)
            out.append({'inv': n, 'id': '%08x' % h, 'name': name, 'label': weapon_label(name) if name else 'Unknown weapon'})
    return out


def _h(x):
    return joaat(x) if isinstance(x, str) else x


def featured(sec_txt):
    """Featured stats present in this save, with the exact rows to edit."""
    groups, tables = stat_rows(sec_txt)
    bidx = {h: i for i, h in enumerate(tables['base'])}
    qidx = {h: i for i, h in enumerate(tables['qual'])}
    where = {}
    for g, G in groups.items():
        for r in range(len(G['value'])):
            where[(G['base'][r], G['qual'][r], G['owner'][r])] = (g, r)
    out = []
    for spec in FEATURED:
        b, q = bidx.get(_h(spec.base)), qidx.get(_h(spec.qual))
        if b is None or q is None:
            continue
        entries = []
        for o in spec.owners:
            loc = where.get((b, q, o))
            if not loc:
                continue
            g, r = loc
            G = groups[g]
            if is_protected(g, b):
                continue
            entries.append({'owner': o, 'group': g, 'row': r, 'base': b, 'qual': q, 'type': G['type'], 'value': G['value'][r]})
        if not entries:
            continue
        vals = {e['owner']: e['value'] for e in entries}
        auto = (entries[0]['type'] != 'bool' and {0, 1, 2} <= set(vals) and _same(entries[0]['type'], vals[0], vals[1] + vals[2]))
        out.append({'id': spec.id, 'category': spec.category, 'label': spec.label, 'help': spec.help, 'risk': spec.risk,
                    'unit': spec.unit, 'autoTotal': bool(auto), 'entries': entries})
    return out


def stats_table(sec_txt):
    """Every stat row (compact columns) with readable names, for the full stats browser."""
    groups, tables = stat_rows(sec_txt)
    return {'groups': [{'key': g, 'type': G['type'], 'base': G['base'], 'qual': G['qual'], 'owner': G['owner'], 'value': G['value']}
                       for g, G in groups.items() if G['value']],
            'names': table_names(tables),
            'protected': {MONEY_GROUP: list(MONEY_BASES)}}
