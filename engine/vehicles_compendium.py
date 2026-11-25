"""BASE MODEL VEHICLES x / 200 on the 100% checklist: add vehicle models to the compendium (Save Garage feature module).

WHAT THE LINE READS
  studied.<2b12592f>/story000, the base-model counter (163 at 67.5%; compendium.py), with its cached percentage
  totalprogressmade.vehiclesdiscovered = float32(min(base, 200) / 200) * 100 (81.5 = 163/200).

WHAT IT CHANGES (the minimum consistent edit)
  Section dbf71c51 (DiscoverableMemoryData), DiscoverableType 3: joaat(model) appended to NameHashes and flag 1 to
  Flags for each added model (the plain 'discovered' state; compendium.py).
  Stats 0635cbd9, story000, by the number of models added:
    * studied.<2b12592f> (base models) and studied.vehicles (+n each; every added model is a base model);
    * studied.<page> for the compendium page of each model (+1 per model; see PAGES);
    * totalprogressmade.vehiclesdiscovered, and the overall figure through checklist.refresh_overall.
  Challenges 3000010d: incomplete trackers whose score equals the old value of a moved counter follow it (the
  EXPLORATION 'discover vehicles' tracker reads studied.vehicles while it is incomplete; complete in A6b).
  'min' (the default) adds just enough models to reach 200; 'all' adds every candidate.

THE 44 PAGE COUNTERS (settled here)
  The compendium has 44 page counters studied.<page> (CARS 9, SERVICE 6, STANDOUT 25 category pages, plus BIKES,
  WATERCRAFT, AIRCRAFT); with the equipment counter their sum is studied.vehicles + the type-6 tools in every save.
  A vehicle site's category list (gtazone, via the SaveRift data file: model hash -> category) gives, for each save,
  how many listed vehicles fall in each category. For 12 categories that count equals one page counter in all 14
  game-written saves of both playthroughs (A0..A6b, B7as_a..B7b), value by value:
    Coupes ee17db65 (13 at 67.5%, the screen's 'COUPES 13 / 18'), Muscle Cars 797cf81e, SUVs 97f2e8d3, Pickups
    c82e2dbe, Sports 9ef3195e, Supercars 37a38f02, Vans 5f3ef66d, Utility 7fe14bbb, Emergency 32f90aa2, Military
    0085e736, Trucks adeae663 or ea384fd4 (the screen's 'TRUCKS 2 / 11'), Transport 704b9a5f or 8b30431d.
  Close but not exact, because vehicles listed under a key that is not their model hash have no category in the
  list: Bikes 8e0937f5, Sedans b34a29b2, Watercraft 1022c6ab (always exactly 5 more in playthrough A: the five boats
  listed under such keys, Airboat 09, S23 CCS, Sea Enchantress, Hydroblast, Shining Sea Squalo), Aircraft 436bbda1,
  Off-Road 631ba30a. (Analysis script: work/act2/veh_pages.py.)
  So the page of a model is known, and this module only adds models from the eight car/utility categories whose
  series match exactly and that have one counter: their page counters stay in step and the sum rule holds.

WHY ONLY THOSE MODELS (the key and membership risks)
  * The compendium key is joaat(model) for 153 of the 176 vehicles seen, but not for 23 (for example the driven
    'airgator' is listed as e54c8bcf 'Airboat 09', 'bombora' as 1b0b0c83 'S23 CCS'): boats, aircraft, industrial
    vehicles and special cars. In the eight chosen categories every discovered vehicle in 14 saves used its model
    hash (otherwise the series would not match), so joaat(model) is the right key there.
  * Membership: the site lists 18 coupes, exactly the screen's 18, and its 11 trucks match the screen's 11. For the
    other categories the page totals are not on screen; base-spec stats rows exist for every candidate.
  * Emergency and Military are left out (police variants are listed but not counted), as are Trucks and Transport
    (two possible counters each).
  With the save at 163 the eight categories leave 45 candidates: 'min' takes 37 (Coupes 5, SUVs 5, Pickups 5,
  Sports 3, Supercars 1, Vans 6, Utility 6, then 6 Muscle Cars in alphabetical order). A save with fewer base models
  cannot reach 200 from this set; the log says how far it got.

RISK: medium. The page mapping rests on exact series matches; the category list is third-party; nothing has been
loaded on a PS5. The game shows the added models as discovered but never driven (no stats beyond the counters).
"""
import challenges
import checklist
import compendium
import featurelib as fl

FEATURE = 'vehicles_compendium'
SEC = compendium.SEC
T_VEHICLES = compendium.T_VEHICLES
STUDIED = 'studied'
C_VEHICLES, C_BASE = 'vehicles', 0x2b12592f
FOR_100 = 200
PCT = ('totalprogressmade', 'vehiclesdiscovered')
FLAG = 1

# category -> (page counter studied.<q>, models with a <model>_base_spec stats row in that category); order = 'min' order
PAGES = (
    ('Coupes', 0xee17db65, ('akane', 'arcturus', 'blista2', 'cypher', 'drafter', 'elegy', 'fr36', 'futo', 'hustler', 'lasso',
                            'paragon', 'penumbra', 'penumbraff', 'ruiner', 'schutzen', 'vectre', 'windsor2', 'zion2')),
    ('SUVs', 0x97f2e8d3, ('aleutian', 'allander', 'astron', 'baller2', 'baller8', 'cavalcade3', 'crawler', 'dorado', 'dubsta',
                          'granger', 'granger3600lx', 'gresleyxt', 'hellion', 'jubilee', 'kamacho', 'landstalker2', 'mesa',
                          'montagne', 'montagnexl', 'reblagts', 'riataclassic', 'toros', 'xls')),
    ('Pickups', 0xc82e2dbe, ('bison', 'bison1800', 'bison3800', 'bison900', 'bobcatxl', 'caracara4x4', 'contender', 'montagnepu',
                             'rancher', 'rebel', 'reclaimer', 'reclaimerclassic', 'riata', 'sandking_4dr', 'sandkingxt', 'walton',
                             'yosemite1500')),
    ('Sports', 0x9ef3195e, ('banshee', 'carbonizzare', 'comet7', 'cometretro', 'coquette', 'coquette4', 'growler', 'mambagt',
                            'neon', 'schafter3', 'sentinelclassic2', 'sultan', 'wymankitcar')),
    ('Supercars', 0x37a38f02, ('cheetah2', 'emerus', 'furia', 'infernus2', 'italirsx', 'tempesta', 'thrax', 'vitello', 'zorrusso')),
    ('Vans', 0x5f3ef66d, ('boxville', 'burrito', 'minivan', 'moocher', 'rumpo', 'shifter', 'shuttle', 'speedo', 'spritz',
                          'trotter', 'vivanite', 'youga2', 'yougaxl')),
    ('Utility', 0x7fe14bbb, ('airtug', 'caddy', 'caddy2', 'forklift', 'golfcarthotrod', 'ripley', 'taco', 'telehandler', 'towtruck')),
    ('Muscle Cars', 0x797cf81e, ('buccaneer', 'chino', 'coquette2', 'declasse500', 'devanity', 'deviant', 'dominator', 'dominator7',
                                 'dominator9', 'dominatorclassic', 'ganado', 'gauntlet4', 'gauntlet5', 'hermes', 'manana', 'phoenix',
                                 'picador', 'slamvan', 'stallion', 'stanier55', 'transgressor', 'tulip', 'tulip2', 'vamos',
                                 'vigero3', 'yosemite')),
)
# the other page counters identified by series (not used for adding; documented and tested)
OTHER_PAGES = {'Emergency': (0x32f90aa2,), 'Military': (0x0085e736,), 'Trucks': (0xadeae663, 0xea384fd4),
               'Transport Vehicles': (0x704b9a5f, 0x8b30431d), 'Bikes': (0x8e0937f5,), 'Sedans': (0xb34a29b2,),
               'Watercraft': (0x1022c6ab,), 'Aircraft': (0x436bbda1,), 'Off-Road Vehicles': (0x631ba30a,)}
PAGE_OF = {m: (cat, q) for cat, q, models in PAGES for m in models}
ORDER = [m for _, _, models in PAGES for m in models]


def _listed(t):
    return {h for h, _ in compendium._lists(t).get(T_VEHICLES, [])}


def _studied_pages(st):
    """{page qualifier: value} of every studied.<q>/story000 row that is not one of the six totals."""
    tot = {fl.joaat('vehicles'), fl.joaat('animals'), fl.joaat('weapons'), 0x2b12592f, 0x8dc8c123, 0x4fa68fa3}
    A, Q, O = st.tables['base'], st.tables['qual'], st.tables['owner']
    out = {}
    for (b, q, o), (g, r) in st.where.items():
        if b == fl.joaat(STUDIED) and o == fl.joaat('story000') and q not in tot:
            out[q] = st.value(b, q)
    return out


def read(b):
    s = fl.Save(b)
    st = fl.Stats(s.text(fl.STATS))
    listed = _listed(s.text(SEC))
    pages = []
    for cat, q, models in PAGES:
        have = [m for m in models if fl.joaat(m) in listed]
        pages.append({'category': cat, 'counter': fl.hexid(q), 'value': st.value(STUDIED, q), 'models': len(models),
                      'listed': len(have), 'consistent': st.value(STUDIED, q) == len(have),
                      'missing': [m for m in models if fl.joaat(m) not in listed]})
    base = st.value(STUDIED, C_BASE)
    allpages = _studied_pages(st)
    tools = len(compendium._lists(s.text(SEC)).get(compendium.T_EQUIPMENT, []))
    return {'feature': FEATURE, 'checklist': {'label': 'BASE MODEL VEHICLES', 'value': base, 'of': FOR_100},
            'percent': st.value(*PCT), 'studiedVehicles': st.value(STUDIED, C_VEHICLES), 'listed': len(listed),
            'pages': pages, 'candidates': sum(len(p['missing']) for p in pages),
            'needed': max(0, FOR_100 - (base or 0)),
            'pageSumConsistent': sum(allpages.values()) == (st.value(STUDIED, C_VEHICLES) or 0) + tools,
            'possible': [m for p in pages for m in p['missing']], 'risk': 'medium',
            'notes': ['Adds base models from eight car/utility pages whose page counters match the saves exactly, with '
                      "their page counters, so 'COUPES 13 / 18' and the other pages stay right.",
                      'The models show as discovered but never driven.']}


def apply(b, choice=None):
    """choice: {'count': 'min' | 'all' | int, 'models': [model names] (optional filter)} -> (new bytes, log)."""
    choice = choice or {}
    count = choice.get('count', 'min')
    want = choice.get('models')
    if want is not None:
        if isinstance(want, (str, bytes)) or any(m not in PAGE_OF for m in want):
            raise fl.FeatureError('unknown_model')
    if not (count in ('min', 'all') or (isinstance(count, int) and not isinstance(count, bool) and count >= 0)):
        raise fl.FeatureError('bad_request')
    s = fl.Save(b)
    t = s.text(SEC)
    listed = _listed(t)
    st = fl.Stats(s.text(fl.STATS))
    base = st.value(STUDIED, C_BASE)
    if base is None:
        raise fl.FeatureError('layout_changed')
    pool = [m for m in ORDER if fl.joaat(m) not in listed and (want is None or m in want)]
    n = len(pool) if count == 'all' else (max(0, FOR_100 - base) if count == 'min' else count)
    add = pool[:n]
    log = []
    if count == 'min' and len(add) < FOR_100 - base:
        log.append({'what': 'short_of_target', 'base': base, 'added': len(add), 'needed': FOR_100 - base})
    if not add:
        return b, log
    t = compendium._append(t, T_VEHICLES, [fl.joaat(m) for m in add], FLAG)
    s.set_text(SEC, t)
    moved = {}

    def bump(q, k, label):
        old = st.value(STUDIED, q)
        if old is None:
            raise fl.FeatureError('layout_changed')
        st.set(STUDIED, q, old + k, label)
        moved[(fl.joaat(STUDIED), fl.h(q), fl.joaat('story000'))] = (old, old + k)

    bump(C_VEHICLES, len(add), 'Vehicles discovered')
    bump(C_BASE, len(add), 'Base model vehicles discovered')
    per = {}
    for m in add:
        cat, q = PAGE_OF[m]
        per[(cat, q)] = per.get((cat, q), 0) + 1
    for (cat, q), k in per.items():
        bump(q, k, 'Vehicle compendium page: ' + cat)
    st.set(PCT[0], PCT[1], fl.pct32(base + len(add), FOR_100), 'Vehicles, part of 100% completion')
    checklist.refresh_overall(st)
    log.append({'what': 'compendium_vehicles', 'added': len(add), 'flag': FLAG, 'models': add,
                'pages': {cat: k for (cat, _), k in per.items()}})
    import activities2
    ct = s.text(challenges.SEC)
    ct2, tlog = activities2.mirror_trackers(ct, moved)
    if ct2 != ct:
        s.set_text(challenges.SEC, ct2)
    txt, slog = st.apply()
    s.set_text(fl.STATS, txt)
    return s.build(), log + tlog + slog
