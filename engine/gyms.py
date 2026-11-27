# Save Garage - Copyright (C) 2026 NotHGM - GNU GPL v3 with the additional terms in NOTICE; see LICENSE.
"""Gym memberships (Save Garage feature module).

WHAT IT CHANGES
  * Inventory section d3f59a5e, inventory 0 main list: one new row per membership, exactly as the game adds it:
      ItemIds  = joaat('document_membership_gym_<id>'), SlotIds = joaat('slotid_document'), Quantities = 1,
      EquippedFlags = false, ParentGuidIndices = the ParentGuids index of the 'sp_player' row, a fresh Guid,
      and Items += (row << 4) | 1.  Uses money._add_row / money._parent_index, the row mechanism the PS5 already
      accepted for money boxes.
  * Stats section 0635cbd9: gymmembershipowned (UInt8, story000) += number of rows added. This is the row behind
    'GYM MEMBERSHIPS PURCHASED x / 8' (matched value for value on the user's stats screens).
  Nothing else. gymused.<gym> is NOT set: it records using a gym (Muscle Sands has a gymused row but sells no
  membership), so the game sets it the first time you work out there.

EVIDENCE FROM THE SAVES
  * A0 -> A1: one row document_membership_gym_bayside appeared under sp_player (slot slotid_document, qty 1),
    gymmembershipowned 0 -> 1, gymused.dynamix false -> true, and the FITNESS challenge 'Gym Member'
    ('Become a member at any gym') completed. A1 -> A2: the same for document_membership_gym_ajax, counter -> 2.
    Both rows survive every later game save unchanged (A2..A6c). The membership hashes occur nowhere else in the
    save (catalog blocks, ScriptShops and the rest were searched).
  * The eight gyms come from the game text: 'Buy a membership for the <gym> in <area>' exists for exactly eight
    gyms, and the screen says 'x / 8'.
  * Item names: the item id hash of a document is the key of its label text (true for both rows seen in saves:
    b91afaf4 'Ajax Gym membership', 71dd7121 'Dynamix Fitness membership'). Brute-forcing
    document_membership_gym_<word> against the other '<gym> membership' label keys gave exact 32-bit matches for
    aichi, majestic_hotel, ocean_beach, vice7, zenith and zenith_y_hotel (about 1e5 candidates against 8 keys, so a
    chance match is ~2e-4).

GRADES
  confirmed: ajax, bayside (written by the game in real saves).
  likely:    aichi, majestic_hotel, ocean_beach, vice7, zenith, zenith_y_hotel (name and label proven, never seen in
             a save; zenith_y_hotel is the Y Hotel gym: its label reads 'Zenith membership').

RISK: medium. Same row mechanism as the PS5-tested money boxes, but no membership other than ajax/bayside has been
loaded on a console. The game may also tie a gym's availability to story progress (gyms unlock as the map opens),
and it does not complete the 'Gym Member' challenge on its own: use the challenges module for that.
"""
import json

import featurelib as fl
import money

FEATURE = 'gyms'
SLOT_DOCUMENT = fl.joaat('slotid_document')
PLAYER_ROOT = fl.joaat('sp_player')
FOR_100 = 8                                  # 'GYM MEMBERSHIPS PURCHASED x / 8'
COUNTER = ('gymmembershipowned', 0)

# (id used in the item name, gymused qualifier, gym, area, grade)
GYMS = (
    ('ajax', 'ajax', 'Ajax Gym', 'Catalan Bay', 'confirmed'),
    ('bayside', 'dynamix', 'Dynamix Fitness', 'Bayside', 'confirmed'),
    ('aichi', 'aichi', 'Aichi', 'Washington Beach', 'likely'),
    ('majestic_hotel', 'grandmajestic', 'Grand Majestic Gym (Majestic Hotel)', 'Tequesta', 'likely'),
    ('ocean_beach', 'venus', 'Venus Fitness', 'Ocean Beach', 'likely'),
    ('vice7', 'viceseven', 'Vice Seven Gym', 'Tequesta', 'likely'),
    ('zenith', 'zenith', 'Zenith', 'Downtown', 'likely'),
    ('zenith_y_hotel', 'yhotel', 'Zenith at the Y Hotel', 'Washington Beach', 'likely'),
)
ITEM = {g[0]: fl.joaat('document_membership_gym_' + g[0]) for g in GYMS}
FREE_GYMS = ('musclesands',)                 # has a gymused row, sells no membership


def _owned(inv_txt):
    """{gym id: (inventory, row)} of membership rows present in the two protagonists' main lists."""
    by_item = {v: k for k, v in ITEM.items()}
    out = {}
    n_inv = len(json.loads(inv_txt)[fl.CODE][fl.key(fl.INVENTORY)][fl.key('Inventories')])
    for n in range(min(2, n_inv)):
        v = money._inventory(inv_txt, n)
        for r, it in enumerate(v['item']):
            g = by_item.get(it & fl.M32)
            if g and g not in out:
                out[g] = (n, r)
    return out


def read(b):
    s = fl.Save(b)
    owned = _owned(s.text(fl.INVENTORY))
    st = fl.Stats(s.text(fl.STATS))
    counter = st.value(*COUNTER)
    gyms = []
    for gid, used_q, label, area, grade in GYMS:
        gyms.append({'id': gid, 'item': fl.hexid(ITEM[gid]), 'label': label, 'area': area, 'grade': grade,
                     'owned': gid in owned, 'inventory': owned[gid][0] if gid in owned else None,
                     'usedGym': bool(st.value('gymused', used_q, default=False))})
    return {'feature': FEATURE,
            'gyms': gyms,
            'owned': len(owned),
            'possible': [g['id'] for g in gyms if not g['owned']],
            'counter': {'stat': 'gymmembershipowned', 'value': counter, 'of': FOR_100,
                        'label': 'GYM MEMBERSHIPS PURCHASED', 'consistent': counter == len(owned)},
            'freeGyms': [{'id': q, 'usedGym': bool(st.value('gymused', q, default=False))} for q in FREE_GYMS],
            'risk': 'medium',
            'notes': ['Adds the membership document rows the game adds when you buy a membership.',
                      'Only Ajax and Dynamix (Bayside) memberships have been seen in real saves; the other six are named from the game text.',
                      "Does not complete the 'Gym Member' challenge; the challenges module can."]}


def apply(b, choice):
    """choice: {'gyms': 'all' | [gym ids]} -> (new bytes, log)."""
    want = choice.get('gyms', 'all') if isinstance(choice, dict) else choice
    ids = [g[0] for g in GYMS] if want == 'all' else list(want)
    for gid in ids:
        if gid not in ITEM:
            raise fl.FeatureError('unknown_gym')
    s = fl.Save(b)
    inv = s.text(fl.INVENTORY)
    owned = _owned(inv)
    v = money._inventory(inv, 0)
    if PLAYER_ROOT not in [x & fl.M32 for x in v['item']]:
        raise fl.FeatureError('layout_changed')
    log = []
    added = 0
    for gid in ids:
        if gid in owned:
            continue
        v = money._inventory(inv, 0)
        root = [x & fl.M32 for x in v['item']].index(PLAYER_ROOT)
        inv, pidx = money._parent_index(inv, 0, v['guid'][root])
        inv, row, guid = money._add_row(inv, 0, money._inventory(inv, 0), pidx, ITEM[gid], SLOT_DOCUMENT, 1)
        added += 1
        log.append({'what': 'gym_membership', 'gym': gid, 'row': row})
    if not added:
        return b, log
    s.set_text(fl.INVENTORY, inv)
    st = fl.Stats(s.text(fl.STATS))
    cur = st.value(*COUNTER)
    if cur is None:
        raise fl.FeatureError('layout_changed')
    st.set(COUNTER[0], COUNTER[1], cur + added, 'Gym memberships purchased')
    txt, slog = st.apply()
    s.set_text(fl.STATS, txt)
    log += slog
    return s.build(), log
