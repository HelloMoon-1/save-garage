# Save Garage - Copyright (C) 2026 NotHGM - GNU GPL v3 with the additional terms in NOTICE; see LICENSE.
"""Reveal the map: clear the fog of war from every map region Save Garage knows (Save Garage feature module).

WHAT IT CHANGES
  FogOfWar section 6ac593ca (code block): {dataVersion 9, regions: [{regionId $0xbf2c8a79, regionType $0x9e96c714}]}.
  Each known region the save lacks is appended as {"$0xbf2c8a79":<id>,"$0x9e96c714":<type>}, the way the game writes
  an entry. Entries already in the list are never changed, removed or moved.

BUILT-IN COVERAGE: the legacy 'known' edit adds up to 749 observed regions. The 'full'
  edit uses a 889-region reference (52 named regions and 837 cells) and requires every
  existing entry to match the reference. Custom reference edits from earlier versions
  remain compatible. New entries are appended; existing entries retain their order.

EVIDENCE FROM THE SAVES (20 saves holding 43 to 719 regions)
  * dataVersion is 9, and every entry is exactly {id, type} with type 1 or 2 and an unsigned 32-bit id; no id repeats.
  * A region's type never changes between saves: it is a property of the region, not progress.
  * The game writes the list in a different order in almost every save (it looks like a hash-table dump) and new
    regions turn up anywhere, so appending at the end is as good as any place.
  * 'Region visited' is true for only some of the named regions on the list (5 of the 25 in an early save), so it is
    not a mirror of the list and is left alone. No stat counts the regions revealed.

REFUSED (FeatureError, nothing written): fog_version (dataVersion is not 9); fog_entry (an entry with other keys, a type
  other than 1 or 2, an id that isn't an unsigned 32-bit number, or a region Save Garage knows listed with the other
  type); fog_repeat (an id listed twice); layout_changed (the section isn't shaped as above). Regions the save has that
  Save Garage doesn't know (outside the built-in table) are fine and are kept as they are.

RISK: caution (one section, appends only). Not tested on a PS5 yet.
"""
import json
import re

import featurelib as fl
import fogdata
from fog_regions import OBSERVED, FULL_MAP_CELLS

FEATURE = 'fog'
SEC = 0x6ac593ca
VERSION = 9
MAP_TOTAL = 889                                # regions on the whole map (GarlicSaves' count; their table isn't used)
K_VERSION, K_LIST, K_ID, K_TYPE = '$0x3521b964', '$0x31bfd061', '$0xbf2c8a79', '$0x9e96c714'
CELL, NAMED = 1, 2
NAMED_IDS = tuple(fl.joaat(n) for n in fogdata.NAMED)
CELL_IDS = tuple(dict.fromkeys((*fogdata.CELLS, *OBSERVED[CELL])))
KNOWN = {**dict.fromkeys(NAMED_IDS, NAMED), **dict.fromkeys(CELL_IDS, CELL)}
FULL_MAP = {**KNOWN, **dict.fromkeys(FULL_MAP_CELLS, CELL)}
_UINT = re.compile(rb'0|[1-9][0-9]{0,9}')


def _uint(tok):
    if not _UINT.fullmatch(tok):
        return None
    v = int(tok)
    return v if v <= fl.M32 else None


def _regions(t):
    """((start, end) of the region list, [(id, type)] in save order), after every check; raises FeatureError."""
    s, _ = fl.walk(t, fl.CODE, fl.key(SEC))
    top = fl.members(t, s)
    spans = {k: (vs, ve) for k, vs, ve in top}
    if len(top) != 2 or set(spans) != {K_VERSION, K_LIST}:
        raise fl.FeatureError('layout_changed')
    vs, ve = spans[K_VERSION]
    if t[vs:ve] != b'%d' % VERSION:
        raise fl.FeatureError('fog_version')
    ls, le = spans[K_LIST]
    if t[ls] != ord('['):
        raise fl.FeatureError('layout_changed')
    out, seen = [], set()
    for es, _ in fl.elements(t, ls):
        if t[es] != ord('{'):
            raise fl.FeatureError('fog_entry')
        em = fl.members(t, es)
        val = {k: t[a:b] for k, a, b in em}
        if len(em) != 2 or set(val) != {K_ID, K_TYPE}:
            raise fl.FeatureError('fog_entry')
        rid, rtype = _uint(val[K_ID]), val[K_TYPE]
        if rid is None or rtype not in (b'1', b'2') or KNOWN.get(rid, int(rtype)) != int(rtype):
            raise fl.FeatureError('fog_entry')
        if rid in seen:
            raise fl.FeatureError('fog_repeat')
        seen.add(rid)
        out.append((rid, int(rtype)))
    # the same list as a JSON parser sees it (no repeated keys hiding a different value)
    p = json.loads(t)[fl.CODE][fl.key(SEC)]
    if p.get(K_VERSION) != VERSION or [(e.get(K_ID), e.get(K_TYPE)) for e in p.get(K_LIST, [])] != out:
        raise fl.FeatureError('layout_changed')
    return (ls, le), out


def read(b):
    t = fl.Save(b).text(SEC)
    try:
        _, have = _regions(t)
        problem = None
    except fl.FeatureError as e:
        have, problem = [], str(e)
    ids = {i for i, _ in have}
    return {'feature': FEATURE, 'regions': len(have), 'named': sum(1 for _, k in have if k == NAMED),
            'cells': sum(1 for _, k in have if k == CELL), 'unknown': sum(1 for i in ids if i not in KNOWN),
            'known': len(KNOWN), 'knownNamed': len(NAMED_IDS), 'knownCells': len(CELL_IDS), 'mapTotal': MAP_TOTAL,
            'fullMapCompatible': problem is None and all(FULL_MAP.get(i) == k for i, k in have),
            'missing': 0 if problem else sum(1 for i in KNOWN if i not in ids), 'problem': problem, 'risk': 'caution'}


def reference_choice(text, target):
    extra = complete_reference(text)
    choice = {'referenceCells': extra}
    _, have = _regions(fl.Save(target).text(SEC))
    if not dict(have).items() <= catalog(choice).items():
        raise fl.FeatureError('fog_reference')
    return choice


def complete_reference(text):
    """Validate the reference section and retain only cells missing from the built-in catalog."""
    if not isinstance(text, str) or len(text) > 256_000:
        raise fl.FeatureError('fog_reference')
    _, entries = _regions(text.encode('utf8'))
    regions = dict(entries)
    if len(regions) != MAP_TOTAL or not KNOWN.items() <= regions.items():
        raise fl.FeatureError('fog_reference')
    if any(kind != CELL for rid, kind in entries if rid not in KNOWN):
        raise fl.FeatureError('fog_reference')
    return [rid for rid, _ in entries if rid not in KNOWN]


def catalog(choice):
    if choice == 'full':
        return FULL_MAP
    if choice == 'known':
        return KNOWN
    if not isinstance(choice, dict) or set(choice) != {'referenceCells'}:
        raise fl.FeatureError('bad_request')
    extra = choice['referenceCells']
    if (not isinstance(extra, list) or len(extra) != MAP_TOTAL - len(KNOWN)
            or any(type(i) is not int or not 0 <= i <= fl.M32 or i in KNOWN for i in extra)
            or len(set(extra)) != len(extra)):
        raise fl.FeatureError('fog_reference')
    return {**KNOWN, **dict.fromkeys(extra, CELL)}


def apply(b, choice):
    regions = catalog(choice)
    s = fl.Save(b)
    t = s.text(SEC)
    (_, le), have = _regions(t)
    ids = {i for i, _ in have}
    if choice != 'known' and any(regions.get(i) != kind for i, kind in have):
        raise fl.FeatureError('fog_reference')
    add = [i for i in regions if i not in ids]
    if not add:
        return b, []
    new = b','.join(b'{"%s":%d,"%s":%d}' % (K_ID.encode(), i, K_TYPE.encode(), regions[i]) for i in add)
    t2 = t[:le - 1] + (b',' if have else b'') + new + t[le - 1:]
    _, after = _regions(t2)                    # read back: every old entry as it was, in place, then the new ones
    if after != have + [(i, regions[i]) for i in add]:
        raise fl.FeatureError('verify_failed')
    s.set_text(SEC, t2)
    return s.build(), [{'what': 'world', 'label': 'Map regions revealed', 'from': len(have), 'to': len(after)}]
