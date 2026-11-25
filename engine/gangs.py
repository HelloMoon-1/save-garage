"""Gang operations: the 100% checklist line 'GANG OPERATIONS CLEARED x / 39' and the PROGRESS / GANGS pages
(Save Garage feature module, READ-ONLY).

There is deliberately no apply(): clearing gang operations by editing the save is not offered (see WHY NOT EDITABLE).
read() maps every operation, what is done and what is left, so they can be played.

WHERE IT LIVES (three sections that agree in every one of the 20 saves)
  * Stats 0635cbd9, one owner per location (44 owners: 35 compound*, 6 front*, bankdruthers, bankfleecavcia):
    ganglocationdiscovered, ganglocationcleared (bool), successfulhits, uniqueitemsfound, and per item slot
    (qualifiers 1a4b1e08, 28c1baf5, 76fb5767, 8544f3fa) 0e3a164e = item taken and 6112a557 = the item's label hash
    ('Safe', 'Custom weapon', 'Crowex Watch', 'Custom vehicle'..., set when the item is seen).
    Per gang (qualifier) and allgangs: ganglocationsdiscovered, ganglocationscleared, successfulhits, uniquehits,
    uniqueitemsfound, valuestolen ('OPERATION GOODS STOLEN'), uniqueencounters ('ENCOUNTERS'), kills ('MEMBERS
    KILLED'); successfulhits.allgangs/withpartner is 'GANG OPERATIONS HIT TOGETHER'. totalprogressmade.allgangs =
    pct32(cleared, 39), weight 3 in the 100% figure. The checklist line reads ganglocationscleared.allgangs.
    In all 20 saves every per-gang and allgangs counter equals the sum of its locations (1,000 checks).
  * Enterprises dee848ca Data[]: one record per location the game has registered (21 of the 44 in the 67.5% save,
    plus a record 932cc5e2 that is no stats owner), Id = the owner hash. Status bits: 0x10 discovered, 0x80 hit,
    0x800 cleared (each equals the stats row in all 20 saves), 0x04 = tip received (TipId set); 0x400 is set only in
    the save right after a location was discovered or cleared. TasksUnlocked = discovered; Tasks[] {Id, Progress,
    IsResolved}; Visit/Engaged/Attacked/Robbed/Cooldown/Recovery/Restock timestamps. GangsData[15] {Id, IsKnown}:
    the 9 known gangs are the 9 on the GANGS page.
  * Discovery 940e954d: FlagState per location (0x100 tip marker, 0x200 discovered, 0x80 cleared; 0x400 and 0x800
    only right after a change), and one map category per gang whose bits are the gang's known locations (tipped or
    discovered); a complete category moves to the Discovered list (Guardia Brothers at A1).
  The Kingfishers page of the 67.5% save is reproduced row for row: OPERATIONS DISCOVERED 2 / 3 (stats 2, map
  category size 3), OPERATIONS CLEARED 1 / 3, OPERATION GOODS STOLEN $1,122, ENCOUNTERS 10, MEMBERS KILLED 47.

WHAT THE GAME WRITES WHEN AN OPERATION IS CLEARED (A3 -> A4, the Emerald Springs gas station meth front, found
and cleared in one visit; A0 -> A1 the Kolt bowling alley is the same)
  * stats: ganglocationdiscovered and ganglocationcleared false -> true, successfulhits 0 -> 1, uniqueitemsfound
    0 -> 1, 0e3a164e.28c1baf5 true and 6112a557.28c1baf5 = 'Safe'; criminal and allgangs: discovered +1, cleared
    +1, successfulhits +1, uniquehits +1, uniqueitemsfound +1, valuestolen +8,369; uniqueencounters and kills;
    totalprogressmade.allgangs 7.692308 -> 10.256411 and the overall figure.
  * Enterprises: a new Data record, Status 3262 (0xcbe; 2238 = 0x8be at the next save), TipId c9e1fd05, one Task
    92fca29d resolved, all timestamps.
  * Discovery: FlagState 1920 (0x780; 0x380 later) and the 'fronts' category bit.
  * Cooldowns (749dffa7): the location id joins CooldownGroups.Names with an expiry time (also seen for the Kolt
    docks at A0, the car theft ring at A3 and the Kingfishers breeding camp in B7b, each right after a visit).
  * What the location held: at the bowling alley the three items were a Crowex watch, a custom weapon (the kit
    weaponkit_shotgun_pumpaction_reward_kolt_01 was collected in the same interval) and an office safe.
  What exactly makes a location 'cleared' is game logic. The four cleared ones have every seen item taken and every
  Task resolved; the clubhouse, staging point and fish warehouse each have an item or Task left. The Kolt stash
  house has its one seen item taken and its one Task resolved and is still not cleared, so either it holds an item
  that was never seen or clearing needs more than the items.

WHY NOT EDITABLE
  * 23 of the 44 locations have no Enterprises record at all; their TipId, Task ids, item slots and item types are
    not in the save. A clear would have to invent them.
  * Setting only the stats would break the three-way agreement that holds in every game-written save: the map and
    the operation itself would still be active, the unique items (custom weapons, custom vehicles, watches, safe
    cash) would never be given, and clearing it later for real would count it again (allgangs past 39, a gang past
    its total).
  * Which 39 of the 44 count is not settled. The map categories hold 41 locations (Other criminals 10, Fronts 5,
    Kolt 5, Final Chapter 4, San4San 4, Kingfishers 3, PTT Youngin$ 3, Guardia Brothers 3, La Polilla Negra 2, M7 2);
    Kingfishers has 4 stats owners for 3 operations; the two banks are in no category.
  * Gang operations feed other things the save cannot show: the 'Pest Control' trophy (rob an operation of each
    gang), the partner photo filter (tracker b0f97f25 in Challenges, 'Clear 25 gang operations with your partner'),
    and the tips that come from contacts.
  A counter-only edit of ganglocationscleared.allgangs is possible through the stats editor and changes the screen,
  but completes nothing and would be pushed past 39 by later real clears.

NAMES
  The two unnamed owners were cracked here: 7fc09fac = frontcriminalbarbershopdrugs (likely: the game text has a
  'Barbershop Weed Front') and e6902700 = compoundkoltarmadillotycoon (weak: a chance match is possible; a decoy run
  of the same search hit 10 of 40 random hashes). Qualifier 9386ea4c is M7 (its category and counter moved with the
  M7 junkyard) and 0f9c45d3 is PTT Youngin$ (its category got both PTT compounds when they were tipped).
  Hints come from the game's own descriptions, matched by place words; check them in game.

RISK: none (read-only).
"""
import featurelib as fl

FEATURE = 'gangs'
SEC_ENTERPRISES = 0xdee848ca
SEC_DISCOVERY = 0x940e954d
OF = 39
STORY = 'story000'
K_DATA, K_GANGS, K_ID, K_STATUS = fl.key('Data'), fl.key('GangsData'), fl.key('Id'), fl.key('Status')
K_TASKS, K_TASK_RESOLVED, K_TASK_PROGRESS, K_TIP = fl.key('Tasks'), fl.key('IsResolved'), fl.key('Progress'), fl.key('TipId')
K_KNOWN = fl.key('IsKnown')
K_DISCOVERED, K_CATS, K_NAME, K_BITS = fl.key('Discovered'), '$0x713b0597', fl.key('Name'), fl.key('Discovered')
K_FLAGSTATE, K_STATEFLAGS = fl.key('FlagState'), fl.key('StateFlags')

ST_TIP, ST_DISCOVERED, ST_HIT, ST_CLEARED = 0x04, 0x10, 0x80, 0x800
FS_CLEARED, FS_TIP, FS_DISCOVERED = 0x80, 0x100, 0x200

# key, stats qualifier, name on the GANGS page / in the game text, Discovery map category
GANGS = (
    ('kingfishers', fl.joaat('kingfishers'), 'Kingfishers', fl.joaat('kingfishers')),
    ('koltandassociates', fl.joaat('koltandassociates'), 'Kolt & Associates', fl.joaat('koltandassociates')),
    ('finalchapter', fl.joaat('finalchapter'), 'Final Chapter', fl.joaat('finalchapter')),
    ('san4san', fl.joaat('san4san'), 'San4San', fl.joaat('san4san')),
    ('guardiabrothers', fl.joaat('guardiabrothers'), 'Guardia Brothers', fl.joaat('guardiabrothers')),
    ('lapolillanegra', fl.joaat('lapolillanegra'), 'La Polilla Negra', fl.joaat('lapolillanegra')),
    ('m7', 0x9386ea4c, 'M7', 0x9386ea4c),
    ('ptty', 0x0f9c45d3, 'PTT Youngin$', 0x0f9c45d3),
    ('criminal', fl.joaat('criminal'), 'Other criminals', fl.joaat('othercriminals')),
)
FRONTS_CATEGORY = fl.joaat('fronts')
ALL = fl.joaat('allgangs')
# Map category sizes ($bits) seen in this console's saves, for saves where a category has no record yet. Guardia
# Brothers' record was already complete (moved to Discovered) in every save that has it: 3 = its three locations,
# all tipped in the interval in which the category completed.
CATEGORY_SIZES = {fl.joaat('kingfishers'): 3, fl.joaat('koltandassociates'): 5, fl.joaat('finalchapter'): 4,
                  fl.joaat('san4san'): 4, fl.joaat('guardiabrothers'): 3, fl.joaat('lapolillanegra'): 2, 0x9386ea4c: 2,
                  0x0f9c45d3: 3, fl.joaat('othercriminals'): 10, FRONTS_CATEGORY: 5}

# owner name (stats), gang key or None, kind, label, hint from the game text (None when no description matched)
LOCATIONS = (
    ('compoundkingfishersbreedingcamp', 'kingfishers', 'compound', 'Breeding Camp', 'lakeside RV park (Sunrise RV Park) on Cottonmouth Lake'),
    ('compoundkingfishersfishingshacks', 'kingfishers', 'compound', 'Fishing Shacks', 'island shacks receiving cocaine by seaplane'),
    ('compoundkingfishersseedymotel', 'kingfishers', 'compound', 'Seedy Motel', 'dilapidated motel on the edge of the wildlife preserve (Pelican Valley)'),
    ('compoundkingfishersstilthouse', 'kingfishers', 'compound', 'Stilt House', None),
    ('compoundkoltabandonedhotel', 'koltandassociates', 'compound', 'Abandoned Hotel', 'derelict hotel in Port Gellhorn'),
    ('compoundkoltandassociatesdocks', 'koltandassociates', 'compound', 'Docks', 'docks in Port Gellhorn'),
    ('compoundkoltbowlingalley', 'koltandassociates', 'compound', 'Bowling Alley', 'abandoned Kingpin Bowling alley'),
    ('compoundkoltstashhouse', 'koltandassociates', 'compound', 'Stash House', 'small house in Port Gellhorn'),
    ('compoundkoltworkvangarage', 'koltandassociates', 'compound', 'Work Van Garage', 'June Warehouse, where the pill vans are kept (Port Gellhorn)'),
    (0xe6902700, 'koltandassociates', 'compound', 'Armadillo Tycoon (name weak)', None),
    ('compoundfinalchaptercarwash', 'finalchapter', 'compound', 'Car Wash', "Hog Stars garage behind Big Joe's Car Wash, Ambrosia"),
    ('compoundfinalchapterclubhouse', 'finalchapter', 'compound', 'Clubhouse', 'large compound beyond a vehicle graveyard'),
    ('compoundfinalchaptermethfacility', 'finalchapter', 'compound', 'Meth Facility', 'rural meth facility near Bellville'),
    ('frontfinalchapterbikerbar', 'finalchapter', 'front', 'Biker Bar (front)', 'biker bar near Ambrosia / Lake Leonida'),
    ('compoundsan4sandrughouse', 'san4san', 'compound', 'Drug House', 'house in La Perle'),
    ('compoundsan4sanimportgarage', 'san4san', 'compound', 'Import Garage', 'old auto body shop in La Perle'),
    ('compoundsan4sanrecordingstudio', 'san4san', 'compound', 'Recording Studio', 'run-down recording studio in Stockyard'),
    ('compoundsan4santowerblock', 'san4san', 'compound', 'Tower Block', 'apartment complex in Rockridge'),
    ('frontsan4sanrareshoes', 'san4san', 'front', 'Rare Shoes (front)', None),
    ('compoundguardiabrothersboatyard', 'guardiabrothers', 'compound', 'Boatyard', 'boatyard on Northbrook Drive, Little Cuba'),
    ('compoundguardiabrothersdistributioncenter', 'guardiabrothers', 'compound', 'Distribution Center', 'Saber Shipping yard / industrial facility in Balsero'),
    ('compoundguardiabrothersstagingpoint', 'guardiabrothers', 'compound', 'Staging Point', 'run-down building in Little Cuba'),
    ('compoundlapolillanegrafishwarehouse', 'lapolillanegra', 'compound', 'Fish Warehouse', None),
    ('compoundlapolillanegrasafehouse', 'lapolillanegra', 'compound', 'Safe House', 'secluded, heavily fortified compound'),
    ('compoundm7junkyard', 'm7', 'compound', 'Junkyard', 'Nova Auto junkyard on the edge of Hamlet'),
    ('compoundm7weedgrow', 'm7', 'compound', 'Weed Grow', 'hydroponic tents in the woods outside Millport'),
    ('compoundpttyabandonedcommunitycenter', 'ptty', 'compound', 'Abandoned Community Center', 'Kamar Devon community center, Southside'),
    ('compoundpttyhouselockup', 'ptty', 'compound', 'House Lockup', None),
    ('compoundpttyillegalgoodsstore', 'ptty', 'compound', 'Illegal Goods Store', None),
    ('compoundcriminalcartheftring', 'criminal', 'compound', 'Car Theft Ring', None),
    ('compoundcriminaldrugkingpin', 'criminal', 'compound', 'Drug Kingpin', None),
    ('compoundcriminalecstasygarage', 'criminal', 'compound', 'Ecstasy Garage', 'ecstasy lab behind a garage door in Ocean Beach'),
    ('compoundcriminalgraffitilab', 'criminal', 'compound', 'Graffiti Lab', None),
    ('compoundcriminalindustrialweedgrow', 'criminal', 'compound', 'Industrial Weed Grow', 'factory in North Mariana County'),
    ('compoundcriminalmushroomgrow', 'criminal', 'compound', 'Mushroom Grow', 'remote farm in Frogswater'),
    ('compoundcriminalnarcoboatrunner', 'criminal', 'compound', 'Narco Boat Runner', None),
    ('compoundcriminalvehiclechopshop', 'criminal', 'compound', 'Vehicle Chop Shop', 'chop shop in a towing lot in Salton'),
    ('compoundcriminalweaponsexport', 'criminal', 'compound', 'Weapons Export', 'secure storage compound in Balsero'),
    ('frontcriminalcigarimport', 'criminal', 'front', 'Cigar Import (front)', 'back room of a liquor store in La Perle'),
    ('frontcriminalexoticanimals', 'criminal', 'front', 'Exotic Animals (front)', 'liquor store in Key Lento'),
    ('frontcriminalgasstationmeth', 'criminal', 'front', 'Gas Station Meth (front)', 'gas station in Emerald Springs'),
    (0x7fc09fac, 'criminal', 'front', 'Barbershop Drugs (front)', 'the game text has a "Barbershop Weed Front"'),
    ('bankdruthers', None, 'bank', 'Bank (Druthers)', None),
    ('bankfleecavcia', None, 'bank', 'Bank (Fleeca VCIA)', None),
)
CRACKED = {0x7fc09fac: ('frontcriminalbarbershopdrugs', 'likely'), 0xe6902700: ('compoundkoltarmadillotycoon', 'weak')}

SLOTS = (0x1a4b1e08, 0x28c1baf5, 0x76fb5767, 0x8544f3fa)
B_SLOT_TAKEN, B_SLOT_ITEM = 0x0e3a164e, 0x6112a557
ITEM_LABELS = {0x6a3946ae: 'Crowex Watch', 0x0368ccbe: 'Crowex Watch', 0x15c91700: 'Custom weapon', 0x06986915: 'Custom vehicle',
               0xe5b9646b: 'Unique Variant', 0xc8134591: 'Office Safe', 0x3825210a: 'Safe', 0x15475845: 'Safe', 0x4397cd0d: 'Safe',
               0x83e256d7: 'Locked Safe', 0x5a21ff87: 'Closet Safe', 0x128d726e: 'Upstairs Safe'}
PER_GANG = (('discovered', 'ganglocationsdiscovered'), ('cleared', 'ganglocationscleared'), ('goodsStolen', 'valuestolen'),
            ('encounters', 'uniqueencounters'), ('membersKilled', 'kills'), ('hits', 'successfulhits'),
            ('uniqueHits', 'uniquehits'), ('itemsFound', 'uniqueitemsfound'))


def _owner(x):
    return x if isinstance(x, int) else fl.joaat(x)


def _hash(v):
    return int(v['$data'], 16) & fl.M32 if isinstance(v, dict) else v & fl.M32


def _bits(rec):
    d = rec[K_BITS]
    words = [int(w, 16) for w in d.get('$data') or []]
    v = sum(w << (32 * i) for i, w in enumerate(words))
    return bin(v).count('1'), d['$bits']


def _state(cleared, looted, discovered, tipped, registered):
    if cleared:
        return 'cleared'
    if looted:
        return 'partly looted, valuables left'
    if discovered:
        return 'discovered'
    if tipped:
        return 'tip on the map'
    if registered:
        return 'registered by the game, not discovered'
    return 'not found yet'


def read(b):
    s = fl.Save(b)
    st = fl.Stats(s.text(fl.STATS))
    ent = fl.payload(s.text(SEC_ENTERPRISES), SEC_ENTERPRISES)
    data = {e[K_ID] & fl.M32: e for e in ent[K_DATA]}
    known = {e[K_ID] & fl.M32: bool(e[K_KNOWN]) for e in ent[K_GANGS]}
    dis = fl.payload(s.text(SEC_DISCOVERY), SEC_DISCOVERY)
    done_cats = {_hash(x) for x in dis[K_DISCOVERED]}
    cats = {_hash(r[K_NAME]): r for r in dis[K_CATS]}
    flags = {_hash(e[K_NAME]): e[K_STATEFLAGS] for e in dis[K_FLAGSTATE]}

    def stat(base, qual=0, owner=STORY):
        return st.value(base, qual, owner)

    locations, sums, in_sync = [], {}, True
    for name, gang, kind, label, hint in LOCATIONS:
        o = _owner(name)
        own = name if isinstance(name, str) else CRACKED[o][0]
        discovered, cleared = stat('ganglocationdiscovered', 0, o), stat('ganglocationcleared', 0, o)
        hits, items = stat('successfulhits', 0, o), stat('uniqueitemsfound', 0, o)
        if discovered is None or cleared is None:
            raise fl.FeatureError('layout_changed')
        slots = []
        for q in SLOTS:
            taken, item = stat(B_SLOT_TAKEN, q, o), stat(B_SLOT_ITEM, q, o)
            if taken or item:
                slots.append({'slot': fl.hexid(q), 'item': ITEM_LABELS.get(item & fl.M32, fl.hexid(item)) if item else None,
                              'taken': bool(taken)})
        e = data.get(o)
        f = flags.get(o)
        status = e[K_STATUS] if e else None
        tipped = bool((status or 0) & ST_TIP) or bool((f or 0) & FS_TIP)
        rec = None
        if e:
            tasks = e.get(K_TASKS) or []
            rec = {'status': status, 'discovered': bool(status & ST_DISCOVERED), 'hit': bool(status & ST_HIT),
                   'cleared': bool(status & ST_CLEARED), 'tip': bool(status & ST_TIP),
                   'tasks': {'resolved': sum(1 for t in tasks if t[K_TASK_RESOLVED]), 'of': len(tasks)}}
        sync = (rec is None and not (discovered or cleared or hits)) or (
            rec is not None and rec['discovered'] == bool(discovered) and rec['cleared'] == bool(cleared) and rec['hit'] == bool(hits))
        if f is not None:
            sync = sync and bool(f & FS_DISCOVERED) == bool(discovered) and bool(f & FS_CLEARED) == bool(cleared)
        in_sync = in_sync and sync
        locations.append({'id': fl.hexid(o), 'owner': own, 'nameConfidence': CRACKED[o][1] if o in CRACKED else 'known',
                          'gang': gang, 'kind': kind, 'label': label, 'hint': hint,
                          'state': _state(cleared, hits or items, discovered, tipped, e is not None),
                          'discovered': bool(discovered), 'cleared': bool(cleared), 'hits': hits, 'itemsFound': items,
                          'items': slots, 'enterprise': rec, 'mapFlags': None if f is None else '0x%x' % f, 'inSync': sync})
        if gang:
            g = sums.setdefault(gang, {'discovered': 0, 'cleared': 0, 'hits': 0, 'itemsFound': 0, 'uniqueHits': 0})
            g['discovered'] += bool(discovered)
            g['cleared'] += bool(cleared)
            g['hits'] += hits
            g['itemsFound'] += items
            g['uniqueHits'] += bool(hits)

    gangs = []
    for key, q, display, cat in GANGS:
        counters = {k: stat(base, q) for k, base in PER_GANG}
        if cat in cats:
            n, size = _bits(cats[cat])
            category = {'known': n, 'size': size, 'complete': False}
        elif cat in done_cats:
            category = {'known': None, 'size': None, 'complete': True}
        else:
            category = {'known': 0, 'size': None, 'complete': False}
        mine = [x for x in locations if x['gang'] == key]
        sm = sums.get(key, {})
        if category['size'] is not None:
            of, of_source = category['size'], 'map category size'
        else:
            of, of_source = CATEGORY_SIZES.get(cat), 'map category size seen in other saves of this console'
        gangs.append({'key': key, 'name': display, 'qualifier': fl.hexid(q), 'known': known.get(q),
                      'counters': counters, 'mapCategory': category,
                      'page': {'OPERATIONS DISCOVERED': counters['discovered'], 'OPERATIONS CLEARED': counters['cleared'],
                               'of': of, 'ofSource': of_source, 'OPERATION GOODS STOLEN': counters['goodsStolen'],
                               'ENCOUNTERS': counters['encounters'], 'MEMBERS KILLED': counters['membersKilled']},
                      'countersMatchLocations': all(counters[k] == sm.get(k, 0) for k in ('discovered', 'cleared', 'hits', 'itemsFound', 'uniqueHits')),
                      'locations': [x['owner'] for x in mine],
                      'left': [{'label': x['label'], 'state': x['state'], 'hint': x['hint']} for x in mine if not x['cleared']]})
    fronts = {'known': 0, 'size': CATEGORY_SIZES[FRONTS_CATEGORY], 'complete': FRONTS_CATEGORY in done_cats}
    if FRONTS_CATEGORY in cats:
        fronts['known'], fronts['size'] = _bits(cats[FRONTS_CATEGORY])

    total = {k: stat(base, ALL) for k, base in PER_GANG}
    all_sum = {k: sum(g.get(k, 0) for g in sums.values()) for k in ('discovered', 'cleared', 'hits', 'itemsFound', 'uniqueHits')}
    cleared = total['cleared']
    pct = stat('totalprogressmade', 'allgangs')
    expected = fl.pct32(cleared or 0, OF)
    return {'feature': FEATURE,
            'checklist': {'label': 'GANG OPERATIONS CLEARED', 'value': cleared, 'of': OF, 'shown': min(cleared or 0, OF),
                          'percent': pct, 'percentExpected': expected,
                          'percentConsistent': pct is not None and abs(pct - expected) <= max(2e-6, abs(pct) * 2e-7), 'weight': 3},
            'allGangs': dict(total, hitTogether=stat('successfulhits', ALL, 'withpartner'),
                             countersMatchLocations=all(total[k] == all_sum[k] for k in all_sum)),
            'gangs': gangs,
            'frontsCategory': fronts,
            'locations': locations,
            'sectionsInSync': in_sync,
            'left': OF - min(cleared or 0, OF),
            'editable': False,
            'risk': 'not offered',
            'why': ['A clear is written in three places (stats, Enterprises, the map), and they agree in every game-written save.',
                    '23 of 44 locations have no Enterprises record; their tip, tasks and unique items are not in the save.',
                    'The unique items (custom weapons, vehicles, watches, safe cash) would never be given, and a later real '
                    'clear would count the location again.',
                    'Which 39 of the 44 locations count is not settled.'],
            'notes': ['Each gang page reads its stats counters; the "of" total is the size of the gang\'s map category '
                      '(Kingfishers 3, as on screen). Guardia Brothers\' category is complete, so its size is not stored (3 '
                      'locations).',
                      'The map categories hold 41 locations, the stats 44 owners and the checklist asks for 39.',
                      'Hints are from the game\'s own descriptions, matched by place words; check them in game.']}
