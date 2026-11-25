"""Compendium: mark animals, weapons and vehicles as discovered (Save Garage feature module).

SECTION dbf71c51 = DiscoverableMemoryData[7], one entry per DiscoverableType 0..6:
  {DiscoverableType, NameHashes: int_array (unsigned decimal), Flags: int_array}, the two arrays parallel.
  0 = people met (names like 'Levi', read-only here), 1 = animals, 3 = vehicles, 5 = weapons and weapon variants,
  6 = equipment (only the Metal Detector ever appears), 2 and 4 = always empty. An empty array is written
  {"$content":"int_array"} without "$data".

WHAT IT CHANGES
  * Appends the missing hashes to NameHashes of the type and the same number of flag values to Flags.
  * Stats 0635cbd9 (owner story000), by the number of entries added:
      animals:  studied.animals and studied.<4fa68fa3> (+n each; equal in every save) and
                totalprogressmade.animalsdiscovered = float32(animals / 100) * 100      ('ANIMALS x / 100')
      weapons:  studied.weapons (+standard +variants), studied.<8dc8c123> (+standard) and
                totalprogressmade.weaponsdiscovered = float32(min(standard, 50) / 50) * 100 ('STANDARD ISSUE WEAPONS x / 50')
      vehicles: studied.vehicles and studied.<2b12592f> (+base models) and
                totalprogressmade.vehiclesdiscovered = float32(min(base, 200) / 200) * 100 ('BASE MODEL VEHICLES x / 200')
    Counters change by the number added (not recomputed) so values edited earlier are kept.

WHAT FLAGS 1 AND 3 MEAN (evidence, not certainty)
  Both values count the same in every counter. Bit 0 (1) = discovered; bit 1 (2) = examined up close, set when the
  entry is first discovered by getting in / close, and occasionally later: in playthrough A, 96 of 121 vehicles
  first discovered and driven in the same interval got 3, 15 of 17 never-driven ones got 1, and the only two
  upgrades 1 -> 3 (Caddy A1->A2, '95 Cheetah A4->A5) happened when the vehicle was first driven. Animals show the
  same split; weapons, people and equipment only ever use 1. The module writes 1 by default (the plain
  'discovered' state the game itself upgrades later); choice['flag'] = 3 is allowed for animals and vehicles.

EVIDENCE FOR THE LISTS AND COUNTERS (15 game-written saves, two playthroughs)
  * Animals: every counted type-1 entry is a discoverable_name_* stats qualifier, and the three uncounted ones are
    not (two named story pets, 'Whitetail Doe'): studied.animals = 3, 7, 10, 14 for lists of 4, 10, 13, 17.
    245 discoverable_name_* qualifiers exist (169 wild, 41 pets, 35 fish; FISHING on screen = 35). The compendium
    tabs on screen add up to 232 (HUNTING 61, FISHING 35, MAMMALS 18, CATS & DOGS 34, REPTILES & AMPHIBIANS 6,
    BIRDS 60, AQUATIC 18), so up to 13 of the 245 may not be shown by the game.
  * Weapons: on every list change studied.<8dc8c123> rose by the new weaponspec_* entries except the melee
    variants (bat_metal, knife_diver/edc/fixed) and the homing RPG, studied.weapons by those plus every new
    weaponkit_*, and two unnamed entries (Claw Hammer, Combat Knife) count nowhere. weaponsdiscovered = std/50 in
    float32 (60.000004 = 30/50) and is capped (54 counted shows 100.0 and '50 / 50').
  * Vehicles: the hashes are joaat(model) (153 of the 176 seen match <model>_base_spec stats names);
    studied.vehicles = list length minus uncounted entries; studied.<2b12592f> counts base models; the rest are
    standout variants (11 in A6b) and one police model counted nowhere. vehiclesdiscovered = base/200.

LIMITS / NOT SHIPPABLE WITHOUT A CONSOLE TEST
  * Vehicles: 44 per-category counters studied.<category> (one per CARS/SERVICE/STANDOUT page, BIKES, WATERCRAFT,
    AIRCRAFT; their sum equals studied.vehicles in every save) can't be kept in step, because which page a model
    belongs to is not in the save or in any local data. The 283 <model>_base_spec models also differ from the
    compendium's own list (e.g. 30 boats in stats against 28 on WATERCRAFT). apply() refuses vehicles unless
    choice['unverified_ok'] is true, and then logs that the category counters were not updated.
  * Weapons: only entries seen in a real list are added by default; named-but-never-seen specs and kits overshoot
    the compendium (11 unseen melee specs for 4 free MELEE slots, 155 unseen kits for VARIANTS 130) and need
    unverified_ok. Equipment (type 6) is read-only: its counter can't be told apart from a vehicle category.
  * The overall 100% figure is not recomputed (its weights can't be derived from the saves).

RISK: medium for animals and seen weapons; high for vehicles and unverified weapons.
"""
import featurelib as fl
import gamelabels
import itemnames
import statnames

FEATURE = 'compendium'
SEC = 0xdbf71c51
K_LIST, K_TYPE = fl.key('DiscoverableMemoryData'), fl.key('DiscoverableType')
K_NAMES, K_FLAGS = fl.key('NameHashes'), fl.key('Flags')
T_PEOPLE, T_ANIMALS, T_VEHICLES, T_WEAPONS, T_EQUIPMENT = 0, 1, 3, 5, 6

STUDIED = 'studied'
C_ANIMALS, C_ANIMALS2 = 'animals', 0x4fa68fa3
C_VEHICLES, C_BASE = 'vehicles', 0x2b12592f
C_WEAPONS, C_STANDARD = 'weapons', 0x8dc8c123
FOR_100 = {'animals': 100, 'vehicles': 200, 'weapons': 50}

# Hashes seen in a game-written compendium list on this console (20 saves, two playthroughs).
SEEN = {
    T_ANIMALS: frozenset((
        0x0ab89353, 0x0b5affda, 0x10ec6eed, 0x2cc8014b, 0x39f29f10, 0x4e4be138, 0x5974ddb3, 0x5bacfb3d, 0x61747f94,
        0x66deba3e, 0x83d91ead, 0x8491d7e5, 0x87c6b9bb, 0x951a7ccf, 0xbf2b065a, 0xdabd068c, 0xe9d5a97a)),
    T_VEHICLES: frozenset((
        0x015e402d, 0x04ce68ac, 0x05071b2d, 0x05cec17e, 0x067bc037, 0x08852855, 0x0aaa8b43, 0x0b6cd7a4, 0x0bba2261,
        0x0d4e5f4d, 0x1044926f, 0x16186345, 0x1677cbb9, 0x16c43d15, 0x17b17bf8, 0x17df5ec2, 0x194c4397, 0x1aba13b5,
        0x1b0b0c83, 0x1b8165d3, 0x23ca25f2, 0x258c9364, 0x28b67aca, 0x2a083060, 0x2bd3b846, 0x2d6d913b, 0x2ef89e46,
        0x33f2dea5, 0x345b8f37, 0x34cfa6fa, 0x34dd8aa1, 0x36f2d2cf, 0x3944d5a0, 0x39da2754, 0x39dd8bb8, 0x3a196cea,
        0x3adb9758, 0x3c7261b2, 0x3d961290, 0x3dee5eda, 0x3e3d1f59, 0x3f119114, 0x43779c54, 0x440851d8, 0x44623884,
        0x4543b74d, 0x45d56ada, 0x462fe277, 0x47bbcf2e, 0x4912da6a, 0x4b70d427, 0x4c1ed648, 0x4e4efe36, 0x4ec25b53,
        0x50a8bee2, 0x52db01e0, 0x56cdee7d, 0x56d42971, 0x57a536c6, 0x59e0fbf3, 0x5a82f9ae, 0x5a9ec131, 0x5c07a028,
        0x5d0aac8f, 0x5f677ec0, 0x615872f5, 0x63171d46, 0x6882fa73, 0x68a5d1ef, 0x69f61675, 0x6a8f503d, 0x7324e3d9,
        0x734c5e50, 0x7836ce2f, 0x78529595, 0x7b8ab45f, 0x7c0d5fbd, 0x7d7c88c0, 0x7eaac5f4, 0x7f7dc726, 0x7fc98542,
        0x81634188, 0x81e38f7f, 0x831a21d5, 0x836ba642, 0x84718d34, 0x865b7f60, 0x8777ee43, 0x881b4b5a, 0x898eccea,
        0x8a6354b8, 0x8a7c7ac3, 0x8c308d16, 0x8e6971d3, 0x8ef5e388, 0x91ca96ee, 0x9628879c, 0x97e55d11, 0x98f65a5e,
        0x9c46d824, 0x9d0450ca, 0xa42fc3a5, 0xa4a4e453, 0xa4d99b7d, 0xa5325278, 0xa63b5647, 0xa6a7128a, 0xa774b5a6,
        0xa7ede74d, 0xa91f52d1, 0xab092c04, 0xac33179c, 0xae2cc02a, 0xae679517, 0xafbb2ca4, 0xb12314e0, 0xb16e0de6,
        0xb39b0ae6, 0xb5d306a4, 0xb802dd46, 0xb822a1aa, 0xb8e2ae18, 0xb98738f8, 0xba1a380d, 0xba5334ac, 0xbb78956a,
        0xc1e908d2, 0xc29f8f4e, 0xc50e1fdc, 0xc5541dcf, 0xca495705, 0xcb84df29, 0xcc8a305c, 0xce0b9f22, 0xcf37bcc3,
        0xcfb3870c, 0xcff986eb, 0xd2389392, 0xd3d366b1, 0xd4ae63d9, 0xd7278283, 0xd757d97d, 0xd77e5276, 0xd7c5bf8c,
        0xd80f4a44, 0xddc0337e, 0xde08b098, 0xe0011fc7, 0xe1b7c320, 0xe2234987, 0xe3788bb1, 0xe54c8bcf, 0xe550775b,
        0xe593f7e3, 0xe5b3aca1, 0xe8ee6ce3, 0xe9805550, 0xea6a047f, 0xed7eada4, 0xedb3aebd, 0xedd516c6, 0xf0e46aee,
        0xf219af13, 0xf26ceff9, 0xf38c4245, 0xf3a5f200, 0xf4e1aa15, 0xf55d2f7a, 0xfbc312fd, 0xfc878c91, 0xfcfcb68b,
        0xfd128dfd, 0xfdc63d86, 0xfe77eae6, 0xfefd644f, 0xff2cd77b)),
    T_WEAPONS: frozenset((
        0x01b42dd9, 0x0cb1ac53, 0x13a8dc79, 0x1fef3cbd, 0x218cbd7d, 0x241c85a2, 0x25dcbacc, 0x25eae03c, 0x298d4e30,
        0x29e48687, 0x29eb8ae0, 0x2c65966e, 0x2d4b3165, 0x2e40179c, 0x2f824957, 0x362c337e, 0x3a7f4de1, 0x3b209582,
        0x3db03763, 0x40c2bfb8, 0x42a2194a, 0x4969611c, 0x5694b416, 0x5875b5dc, 0x599a84fe, 0x5dd5e66d, 0x5ddf8e20,
        0x5ea6e528, 0x63701876, 0x63900e61, 0x64572c77, 0x65761b58, 0x6b992eee, 0x6ee185ac, 0x7115d13a, 0x71500633,
        0x73c0e6bd, 0x77080f3e, 0x78f78bad, 0x796a1f2a, 0x817f229b, 0x818f19bc, 0x82ace2d4, 0x8af6ecb7, 0x8d6185fc,
        0x9a605b86, 0x9b775a81, 0x9b877501, 0x9c1bf672, 0x9fcad864, 0xa0bb0fa6, 0xa0f6d6a7, 0xa4c51aae, 0xa856495a,
        0xa96d4140, 0xacbf3e81, 0xb0942fb7, 0xb371b958, 0xbb98e9a9, 0xc24e18bf, 0xc487db86, 0xcf339c0d, 0xd1882243,
        0xd20c3144, 0xd6587a06, 0xd7979f08, 0xdd26fa33, 0xdfd9e0ba, 0xe685e32f, 0xe9578d10, 0xec26da4a, 0xedda1bf8,
        0xf238661c, 0xf2abae5d, 0xf2fb85f4, 0xf59f9d17, 0xf6a49c8c)),
    T_EQUIPMENT: frozenset((0xd17e2826,)),
}
# Seen hashes with no known name, with the game's text and what the counters showed they are.
UNNAMED = {
    0x39f29f10: ('Whitetail Doe', 'uncounted'), 0xdabd068c: ('Cheddar Biscuit', 'uncounted'), 0xbf2b065a: ('Peaches', 'uncounted'),
    0xf59f9d17: ('Claw Hammer', 'uncounted'), 0x4969611c: ('Combat Knife', 'uncounted'), 0xd17e2826: ('Metal Detector', 'equipment'),
    0xba1a380d: ('L35P', 'base'), 0x865b7f60: (None, 'base'), 0xb16e0de6: ('Boomazoom', 'base'),
    0x7f7dc726: (None, 'standout'), 0xfdc63d86: ('Venturas BLVD Elegy', 'standout'), 0xd7c5bf8c: ('Cellerica Caddy', 'standout'),
    0x7fc98542: ('Police Lowline', 'uncounted'),
    0x6a8f503d: ('Shining Sea Squalo', 'base or standout'), 0x345b8f37: ('Hydroblast', 'base or standout'),
    0xe54c8bcf: ('Airboat 09', 'base or standout'), 0x7d7c88c0: ('Sea Enchantress', 'base or standout'),
    0xfe77eae6: ('Transient', 'base or standout'), 0x1b0b0c83: ('S23 CCS', 'base or standout'),
    0xc5541dcf: (None, 'base or standout'), 0x4c1ed648: (None, 'base or standout'), 0xa63b5647: ('B3000 Excavator', 'base or standout'),
    0x836ba642: (None, 'base or standout'), 0x881b4b5a: ('SuperVolito', 'base or standout'), 0xde08b098: (None, 'base or standout'),
    0x05cec17e: (None, 'base or standout'), 0xfbc312fd: ('Vapid Dominator Buggy', 'base or standout'),
    0xe0011fc7: ("'67 Dominator Buggy", 'base or standout'), 0x5c07a028: (None, 'base or standout'),
}
WEAPON_NOT_STANDARD = frozenset(fl.joaat(n) for n in (
    'weaponspec_melee_bat_metal', 'weaponspec_melee_knife_diver', 'weaponspec_melee_knife_edc', 'weaponspec_melee_knife_fixed',
    'weaponspec_launched_rpg_homing'))
_WEAPON_EXCLUDE = ('_arcade_', 'weaponspec_sports_', 'weaponkit_sports_', 'weaponspec_tool_', 'weaponkit_tool_', 'weaponspec_unarmed',
                   'weaponspec_thrown_item_default')


def _labels(hh):
    return (gamelabels.QUALIFIER_LABELS.get(hh) or itemnames.ITEM_LABELS.get(hh) or (UNNAMED.get(hh) or (None,))[0])


def _candidates():
    """{type: [{'hash', 'name', 'label', 'grade', 'counts'}]}; counts = counters the entry moves."""
    out = {T_ANIMALS: [], T_VEHICLES: [], T_WEAPONS: []}
    for n in sorted(statnames.QUALIFIER_NAMES):
        if n.startswith('discoverable_name_'):
            hh = fl.joaat(n)
            out[T_ANIMALS].append({'hash': hh, 'name': n, 'label': _labels(hh), 'grade': 'seen' if hh in SEEN[T_ANIMALS] else 'named',
                                   'counts': ('animals',)})
    for n in sorted(statnames.QUALIFIER_NAMES):
        if n.endswith('_base_spec'):
            model = n[:-len('_base_spec')]
            hh = fl.joaat(model)
            out[T_VEHICLES].append({'hash': hh, 'name': model, 'label': gamelabels.QUALIFIER_LABELS.get(fl.joaat(n)),
                                    'grade': 'seen' if hh in SEEN[T_VEHICLES] else 'named', 'counts': ('vehicles', 'base')})
    for hh, (label, role) in UNNAMED.items():
        if hh in SEEN[T_VEHICLES] and role == 'base':
            out[T_VEHICLES].append({'hash': hh, 'name': None, 'label': label, 'grade': 'seen', 'counts': ('vehicles', 'base')})
    names = sorted({n for n in list(itemnames.ITEM_NAMES) + list(statnames.QUALIFIER_NAMES) if n.startswith(('weaponspec_', 'weaponkit_'))})
    for n in names:
        hh = fl.joaat(n)
        seen = hh in SEEN[T_WEAPONS]
        if not seen and (any(x in n for x in _WEAPON_EXCLUDE) or (n.startswith('weaponkit_') and n.endswith('_001'))):
            continue
        if n.startswith('weaponkit_'):
            counts = ('weapons',)
        elif hh in WEAPON_NOT_STANDARD or (not seen and n.startswith('weaponspec_melee_') and not n.endswith('_default')):
            counts = ()
        else:
            counts = ('weapons', 'standard')
        out[T_WEAPONS].append({'hash': hh, 'name': n, 'label': _labels(hh), 'grade': 'seen' if seen else 'named', 'counts': counts})
    for hh, (label, role) in UNNAMED.items():
        if hh in SEEN[T_WEAPONS]:
            out[T_WEAPONS].append({'hash': hh, 'name': None, 'label': label, 'grade': 'seen', 'counts': ()})
    return out


CANDIDATES = _candidates()
GROUPS = {'animals': T_ANIMALS, 'vehicles': T_VEHICLES, 'weapons': T_WEAPONS}


def _lists(sec_txt):
    """{type: [(hash, flag)]} from the section."""
    out = {}
    for e in fl.payload(sec_txt, SEC)[K_LIST]:
        names = [x & fl.M32 for x in ((e[K_NAMES] or {}).get('$data') or [])]
        flags = (e[K_FLAGS] or {}).get('$data') or []
        if len(names) != len(flags):
            raise fl.FeatureError('layout_changed')
        out[e[K_TYPE]] = list(zip(names, flags))
    return out


def read(b):
    s = fl.Save(b)
    lists = _lists(s.text(SEC))
    st = fl.Stats(s.text(fl.STATS))
    types = []
    for gname, t in GROUPS.items():
        present = dict(lists.get(t, []))
        entries = [{'id': fl.hexid(c['hash']), 'name': c['name'], 'label': c['label'], 'grade': c['grade'], 'counts': list(c['counts']),
                    'discovered': c['hash'] in present, 'flag': present.get(c['hash'])} for c in CANDIDATES[t]]
        cand = {c['hash'] for c in CANDIDATES[t]}
        extra = [{'id': fl.hexid(hh), 'label': _labels(hh), 'flag': f, 'role': (UNNAMED.get(hh) or (None, None))[1]}
                 for hh, f in lists.get(t, []) if hh not in cand]
        flags = {}
        for _, f in lists.get(t, []):
            flags[str(f)] = flags.get(str(f), 0) + 1
        types.append({'group': gname, 'type': t, 'listed': len(present), 'flags': flags,
                      'candidates': len(entries), 'discovered': sum(1 for e in entries if e['discovered']),
                      'seenCandidates': sum(1 for e in entries if e['grade'] == 'seen'),
                      'missingSeen': sum(1 for e in entries if e['grade'] == 'seen' and not e['discovered']),
                      'missingNamed': sum(1 for e in entries if e['grade'] == 'named' and not e['discovered']),
                      'entries': entries, 'otherListed': extra,
                      'risk': {'animals': 'medium', 'weapons': 'medium', 'vehicles': 'high'}[gname]})
    counters = {
        'animals': {'studied': st.value(STUDIED, C_ANIMALS), 'studied2': st.value(STUDIED, C_ANIMALS2),
                    'percent': st.value('totalprogressmade', 'animalsdiscovered'), 'for100': FOR_100['animals']},
        'vehicles': {'studied': st.value(STUDIED, C_VEHICLES), 'base': st.value(STUDIED, C_BASE),
                     'percent': st.value('totalprogressmade', 'vehiclesdiscovered'), 'for100': FOR_100['vehicles']},
        'weapons': {'studied': st.value(STUDIED, C_WEAPONS), 'standard': st.value(STUDIED, C_STANDARD),
                    'percent': st.value('totalprogressmade', 'weaponsdiscovered'), 'for100': FOR_100['weapons']},
    }
    checklist = [{'label': 'ANIMALS', 'value': counters['animals']['studied'], 'of': 100},
                 {'label': 'BASE MODEL VEHICLES', 'value': counters['vehicles']['base'], 'of': 200},
                 {'label': 'STANDARD ISSUE WEAPONS', 'value': min(counters['weapons']['standard'] or 0, 50), 'of': 50}]
    return {'feature': FEATURE, 'types': types, 'counters': counters, 'checklist': checklist,
            'people': len(lists.get(T_PEOPLE, [])), 'equipment': [{'id': fl.hexid(hh), 'label': _labels(hh), 'flag': f} for hh, f in lists.get(T_EQUIPMENT, [])],
            'flagMeaning': {'1': 'discovered', '3': 'discovered and examined up close (likely)'},
            'risk': 'medium',
            'notes': ['Animals: adds every discoverable animal (245); the game shows 232 on its tabs, so a few may stay hidden.',
                      'Weapons: adds weapons and variants seen in real saves; others need unverified_ok.',
                      "Vehicles: experimental; the per-page counters ('COUPES 13 / 18' and so on) can't be kept in step."]}


def _append(t, typ, hashes, flag):
    s, _ = fl.walk(t, fl.CODE, fl.key(SEC), K_LIST)
    for a, z in fl.elements(t, s):
        mem = {k: (x, y) for k, x, y in fl.members(t, a)}
        if int(t[mem[K_TYPE][0]:mem[K_TYPE][1]]) != typ:
            continue
        if not mem[K_NAMES][0] < mem[K_FLAGS][0]:
            raise fl.FeatureError('layout_changed')
        names = fl.typed_values(t, mem[K_NAMES][0])[1]
        flags = fl.typed_values(t, mem[K_FLAGS][0])[1]
        if len(names) != len(flags):
            raise fl.FeatureError('layout_changed')
        t = fl.typed_append(t, mem[K_FLAGS][0], [b'%d' % flag] * len(hashes))        # Flags come later in the text
        return fl.typed_append(t, mem[K_NAMES][0], [b'%d' % (x & fl.M32) for x in hashes])
    raise fl.FeatureError('layout_changed')


def apply(b, choice):
    """choice: {'groups': ['animals', 'weapons', 'vehicles'], 'ids': [hex ids] (optional filter), 'flag': 1 | 3,
    'unverified_ok': False} -> (new bytes, log). 'flag' applies to animals and vehicles; weapons always get 1.
    Without unverified_ok: animals (all 245) and weapons seen in real saves. Vehicles and never-seen weapons need it."""
    choice = choice or {}
    groups = choice.get('groups', ['animals', 'weapons'])
    if set(groups) - set(GROUPS):
        raise fl.FeatureError('unknown_group')
    unverified = bool(choice.get('unverified_ok'))
    if 'vehicles' in groups and not unverified:
        raise fl.FeatureError('vehicles_unverified')
    flag = int(choice.get('flag', 1))
    if flag not in (1, 3):
        raise fl.FeatureError('bad_value')
    only = None
    if choice.get('ids'):
        only = {fl.h(x if isinstance(x, int) else ('0x' + x if not x.startswith('0x') else x)) for x in choice['ids']}
    s = fl.Save(b)
    t = s.text(SEC)
    lists = _lists(t)
    st = fl.Stats(s.text(fl.STATS))
    log = []
    for gname in groups:
        typ = GROUPS[gname]
        gflag = 1 if typ == T_WEAPONS else flag          # weapons only ever use 1 in real saves
        present = {hh for hh, _ in lists.get(typ, [])}
        add = []
        for c in CANDIDATES[typ]:
            if c['hash'] in present or (only is not None and c['hash'] not in only):
                continue
            if c['grade'] != 'seen' and gname == 'weapons' and not unverified:
                continue
            add.append(c)
            present.add(c['hash'])
        if not add:
            continue
        t = _append(t, typ, [c['hash'] for c in add], gflag)
        n = {k: sum(1 for c in add if k in c['counts']) for k in ('animals', 'vehicles', 'base', 'weapons', 'standard')}
        log.append({'what': 'compendium', 'group': gname, 'added': len(add), 'flag': gflag,
                    'grades': {g: sum(1 for c in add if c['grade'] == g) for g in ('seen', 'named')}})
        if gname == 'animals':
            cur = st.value(STUDIED, C_ANIMALS)
            st.set(STUDIED, C_ANIMALS, cur + n['animals'], 'Animals discovered')
            st.set(STUDIED, C_ANIMALS2, st.value(STUDIED, C_ANIMALS2) + n['animals'], 'Animals discovered (second counter)')
            st.set('totalprogressmade', 'animalsdiscovered', fl.pct32(cur + n['animals'], 100), 'Animals, part of 100% completion')
        elif gname == 'weapons':
            st.set(STUDIED, C_WEAPONS, st.value(STUDIED, C_WEAPONS) + n['weapons'], 'Weapons discovered')
            cur = st.value(STUDIED, C_STANDARD)
            st.set(STUDIED, C_STANDARD, cur + n['standard'], 'Standard issue weapons discovered')
            st.set('totalprogressmade', 'weaponsdiscovered', fl.pct32(cur + n['standard'], 50), 'Weapons, part of 100% completion')
        else:
            st.set(STUDIED, C_VEHICLES, st.value(STUDIED, C_VEHICLES) + n['vehicles'], 'Vehicles discovered')
            cur = st.value(STUDIED, C_BASE)
            st.set(STUDIED, C_BASE, cur + n['base'], 'Base model vehicles discovered')
            st.set('totalprogressmade', 'vehiclesdiscovered', fl.pct32(cur + n['base'], 200), 'Vehicles, part of 100% completion')
            log.append({'what': 'category_counters_not_updated', 'group': 'vehicles', 'added': len(add),
                        'note': 'per-page studied.<category> counters no longer sum to studied.vehicles'})
    if not any(x['what'] == 'compendium' for x in log):
        return b, log
    s.set_text(SEC, t)
    txt, slog = st.apply()
    s.set_text(fl.STATS, txt)
    return s.build(), log + slog
