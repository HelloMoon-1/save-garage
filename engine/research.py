"""Research-backed story save fields shared by the editor and the patch writer."""
import json
import re
from datetime import datetime, timezone

import collectibles2
import featurelib as fl
import fog_regions
import hashnames
import jsonedit as je
import money
import savekeys
import savedit

FOG, CHARACTER = 0x6ac593ca, 0x22a87829
REGIONS, REGION_ID, REGION_TYPE = '$0x31bfd061', '$0xbf2c8a79', fl.key('regionType')
PLAYERS = {fl.key(n)[1:]: n.title() for n in ('lucia', 'jason')}
TRUNK = fl.h('slotid_trunk')
TRUNK_LIMITS = {0x961ede90: 4, 0xc7e59bac: 2}


def saved_time(s, add):
    stamp = collectibles2._save_time(s)
    add('Save time', 'Game save timestamp', datetime.fromtimestamp(stamp, timezone.utc).isoformat())


def ped_fields(s, add):
    ped = fl.payload(s.text(fl.h('PlayerPed')), fl.h('PlayerPed'))
    for axis, coord in ped.get(fl.key('Position'), {}).items():
        add('Player attributes', 'Position / ' + axis, coord)


def player_fields(s, add):
    ch = fl.payload(s.text(CHARACTER), CHARACTER)
    cp = [fl.CODE, fl.key(CHARACTER)]
    lo, hi = (ch.get(fl.key(k)) for k in ('relationshipScriptLowerCap', 'relationshipScriptCap'))
    for name in ('relationship', 'relationshipLevel', 'relationshipJason', 'relationshipLucia',
                 'relationshipLocked', 'relationshipDisabled', 'relationshipScriptLowerCap', 'relationshipScriptCap'):
        k = fl.key(name)
        if k not in ch:
            continue
        if (name == 'relationship' and type(lo) is int and type(hi) is int and lo <= ch[k] <= hi
                and not ch.get(fl.key('relationshipLocked')) and not ch.get(fl.key('relationshipDisabled'))):
            add('Relationship', name, ch[k], 'research_relationship', lo, hi, (CHARACTER, cp + [k]))
        else:
            add('Relationship', name, ch[k])
    for player in ch.get(fl.key('attributeSet'), []):
        name = PLAYERS.get(player.get(fl.key('Name'), {}).get('$data'))
        if name and '$0x177caa16' in player:
            add('Criminal profile', name + ' · 0x177CAA16', player['$0x177caa16'])
        if name:
            for i, n in enumerate(player.get(fl.key('attributes'), {}).get('$data', [])):
                add('Player attributes', name + ' · [' + str(i) + ']', n)


def map_fields(s, add):
    fog = fl.payload(s.text(FOG), FOG)
    entries = fog.get(REGIONS, [])
    found = {x[REGION_ID]: x[REGION_TYPE] for x in entries}
    valid = fog.get(fl.key('dataVersion')) == 9 and len(entries) == len(found)
    valid = valid and all(found.get(i, typ) == typ for typ, ids in fog_regions.OBSERVED.items() for i in ids)
    for typ, ids in fog_regions.OBSERVED.items():
        count = sum(i in found for i in ids)
        label = 'Named regions' if typ == 2 else 'Type 1 regions'
        if valid and count < len(ids):
            add('Map fog', label, count, 'research_fog_' + str(typ), len(ids), len(ids), ('fog', (typ, None)))
        else:
            add('Map fog', label, count)
    for i, typ in found.items():
        name = (hashnames.lookup(i) or {}).get('text', '0x%08X' % i)
        add('Region IDs', name + ' / ' + str(typ), 1)
    if valid:
        for typ, ids in fog_regions.OBSERVED.items():
            for i in ids:
                if i not in found:
                    name = (hashnames.lookup(i) or {}).get('text', '0x%08X' % i)
                    add('Region IDs', name + ' / ' + str(typ), 0, 'research_region_%08x' % i, 1, 1,
                        ('fog', (typ, i)))


def ledger_fields(s, add):
    book = json.loads(s.text(money.SEC_LEDGER))['$0x24d043f2'][fl.key(money.SEC_LEDGER)]['$0x45a134ec']
    for k, label in ((money.LEDGER_CHECKING, 'Checking'), (money.LEDGER_SAVINGS, 'Savings')):
        for r in book.get(k, []):
            add('Bank transactions', '%s #%s · %08X' % (label, r[money.K_ENTRY], r[money.K_OWNER]),
                '%+d → %d' % (r[money.K_DELTA], r[money.K_BALANCE]))
            for field, value in r.items():
                name = savekeys.KEY_NAMES.get(int(field[1:], 16), field) if field.startswith('$0x') else field
                if isinstance(value, dict) and set(value) == {'$data'}:
                    value = value['$data']
                add('Transaction details', f"{label} #{r[money.K_ENTRY]} / {name}",
                    json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else value)


def vehicle_fields(s, add):
    vehicles = fl.payload(s.text(fl.h('Vehicles')), fl.h('Vehicles')).get(fl.key('vehicles'), [])
    plates = {}
    for car in vehicles:
        blob = bytes(car.get('$0x08ccb621', {}).get('$data', []))
        found_plates = {v.decode('ascii').strip() for v in re.findall(rb'\x00{3}([A-Z0-9 ]{8})(?=\xff{4}|\x08\x00\x00\x00)', blob) if v.strip()}
        vid = car.get(fl.key('id'))
        if vid is not None:
            plates[vid & fl.M32] = next(iter(found_plates)) if len(found_plates) == 1 else None
            add('Vehicle records', '0x%08X' % (vid & fl.M32), plates[vid & fl.M32] or '—')
    inventories = fl.payload(s.text(money.SEC_INV), money.SEC_INV)[fl.key('Inventories')]
    for n, inv in enumerate(inventories):
        parents = money._data(inv[money.K_PARENTS])
        children = {}
        for group in (money.K_MAIN, *money.K_SUBLISTS):
            cols = [money._data(inv[group][k]) for k in (money.K_GUID, money.K_PARENT, money.K_ITEM, money.K_SLOT, money.K_QTY)]
            for ix, (guid, parent, item, slot, qty) in enumerate(zip(*cols)):
                if 0 <= parent < len(parents):
                    children[guid] = (parents[parent], item & fl.M32, slot & fl.M32, qty, group, ix)
        for guid, (parent, item, slot, qty, group, index) in children.items():
            seen = {guid}
            while parent in children and parent not in seen:
                seen.add(parent)
                ancestor = children[parent]
                if ancestor[2] == TRUNK:
                    vehicle = children.get(ancestor[0])
                    title = 'Lucia' if n == 0 else 'Jason'
                    if vehicle and vehicle[4] == '$0x6ebbccb1':
                        ids = money._data(inv[vehicle[4]]['$0xd65b1f97'])
                        vid = ids[vehicle[5]] & fl.M32
                        title += ' / ' + (plates.get(vid) or '0x%08X' % vid)
                    title += ' / ' + ((hashnames.lookup(item) or {}).get('text') or '0x%08X' % item)
                    if item in TRUNK_LIMITS and qty > 0:
                        path = [fl.CODE, fl.key(money.SEC_INV), fl.key('Inventories'), n, group, money.K_QTY, '$data', index]
                        add('Trunk contents', title, qty, 'research_cargo_%d_%x_%x' % (n, guid, item),
                            1, max(qty, TRUNK_LIMITS[item]), (money.SEC_INV, path))
                    else:
                        add('Trunk contents', title, qty)
                    break
                parent = ancestor[0]


READERS = (
    ('Save time', saved_time),
    ('Player attributes', ped_fields),
    ('Relationship', player_fields),
    ('Map fog', map_fields),
    ('Bank transactions', ledger_fields),
    ('Vehicle records', vehicle_fields),
)


def describe(s):
    rows, writes = [], {}

    def add(group, label, value, key=None, low=None, high=None, target=None, **extra):
        row = dict(group=group, label=label, value=value, **extra)
        if key is not None:
            row.update(key=key, min=low, max=high)
            writes[key] = (row, target)
        rows.append(row)

    for group, reader in READERS:
        try:
            reader(s, add)
        except (KeyError, IndexError, TypeError, ValueError, money.SaveError):
            add(group, 'Unavailable in this save layout', '—')
    return rows, writes


def read(b):
    return describe(fl.Save(b))[0]


def apply(b, edits):
    s = fl.Save(b)
    _, writes = describe(s)
    log = []
    for key, value in edits.items():
        if key not in writes:
            raise ValueError('stale_item')
        row, (sec, path) = writes[key]
        if type(value) is not int or not row['min'] <= value <= row['max']:
            raise ValueError('out_of_range')
        if value == row['value']:
            continue
        if sec == 'fog':
            text = s.text(FOG)
            obj = fl.payload(text, FOG)
            found = {x[REGION_ID] for x in obj[REGIONS]}
            typ, region = path
            candidates = fog_regions.OBSERVED[typ] if region is None else (region,)
            missing = [{REGION_ID: i, REGION_TYPE: typ} for i in candidates if i not in found]
            if not missing:
                continue
            _, end = je.find(text, [fl.CODE, fl.key(FOG), REGIONS])
            tokens = json.dumps(missing, separators=(',', ':')).encode()[1:-1]
            s.set_text(FOG, text[:end-1] + (b',' if found else b'') + tokens + text[end-1:])
        else:
            s.set_text(sec, je.put(s.text(sec), path, je.fmt_int(value)))
        log.append({'what': 'world', 'label': row['label'], 'from': row['value'], 'to': value})
    return (s.build() if log else b), log

def stats_rows(b):
    """Address each row by the engine's checked stat identity, not by its displayed label."""
    stats = fl.Stats(fl.Save(b).text(fl.STATS))
    rows = []
    for owner_index, owner in enumerate(stats.tables['owner'][:3]):
        who = ('Total', 'Lucia', 'Jason')[owner_index]
        counters = [(k, 0) for k in ('numpositivetemperamentevents', 'numnegativetemperamentevents', 'busted', 'deaths')]
        counters += [(k, q) for k in ('reachedwantedlevel', 'evadedwantedlevel')
                     for q in ('any', 'level1', 'level2', 'level3', 'level4', 'level5', 'level6')]
        for base, qual in counters:
            row = stats.row(base, qual, owner)
            if row:
                rows.append(dict(group='Crime history', label=f'{who} / {base}' + (f' / {qual}' if qual else ''),
                                 stat=row, value=row['value']))
    for qualifier, owner in [('partnerhandholding', fl.STORY), (0, 'withpartner'), (0, 'withpartnerfreeroam')]:
        row = stats.row('totalplayingtimems', qualifier, owner)
        if row:
            rows.append(dict(group='Relationship', label=f'{qualifier or owner} (ms)', stat=row, value=row['value']))
    text = stats.txt
    owners = ('Total', 'Lucia', 'Jason')
    for spec in savedit.featured(text):
        for row in spec['entries']:
            editable = not (spec['autoTotal'] and row['owner'] == 0)
            who = owners[row['owner']] if row['owner'] < len(owners) else str(row['owner'])
            label = f"{who} / {spec['label']} ({spec['unit']})"
            item = dict(group='Stats / ' + spec['category'], label=label, value=row['value'], cap=spec.get('max'))
            if editable:
                item['stat'] = row
            rows.append(item)
    inv_text = savedit.section(b, money.SEC_INV)
    for weapon in savedit.weapons(inv_text):
        rows.append(dict(group='Carried weapons', label=owners[weapon['inv']+1] + ' / ' + (weapon['label'] or weapon['id']),
                         value=weapon['name'] or weapon['id']))
    for item in savedit.ammo(inv_text):
        rows.append(dict(group='Carried ammo', label=owners[item['inv']+1] + ' / ' + item['label'], value=item['value']))
    for item in money.scan(b)['items']:
        for key in ('value', 'spendable', 'stuck'):
            if key in item:
                rows.append(dict(group='Account balances', label=f"{owners[item['inv']+1]} / {item['kind']} / {key}",
                                 value=item[key]))
    import activities2
    for venue, course, tier in activities2._courses():
        for field in ('bestscore', 'recentscore', 'highestmedal', 'shots', 'hits', 'accuracy', 'bullseyes', 'timescompleted', 'timescancelled', 'unlocked'):
            row = stats.row(field, tier, course)
            if row:
                item = dict(group='Range records', label=f'{venue} / {course} / {tier} / {field}', value=row['value'])
                if field in ('bestscore', 'recentscore'):
                    item['stat'] = row
                rows.append(item)
    return rows
