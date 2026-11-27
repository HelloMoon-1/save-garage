# Save Garage - Copyright (C) 2026 NotHGM - GNU GPL v3 with the additional terms in NOTICE; see LICENSE.
"""Add the guns a character doesn't have yet, built the way the game writes a gun it gives you (Save Garage feature
module, shown on the Ammo tab).

WHAT IT CHANGES (inventory section d3f59a5e, Lucia's inventory 0 and Jason's inventory 1 only)
  For each chosen gun the character doesn't have (no row of that weapon in its weapons list, in any slot):
  * the weapons list (list 3, 14 columns): one row under the character's weapon container, at slotid_owned_weapons_0:
    Quantities 1, EquippedFlags false, DamageModes 0, AttachPoints 0xFFFFFFFF, $0x73d707b5 0, Locations 0,
    SourceLocations = the character's InventoryId, IsFavouriteFlags true, $0x0882cd47 true, $0x590ad213 false;
  * the main list: weaponkit_<gun>_001 under the weapon row, and under the kit one weaponmod_<gun>_<part>_regular_01
    row per part (gundata.RECIPES), each holding 1 and equipped, as the game writes a new gun's default parts;
  * ParentGuids: the new weapon and kit, each the parent of the rows under it (a knife's kit has none, so isn't added);
  * Items: (row << 4) | list for every new row;
  * OwnedWeaponsHistory: the weapon, in its sorted place, when it isn't there yet.
  Grenade and sticky bomb: the weapons-list row at slotid_unowned_weapons_0 (Locations = the InventoryId,
  SourceLocations 0) and the ammo row the game added with them, under the character: 5 grenades, 4 sticky bombs.
  They are left out of OwnedWeaponsHistory, as the game leaves them out.
  Compendium (dbf71c51): a weapon that isn't discovered yet is added with its counters (compendium.py), and the 100%
  figure is worked out again (checklist.py).

  New rows are appended with money.py's row helpers (_add_row, _parent_index, _fresh_guid), the mechanism the money
  boxes use; the weapons-list row is appended column by column the same way. Existing rows, their order and every
  other inventory are never changed: the inventory is checked before and after, and the edit is refused when it
  isn't exactly the old one plus the new rows.

EVIDENCE (dev_scratch/gen_gundata.py, 15 game-written saves)
  * Between A5as_mod and A6a the game added about 45 bought weapons. 47 of the 48 gun rows it wrote have exactly the
    column values above (the 48th was holstered straight away). Every gun got its _001 kit and default parts, and
    every gun (not the grenade or sticky bomb) was added to OwnedWeaponsHistory, which the game keeps sorted.
  * A gun is offered to a character only when that character had it in exactly that shape in a game save: 15 guns plus
    the grenade and sticky bomb for Lucia, 16 guns for Jason (gundata.LUCIA, gundata.JASON). Every such instance of a
    gun has the same kit and parts. Other guns were only seen with bought mods, mission or reward kits
    (gundata.NOT_OFFERED), so their default parts aren't known and they aren't offered.
  * Every weapon a character owns is discovered in the compendium in every save, and the purchase added the 13 that
    weren't. The purchase counters (numownedpurchased, spendweapons, ownednow) are not changed: no money is spent, and
    a gun the story gives you leaves them as they are.
  * Guns come without ammo: every ammo type already existed when the guns were bought, so whether the game adds ammo
    with a gun isn't known. The grenade and sticky bomb are their own ammo; the game never wrote one without the other.

CHECKED BEFORE AND AFTER (refused with FeatureError, nothing written)
  guns_layout: the inventory isn't shaped as above (InventoryId, list columns and their order, equal column lengths,
    one character root with one weapon container, a sorted OwnedWeaponsHistory).
  inventory_damaged: the save already breaks a rule the game keeps (a Guid used twice, Items not listing every row
    exactly once, a parent index that dangles, a ParentGuids entry with no child): the "Slam Dunk" case.
  item_limit: Items would pass ITEM_LIMIT - ITEM_RESERVE (4,095 less the 300 always left free, as in money.py).
  not_offered: a gun that can't be added to that character. bad_request: a choice that isn't understood.
  verify_failed: the result isn't the old inventory plus exactly the new rows.

RISK: experimental. Not tested on a PS5 yet.
"""
import json
import re
from collections import Counter

import featurelib as fl
import gundata
import itemnames
import money
import savedit

FEATURE = 'guns'
SEC = money.SEC_INV
J = money.joaat
M32 = fl.M32
K_INVS, K_INV_ID, K_HISTORY = '$0x789bdd41', '$0x3e226822', '$0x62edb0ef'
G, P, I, S, Q, F = money.K_GUID, money.K_PARENT, money.K_ITEM, money.K_SLOT, money.K_QTY, money.K_FLAG
DAMAGE, ATTACH, X73, LOCATIONS, SOURCES, FAVOURITE, X08, X59 = (
    '$0x4b22373a', '$0xc0251e62', '$0x73d707b5', '$0xce559722', '$0x37cd3fc1', '$0xc84eb3e9', '$0x0882cd47', '$0x590ad213')
LISTS = (money.K_MAIN,) + money.K_SUBLISTS                      # list numbers 1 to 5: main, vehicles, weapons, wardrobe, character
K_WEAPONS = money.K_SUBLISTS[1]
MAIN_COLUMNS = (G, P, I, S, Q, F)
WEAPON_COLUMNS = (G, P, I, S, Q, F, DAMAGE, ATTACH, X73, LOCATIONS, SOURCES, FAVOURITE, X08, X59)
BOOL_COLUMNS = {F, FAVOURITE, X08, X59}
CHARACTERS = (('lucia', 'Lucia', 0), ('jason', 'Jason', 1))
NAME = dict((k, n) for k, n, _ in CHARACTERS)
NTH = dict((k, i) for k, _, i in CHARACTERS)
INVENTORY_ID = {'lucia': 0xc0000002, 'jason': 0xc0000003}
ROOT_ITEM = J('character')
ROOT_SLOT = {'lucia': J('slotid_character_0'), 'jason': J('slotid_character_1')}
CONTAINER, CONTAINER_SLOT = J('weapon_container'), J('slotid_weapon_container')
OWNED_SLOT, UNOWNED_SLOT, AMMO_SLOT = J('slotid_owned_weapons_0'), J('slotid_unowned_weapons_0'), J('slotid_ammo')
OFFERED = {'lucia': gundata.LUCIA, 'jason': gundata.JASON}
ITEM_LIMIT, ITEM_RESERVE = money.ITEM_LIMIT, money.ITEM_RESERVE
_HEX = re.compile(r'(?:0x)?([0-9a-fA-F]{8})')
_HIST = re.compile(r'0x[0-9a-f]{8}')


def rows_of(spec):
    """Inventory rows one gun adds (each takes an Items entry)."""
    if spec in gundata.THROWN:
        return 2
    return 2 + len(gundata.RECIPES[spec][2])


def _label(spec):
    """(what the game calls the weapon, its kind when the name doesn't say it), as the Ammo tab shows weapons."""
    h = J(spec)
    kind = savedit.weapon_label(spec)
    label = itemnames.ITEM_LABELS.get(h)
    if not label:
        return kind, ''
    return label, ('' if kind.split(' ')[0].lower() in label.lower().replace(' ', '') else kind)


# ---------------------------------------------------------------- reading and checking one inventory
def _column(x, bools):
    """The values of one list column: a typed array {"$content": ..., "$data": [...]} or, for true/false, a bare list."""
    if bools:
        if not isinstance(x, list) or not all(isinstance(v, bool) for v in x):
            raise fl.FeatureError('guns_layout')
        return x
    if not isinstance(x, dict) or set(x) - {'$content', '$data'} or not isinstance(x.get('$data', []), list):
        raise fl.FeatureError('guns_layout')
    vals = x.get('$data', [])
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in vals):
        raise fl.FeatureError('guns_layout')
    return vals


def _view(inv, who):
    """Everything the edit needs from one character's inventory, after checking it. Raises FeatureError."""
    if not isinstance(inv, dict) or any(k not in inv for k in (K_INV_ID, money.K_ITEMS, money.K_PARENTS, K_HISTORY) + LISTS):
        raise fl.FeatureError('guns_layout')
    if not isinstance(inv[K_INV_ID], int) or inv[K_INV_ID] & M32 != INVENTORY_ID[who]:
        raise fl.FeatureError('guns_layout')
    rows = []
    for li, L in enumerate(LISTS, 1):
        obj = inv[L]
        if not isinstance(obj, dict) or any(k not in obj for k in MAIN_COLUMNS):
            raise fl.FeatureError('guns_layout')
        if (li == 1 and tuple(obj) != MAIN_COLUMNS) or (li == 3 and tuple(obj) != WEAPON_COLUMNS):
            raise fl.FeatureError('guns_layout')
        cols = {}
        for k, v in obj.items():
            if k in (G, P, I, S, Q) or li in (1, 3):    # the columns this edit reads or writes: their types too
                cols[k] = _column(v, k in BOOL_COLUMNS)
            elif isinstance(v, list):                   # other lists' own columns (names, flags): only their length
                cols[k] = v
            elif isinstance(v, dict) and isinstance(v.get('$data', []), list):
                cols[k] = v.get('$data', [])
            else:
                raise fl.FeatureError('guns_layout')
        n = len(cols[G])
        if any(len(v) != n for v in cols.values()):
            raise fl.FeatureError('guns_layout')
        for i in range(n):
            rows.append({'list': li, 'pos': i, 'guid': cols[G][i], 'parent': cols[P][i], 'item': cols[I][i] & M32, 'slot': cols[S][i] & M32})
    items = _column(inv[money.K_ITEMS], False)
    parents = _column(inv[money.K_PARENTS], False)
    guids = [r['guid'] for r in rows]
    if len(set(guids)) != len(guids) or len(set(parents)) != len(parents):
        raise fl.FeatureError('inventory_damaged')
    if len(items) > ITEM_LIMIT or Counter(items) != Counter((r['pos'] << 4) | r['list'] for r in rows):
        raise fl.FeatureError('inventory_damaged')
    known = set(guids)
    used = Counter()
    for r in rows:
        if not 0 <= r['parent'] < len(parents) or parents[r['parent']] not in known:
            raise fl.FeatureError('inventory_damaged')
        used[r['parent']] += 1
    if len(used) != len(parents):
        raise fl.FeatureError('inventory_damaged')               # a ParentGuids entry with nothing under it
    by_guid = {r['guid']: r for r in rows}
    for r in rows:
        r['parent_guid'] = parents[r['parent']]
    roots = [r for r in rows if r['list'] == 5 and r['item'] == ROOT_ITEM and r['slot'] == ROOT_SLOT[who]]
    if len(roots) != 1:
        raise fl.FeatureError('guns_layout')
    conts = [r for r in rows if r['list'] == 1 and r['item'] == CONTAINER and r['slot'] == CONTAINER_SLOT]
    if len(conts) != 1 or conts[0]['parent_guid'] != roots[0]['guid']:
        raise fl.FeatureError('guns_layout')
    hist = inv[K_HISTORY]
    if not isinstance(hist, list) or not all(isinstance(x, dict) and set(x) == {'$data'} and isinstance(x['$data'], str)
                                             and _HIST.fullmatch(x['$data']) for x in hist):
        raise fl.FeatureError('guns_layout')
    history = [int(x['$data'], 16) for x in hist]
    if history != sorted(set(history)):
        raise fl.FeatureError('guns_layout')
    weapons = {r['item'] for r in rows if r['list'] == 3}
    ammo = {r['item'] for r in rows if r['list'] == 1 and r['slot'] == AMMO_SLOT and r['parent_guid'] == roots[0]['guid']}
    return {'rows': rows, 'by_guid': by_guid, 'items': items, 'parents': parents, 'history': history, 'weapons': weapons,
            'ammo': ammo, 'root': roots[0]['guid'], 'container': conts[0]['guid']}


def _state(spec, view):
    """'owned' (the character has it), 'can_add', or 'ammo_only' (a thrown weapon's ammo row without its weapon row,
    which no save shows; left alone)."""
    if J(spec) in view['weapons']:
        return 'owned'
    if spec in gundata.THROWN and J(gundata.THROWN[spec][0]) in view['ammo']:
        return 'ammo_only'
    return 'can_add'


def _inventories(t):
    p = fl.payload(t, SEC)
    invs = p.get(K_INVS) if isinstance(p, dict) else None
    if not isinstance(invs, list) or len(invs) < 2:
        raise fl.FeatureError('guns_layout')
    return p, invs


# ---------------------------------------------------------------- read
def read(b):
    s = fl.Save(b)
    t = s.text(SEC)
    try:
        _, invs = _inventories(t)
    except (fl.FeatureError, ValueError, KeyError, TypeError):
        invs = None
    try:
        import compendium
        found = {h for h, _ in compendium._lists(s.text(compendium.SEC)).get(compendium.T_WEAPONS, [])}
    except Exception:
        found = None
    chars = []
    for who, name, nth in CHARACTERS:
        c = {'key': who, 'name': name, 'problem': None, 'offered': [], 'owned': [], 'left': [], 'items': None, 'itemsFree': None}
        try:
            if invs is None:
                raise fl.FeatureError('guns_layout')
            view = _view(invs[nth], who)
        except fl.FeatureError as e:
            c['problem'] = str(e)
            chars.append(c)
            continue
        c['items'] = len(view['items'])
        c['itemsFree'] = max(0, ITEM_LIMIT - ITEM_RESERVE - len(view['items']))
        for spec in OFFERED[who]:
            label, kind = _label(spec)
            entry = {'id': fl.hexid(J(spec)), 'name': spec, 'label': label, 'kind': kind, 'rows': rows_of(spec),
                     'thrown': spec in gundata.THROWN, 'ammo': gundata.THROWN.get(spec, (None, None))[1],
                     'discovered': None if found is None else J(spec) in found}
            state = _state(spec, view)
            c['offered' if state == 'can_add' else 'owned' if state == 'owned' else 'left'].append(entry)
        chars.append(c)
    return {'feature': FEATURE, 'characters': chars, 'itemLimit': ITEM_LIMIT, 'itemReserve': ITEM_RESERVE,
            'notOffered': {who: [dict(zip(('label', 'kind'), _label(sp)), id=fl.hexid(J(sp))) for sp in gundata.NOT_OFFERED[who]]
                           for who, _, _ in CHARACTERS},
            'risk': 'experimental'}


# ---------------------------------------------------------------- apply
def _choice(choice):
    """{character: ([weapon names], named one by one)} from {'lucia': [hex ids] | 'all', 'jason': ...}."""
    if not isinstance(choice, dict) or set(choice) - set(NTH):
        raise fl.FeatureError('bad_request')
    out = {}
    for who in NTH:
        want = choice.get(who)
        if want is None:
            continue
        by_id = {J(sp): sp for sp in OFFERED[who]}
        if want == 'all':
            out[who] = (list(OFFERED[who]), False)
            continue
        if not isinstance(want, list) or not all(isinstance(x, str) for x in want):
            raise fl.FeatureError('bad_request')
        specs = []
        for x in want:
            m = _HEX.fullmatch(x)
            if not m:
                raise fl.FeatureError('bad_request')
            sp = by_id.get(int(m.group(1), 16))
            if sp is None:
                raise fl.FeatureError('not_offered')
            if sp not in specs:
                specs.append(sp)
        out[who] = ([sp for sp in OFFERED[who] if sp in specs], True)  # in a fixed order, whatever order was asked
    return out


def _token(v):
    return b'true' if v is True else b'false' if v is False else b'%d' % v


def _member_span(t, nth, key):
    """(start, end) of one key's value in the nth inventory, found the way money.py finds its columns: the first such
    key after that inventory's main list (the key order is checked by _view, and the result by _verify)."""
    k = b'"%s":' % key.encode()
    vs = t.index(k, money._main(t, nth)) + len(k)
    if t[vs] not in b'{[':
        raise fl.FeatureError('guns_layout')
    return vs, fl.value_end(t, vs)


def _append_weapon_row(t, nth, values):
    """Append one row to the weapons list (all 14 columns) and register it in Items; returns (text, row)."""
    ws, _ = _member_span(t, nth, K_WEAPONS)
    mem = fl.members(t, ws)
    if tuple(k for k, _, _ in mem) != WEAPON_COLUMNS:
        raise fl.FeatureError('guns_layout')
    row = len(fl.typed_values(t, mem[0][1])[1])
    for k, vs, ve in reversed(mem):                     # the last column first, so the earlier spans stay where they are
        tok = _token(values[k])
        if t[vs] == ord('['):                           # a bare true/false list
            t = t[:ve - 1] + (b',' if ve - vs > 2 else b'') + tok + t[ve - 1:]
        else:
            t = fl.typed_append(t, vs, [tok])
    return money._append(t, nth, money.K_ITEMS, b'%d' % ((row << 4) | 3)), row


def _add_history(t, nth, specs):
    """Insert weapons into OwnedWeaponsHistory in their sorted places; the old entries stay byte for byte."""
    for h in sorted(specs):
        hs, he = _member_span(t, nth, K_HISTORY)
        els = fl.elements(t, hs)
        tok = b'{"$data":"0x%08x"}' % h
        pos = next((a for a, z in els if int(json.loads(t[a:z])['$data'], 16) > h), None)
        if pos is None:
            t = t[:he - 1] + (b',' if els else b'') + tok + t[he - 1:]
        else:
            t = t[:pos] + tok + b',' + t[pos:]
    return t


def _add_gun(t, nth, who, spec, view):
    """Append one gun's rows (money.py's helpers for the main list and ParentGuids); returns the text."""
    t, cidx = money._parent_index(t, nth, view['container'])
    g = money._fresh_guid(money._inventory(t, nth))
    thrown = spec in gundata.THROWN
    t, _ = _append_weapon_row(t, nth, {
        G: g, P: cidx, I: J(spec), S: UNOWNED_SLOT if thrown else OWNED_SLOT, Q: 1, F: False, DAMAGE: 0, ATTACH: M32, X73: 0,
        LOCATIONS: INVENTORY_ID[who] if thrown else 0, SOURCES: 0 if thrown else INVENTORY_ID[who],
        FAVOURITE: True, X08: True, X59: False})
    if thrown:                                          # the grenades or sticky bombs themselves, under the character
        ammo, amount = gundata.THROWN[spec]
        t, ridx = money._parent_index(t, nth, view['root'])
        t, _, _ = money._add_row(t, nth, money._inventory(t, nth), ridx, J(ammo), AMMO_SLOT, amount)
        return t
    kit, kit_slot, mods = gundata.RECIPES[spec]
    t, widx = money._parent_index(t, nth, g)
    t, _, kg = money._add_row(t, nth, money._inventory(t, nth), widx, J(kit), J(kit_slot), 1, equipped=True)
    if mods:
        t, kidx = money._parent_index(t, nth, kg)
        for mod, slot in mods:
            t, _, _ = money._add_row(t, nth, money._inventory(t, nth), kidx, J(mod), J(slot), 1, equipped=True)
    return t


def _expected(specs):
    """The new rows the edit must add, as (list, item, slot, what it hangs under), what it hangs under being the weapon
    container, the character, or the item of a new row."""
    out = []
    for spec in specs:
        if spec in gundata.THROWN:
            out += [(3, J(spec), UNOWNED_SLOT, 'container'), (1, J(gundata.THROWN[spec][0]), AMMO_SLOT, 'root')]
            continue
        kit, kit_slot, mods = gundata.RECIPES[spec]
        out += [(3, J(spec), OWNED_SLOT, 'container'), (1, J(kit), J(kit_slot), J(spec))]
        out += [(1, J(m), J(sl), J(kit)) for m, sl in mods]
    return sorted(out, key=repr)


def _verify(old_inv, new_inv, old_view, who, specs, history_add):
    """The new inventory is the old one plus exactly the new rows, Items entries, ParentGuids and history entries."""
    nv = _view(new_inv, who)                            # every rule still holds
    if set(new_inv) != set(old_inv) or list(new_inv) != list(old_inv):
        raise fl.FeatureError('verify_failed')
    for k in new_inv:
        if k not in LISTS + (money.K_ITEMS, money.K_PARENTS, K_HISTORY) and new_inv[k] != old_inv[k]:
            raise fl.FeatureError('verify_failed')
    old_rows = {(r['list'], r['pos']): r for r in old_view['rows']}
    added = []
    for r in nv['rows']:
        o = old_rows.get((r['list'], r['pos']))
        if o is None:
            added.append(r)
            continue
        if any(r[k] != o[k] for k in ('guid', 'parent', 'item', 'slot')):
            raise fl.FeatureError('verify_failed')
    for li, L in enumerate(LISTS, 1):                   # every old value of every column, and the old columns' types
        for k, v in old_inv[L].items():
            nvals = new_inv[L][k] if isinstance(v, list) else new_inv[L][k].get('$data', [])
            ovals = v if isinstance(v, list) else v.get('$data', [])
            if nvals[:len(ovals)] != ovals or (isinstance(v, dict) and v.get('$content') != new_inv[L][k].get('$content')):
                raise fl.FeatureError('verify_failed')
    if nv['items'][:len(old_view['items'])] != old_view['items'] or nv['parents'][:len(old_view['parents'])] != old_view['parents']:
        raise fl.FeatureError('verify_failed')
    new_guids = {r['guid']: r for r in added}

    def under(r):
        if r['parent_guid'] == old_view['container']:
            return 'container'
        if r['parent_guid'] == old_view['root']:
            return 'root'
        return new_guids[r['parent_guid']]['item'] if r['parent_guid'] in new_guids else None
    if sorted(((r['list'], r['item'], r['slot'], under(r)) for r in added), key=repr) != _expected(specs):
        raise fl.FeatureError('verify_failed')
    for r in added:                                     # the other columns of the new rows
        L = new_inv[LISTS[r['list'] - 1]]
        val = {k: (v if isinstance(v, list) else v['$data'])[r['pos']] for k, v in L.items()}
        if r['list'] == 1:
            thrown_ammo = r['slot'] == AMMO_SLOT
            want = {Q: next(a for sp, (it, a) in gundata.THROWN.items() if J(it) == r['item']) if thrown_ammo else 1, F: not thrown_ammo}
        else:
            thrown = r['slot'] == UNOWNED_SLOT
            want = {Q: 1, F: False, DAMAGE: 0, ATTACH: M32, X73: 0, LOCATIONS: INVENTORY_ID[who] if thrown else 0,
                    SOURCES: 0 if thrown else INVENTORY_ID[who], FAVOURITE: True, X08: True, X59: False}
        if any(val[k] != v for k, v in want.items()):
            raise fl.FeatureError('verify_failed')
    if nv['history'] != sorted(set(old_view['history']) | set(history_add)) or len(nv['history']) != len(old_view['history']) + len(history_add):
        raise fl.FeatureError('verify_failed')
    return nv


def apply(b, choice):
    """choice: {'lucia': [weapon ids (hex)] | 'all', 'jason': [...]} -> (new bytes, log). Guns a character already has
    are skipped, so applying the result again changes nothing."""
    want = _choice(choice)
    s = fl.Save(b)
    t = s.text(SEC)
    top, invs = _inventories(t)
    log, discovered = [], []
    plan = {}
    for who, (specs, named) in want.items():
        nth = NTH[who]
        view = _view(invs[nth], who)                    # refuse a layout or a damaged inventory before writing anything
        add = []
        for spec in specs:
            state = _state(spec, view)
            if state == 'ammo_only' and named:          # 'all' leaves it alone, as read() shows
                raise fl.FeatureError('not_offered')
            if state == 'can_add':
                add.append(spec)
        if not add:
            continue
        if len(view['items']) + sum(rows_of(sp) for sp in add) > ITEM_LIMIT - ITEM_RESERVE:
            raise fl.FeatureError('item_limit')
        plan[who] = (view, add)
    if not plan:
        return b, []
    t2 = t
    history = {}
    for who, (view, add) in plan.items():
        nth = NTH[who]
        for spec in add:
            t2 = _add_gun(t2, nth, who, spec, view)
        history[who] = [J(sp) for sp in add if sp not in gundata.THROWN and J(sp) not in view['history']]
        if history[who]:
            t2 = _add_history(t2, nth, history[who])
    # read back: every inventory but the edited ones as it was, and those exactly the old one plus the new rows
    top2, invs2 = _inventories(t2)
    if len(invs2) != len(invs) or {k: v for k, v in top2.items() if k != K_INVS} != {k: v for k, v in top.items() if k != K_INVS}:
        raise fl.FeatureError('verify_failed')
    for i, (a, z) in enumerate(zip(invs, invs2)):
        who = next((w for w, n in NTH.items() if n == i), None)
        if who not in plan:
            if a != z:
                raise fl.FeatureError('verify_failed')
            continue
        view, add = plan[who]
        hist = history[who]
        _verify(a, z, view, who, add, hist)
        labels = [_label(sp)[0] for sp in add]
        log.append({'what': 'guns', 'label': 'Guns added (%s)' % NAME[who], 'from': '', 'to': len(add), 'character': who,
                    'guns': [fl.hexid(J(sp)) for sp in add], 'names': labels, 'rows': sum(rows_of(sp) for sp in add),
                    'items': [len(view['items']), len(view['items']) + sum(rows_of(sp) for sp in add)], 'history': len(hist)})
        discovered += [sp for sp in add if sp not in discovered]
    s.set_text(SEC, t2)
    out = s.build()
    # the compendium: an owned weapon is always discovered; add the new ones it lacks, with their counters
    import checklist
    import compendium
    found = {h for h, _ in compendium._lists(fl.Save(out).text(compendium.SEC)).get(compendium.T_WEAPONS, [])}
    missing = [fl.hexid(J(sp)) for sp in discovered if J(sp) not in found]
    if missing:
        out, clog = compendium.apply(out, {'groups': ['weapons'], 'ids': missing})
        if not any(x.get('what') == 'compendium' and x.get('added') == len(missing) for x in clog):
            raise fl.FeatureError('verify_failed')
        log += [dict(x, what='completion', step=x.get('what')) if x.get('what') == 'compendium' else x for x in clog]
        out, klog = checklist.apply(out, {'overall': 'recompute'})
        log += [dict(x, what='completion', step=x.get('what'), label='100% completion') for x in klog]
    return out, log
