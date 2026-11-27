# Save Garage - Copyright (C) 2026 NotHGM - GNU GPL v3 with the additional terms in NOTICE; see LICENSE.
"""Browse every section of the save and change single numbers or true/false values in place.

This is the expert view behind the curated tabs. Values are replaced byte for byte (see jsonedit), the old value must
still be there, and a number stays a number in the same style (whole, or with six decimals). Sections the game uses to
run the story, the money and inventory (edited on their own tabs) and the vehicle records (protected by a checksum) are
read-only here.
"""
import math
import re

import fog
import hashnames
import jsonedit as je
import money
import player
import savekeys

READ_ONLY = {
    0x029bbf82: 'the game version',
    0x7e56d644: 'vehicle records are protected by a checksum',
    0xd9851844: 'the story flow',
    0xc5c89169: 'script state',
    0xe9bcf3c7: 'heist state',
    money.SEC_INV: 'use the Money and Ammo tabs',
    money.SEC_STAT: 'use the Stats and All stats tabs',
    0x6296c122: 'the bank ledger is kept in step by the Money tab',
    0x46f14889: 'use the World tab',                      # the strength, cardio and focus levels (levels.py)
    fog.SEC: 'use the World tab',
}
# Single fields with their own rule: (section, key) -> reason it can't be changed, the (low, high) range allowed, or a
# function of the section text and the field's path that returns one of those (a rule that depends on the save). A key
# can also name a typed array ({"$data": [...]}), for a rule on each of its elements.
PED = 0xe528fe31
FIELD_RULES = {
    (PED, '$0x4802abf7'): 'the game keeps maximum health at 100 in every save',        # fMaxHealth
    (PED, '$0x0834e1d0'): (1.0, 250.0),                                                 # fHealth: the game itself goes up to 250
}
FIELD_RULES.update(player.raw_rules())   # the World tab's limits for the attributes, criminal profile, relationship and armour
RISKY = {0x6df5d2cf, 0x7f587594, 0xe4fcc5fa, 0xba7a26ca, 0x8496351d, 0x22a87829, 0xdee848ca, 0x3a4cbf5d, 0x9653b39d, 0x96f1a1c3,
         0x86572177, 0x5299e475}
_HEX = re.compile(r'^\$0x([0-9a-f]{8})$')
_INT = re.compile(rb'^-?[0-9]+$')
_FLT = re.compile(rb'^-?[0-9]+\.[0-9]+$')


class BrowseError(Exception):
    pass


def label(key):
    m = _HEX.match(key) if isinstance(key, str) else None
    if not m:
        return key
    h = int(m.group(1), 16)
    return savekeys.KEY_NAMES.get(h) or savekeys.SECTION_NAMES.get(h) or key


def _kind(raw):
    c = raw[:1]
    if c == b'{':
        return 'object'
    if c == b'[':
        return 'array'
    if c == b'"':
        return 'text'
    if raw in (b'true', b'false'):
        return 'bool'
    if raw == b'null':
        return 'null'
    return 'float' if b'.' in raw or b'e' in raw.lower() else 'int'


def sections(b):
    ents, secs, _, _, _ = money._load(b)
    return [{'hash': '%08x' % e[0], 'name': savekeys.SECTION_NAMES.get(e[0]), 'bytes': len(secs[i]),
             'readOnly': READ_ONLY.get(e[0]), 'risky': e[0] in RISKY} for i, e in enumerate(ents)]


_HEXTEXT = re.compile(rb'^"0x([0-9a-fA-F]{8})"$')


def _means(kind, raw):
    """What a value stands for when it is the ID of something with a known name (a number or "0x…" text)."""
    if kind == 'int':
        return hashnames.lookup(int(raw))
    m = _HEXTEXT.match(raw) if kind == 'text' else None
    return hashnames.lookup(int(m.group(1), 16)) if m else None


def _record_means(members):
    """For an object: a typed hash {"$data": "0x…"} names itself; a small record is named by the first ID in it."""
    if len(members) == 1 and members[0][0] == '$data':
        return _means('text', members[0][1])
    for _, v in members[:8]:
        if len(v) > 200:
            continue
        kv = _kind(v)
        if kv == 'object':
            sub = je.members(v)
            m = _means('text', sub[0][1]) if len(sub) == 1 and sub[0][0] == '$data' else None
        else:
            m = _means(kv, v)
        if m:
            return m
    return None


def _rule(sec_hash, txt, path):
    """The rule for the field at path (see FIELD_RULES): a reason it is read-only, a (low, high) range, or None."""
    if not path:
        return None
    rule = FIELD_RULES.get((sec_hash, path[-1]))
    if rule is None and len(path) >= 3 and path[-2] == '$data':          # an element of a typed array
        rule = FIELD_RULES.get((sec_hash, path[-3]))
    return rule(txt, list(path)) if callable(rule) else rule


def node(b, sec_hash, path, offset=0, limit=200):
    ents, secs, _, _, _ = money._load(b)
    txt = secs[money._sec(ents, sec_hash)]
    rows = je.members(txt, path)
    out = []
    for k, raw in rows[offset:offset + limit]:
        kind = _kind(raw)
        item = {'key': k, 'label': label(k) if isinstance(k, str) else k, 'kind': kind}
        if kind in ('object', 'array'):
            members = je.members(raw)
            item['count'] = len(members)
            means = _record_means(members) if kind == 'object' else None
            if means:
                item['means'] = means
        else:
            item['raw'] = raw.decode('utf-8', 'replace')[:200]
            rule = _rule(sec_hash, txt, list(path) + [k])
            if isinstance(rule, str):
                item['readOnly'] = rule
            elif rule:
                item['min'], item['max'] = rule
            means = _means(kind, raw)
            if means:
                item['means'] = means
        out.append(item)
    return {'section': '%08x' % sec_hash, 'path': path, 'total': len(rows), 'offset': offset, 'items': out,
            'readOnly': READ_ONLY.get(sec_hash), 'risky': sec_hash in RISKY}


def _token(old_raw, new):
    kind = _kind(old_raw)
    if kind == 'bool':
        if not isinstance(new, bool):
            raise BrowseError('bad_value')
        return b'true' if new else b'false'
    if kind == 'int':
        if isinstance(new, bool) or not isinstance(new, (int, float)) or (isinstance(new, float) and not new.is_integer()):
            raise BrowseError('bad_value')
        n = int(new)
        if not -(2 ** 63) <= n < 2 ** 64:
            raise BrowseError('out_of_range')
        return str(n).encode()
    if kind == 'float':
        if isinstance(new, bool) or not isinstance(new, (int, float)) or not math.isfinite(new) or abs(new) > 1e12:
            raise BrowseError('bad_value')
        return b'%.6f' % new
    raise BrowseError('not_editable')


def apply(b, edits):
    """edits: [{'section': hex, 'path': [...], 'value': old raw text, 'newValue': number or bool}] -> (bytes, log)."""
    ents, secs, gaps, head, tail = money._load(b)
    log = []
    for e in edits:
        h = int(e['section'], 16)
        if h in READ_ONLY:
            raise BrowseError('read_only')
        i = money._sec(ents, h)
        path = list(e['path'])
        cur = je.get(secs[i], path)
        if cur.decode('utf-8', 'replace') != str(e['value']):
            raise BrowseError('stale_item')
        rule = _rule(h, secs[i], path)
        if isinstance(rule, str):
            raise BrowseError('read_only')
        if rule and not (isinstance(e['newValue'], (int, float)) and not isinstance(e['newValue'], bool) and rule[0] <= e['newValue'] <= rule[1]):
            raise BrowseError('out_of_range')
        tok = _token(cur, e['newValue'])
        if tok != cur:
            secs[i] = je.put(secs[i], path, tok)
            log.append({'what': 'raw', 'label': e.get('label') or '/'.join(str(label(p)) for p in path[-2:]),
                        'from': cur.decode(), 'to': tok.decode()})
    if not log:
        return b, log
    return money._rebuild(head, ents, secs, gaps, tail, len(b)), log
