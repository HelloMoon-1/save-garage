# Save Garage - Copyright (C) 2026 NotHGM - GNU GPL v3 with the additional terms in NOTICE; see LICENSE.
"""BASE MODEL VEHICLES x / 200 on the 100% checklist: add vehicle models to the compendium (Save Garage feature module).

WHAT THE LINE READS
  studied.<2b12592f>/story000, the base-model counter (163 at 67.5%; compendium.py), with its cached percentage
  totalprogressmade.vehiclesdiscovered = float32(min(base, 200) / 200) * 100 (81.5 = 163/200). The game has 277 base
  models (PowerPyx: 'any 200 of the 277 base model vehicles'); 280 standout vehicles are counted elsewhere.

WHAT IT CHANGES (the minimum consistent edit)
  Section dbf71c51 (DiscoverableMemoryData), DiscoverableType 3: the model's compendium key appended to NameHashes and
  flag 1 to Flags for each added model (the plain 'discovered' state; compendium.py).
  Stats 0635cbd9, story000, by the number of models added:
    * studied.<2b12592f> (base models) and studied.vehicles (+n each; every added model is a base model);
    * studied.<page> for the compendium page of each model (+1 per model; see PAGES);
    * totalprogressmade.vehiclesdiscovered, and the overall figure through checklist.refresh_overall.
  Challenges 3000010d: incomplete trackers whose score equals the old value of a moved counter follow it (the
  EXPLORATION 'discover vehicles' tracker reads studied.vehicles while it is incomplete; complete in A6b).
  'min' (the default) adds just enough models to reach 200; 'all' adds every candidate.

THE COMPENDIUM KEY IS THE VEHICLE'S gameName (settled in round 16)
  The key of a listed vehicle is joaat(gameName), the game-text key of its display name (table C0898). For most
  vehicles the gameName is the model name, so the key is joaat(model): 153 of the 176 vehicles seen in the 20 saves.
  For ten it is not, and all ten were cracked against the keys seen in game-written lists (GAME_NAMES): 60 guesses gave
  12 hits, all on seen keys, and 0 hits on 100,000 random decoys (expected 0.0014); the last three came from a token
  grammar, 3 of 3 targets and 0 of 30 decoys. Example: the driven 'airgator' is listed as e54c8bcf = joaat('airboat'),
  whose text is 'Airboat 09'. Two of them are the model name cut to 11 characters (seaenchantr, dominatorbu).
  The 23 listed keys that are not joaat(model) are now all accounted for: the 10 gameNames, 11 standout vehicles
  (C0924 kit keys or unnamed, all on STANDOUT pages), the uncounted Police Lowline, and one base model 865b7f60 whose
  name is unknown (in every save of both playthroughs, on page 127d7901).

THE PAGE COUNTERS (settled; 4 more in round 16)
  The compendium has 44 page counters studied.<page> (CARS 9, SERVICE 6, STANDOUT 25 category pages, plus BIKES,
  WATERCRAFT, AIRCRAFT); with the equipment counter their sum is studied.vehicles + the type-6 tools in every save.
  A vehicle site's category list (GTA.ZONE, via the SaveRift data file) with the game's display names and the gameNames
  gives, for each save, how many listed vehicles fall in each category. For 18 categories that count equals a page
  counter in all 14 game-written saves of both playthroughs (A0..A6b, B7as_a..B7b), value by value:
    Coupes ee17db65 (13 at 67.5%, the screen's 'COUPES 13 / 18'), Muscle Cars 797cf81e, SUVs 97f2e8d3, Pickups
    c82e2dbe, Sports 9ef3195e, Supercars 37a38f02, Vans 5f3ef66d, Utility 7fe14bbb, Emergency 32f90aa2, Military
    0085e736, and since round 16 Bikes 8e0937f5, Sedans b34a29b2, Aircraft 436bbda1 and Watercraft 1022c6ab (they
    were only close before, because Boomazoom, Transient, SuperVolito and five boats are listed under gameName keys).
  Four categories match two counters each, because one of each pair is a STANDOUT page whose series happens to be
  identical in these saves: Off-Road acc5c529/7ac90154, Industrial bd646822/8bd2aa53, Transport 8b30431d/704b9a5f,
  Trucks adeae663/ea384fd4. A save with more vehicles will separate them; until then they are not used.
  The page totals match the screen where it was seen: the site's 18 coupes, 11 trucks and 28 boats ('WATERCRAFT x / 28').
  The site lists 271 'Discover in game' base models plus 4 Ultimate Edition and 1 pack vehicle; with 865b7f60 that is
  277, the guides' number. (Analysis: research_scratch/names/round16/tasks_gangs_vehicles/scripts/v3_pages.py,
  v9_keys2.py, v10_catalogue.py.)

WHICH MODELS ARE OFFERED (the key and membership risks)
  Only models on the 12 pages with a single confirmed counter, minus Emergency and Military (police variants are listed
  but not counted), and only with a key graded:
    * confirmed: the key was seen in a game-written compendium list (148 offered), or the game's own vehicle data
      gives the model's gameName (VEHICLE_DATA, 69 offered). DurtyFree's GTA VI vehicles.json (build 1.0.2.1) names
      the gameName of 190 of the 231 page members and never contradicts a key: 117 of them were seen in saves, 64 had
      been graded likely, 5 were held back as weak and 4 are edition vehicles. For all 190 the gameName is the model
      name;
    * likely: joaat(model) is the only C0898 key carrying the model's display name (6 offered). That rule holds for
      135 of 135 seen vehicles it applies to and for the 64 the vehicle data confirms, and none of the ten gameName
      vehicles falls under it.
  Held back (NOT_OFFERED): 3 models whose key is weak (no name key for the model, or several keys carry the same name)
  and the 5 Ultimate Edition / pack vehicles, which a standard copy of the game does not have. They stay page members,
  so a page still reads as consistent when the game lists them.
  Every offered model has a <model>_base_spec stats row. 'min' takes the pages in the order of PAGES (the eight car and
  utility pages first, as before, then Sedans, Bikes, Watercraft, Aircraft) and models in alphabetical order. With the
  save at 163 it adds 37 models from the car and utility pages (2 with a likely key); an early save (playthrough B,
  4 base models) reaches 200 using the new pages (5 with a likely key).

RISK: medium. The page mapping rests on exact series matches; the category list is third-party; 6 of the offered keys
are inferred from the game text alone (likely) and 69 come from the game's vehicle data, not from a save; nothing has
been loaded on a PS5. The game shows the added models as discovered but never driven (no stats beyond the counters).
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

# model -> gameName where they differ (each joaat equals a key seen in a game-written compendium list; round 16)
GAME_NAMES = {'airgator': 'airboat', 'bombora': 's23', 'willard': 'transient', 'digger': 'excavator',
              'mobilityscooter': 'mobility', 'lurepredator': 'l35p', 'seashark': 'hydroblast', 'seaenchantress': 'seaenchantr',
              'dominatorbuggy': 'dominatorbu', 'supervolito': 'svolito'}


def key_of(model):
    """Compendium key of a model: joaat(gameName)."""
    return fl.joaat(GAME_NAMES.get(model, model))


# category -> (page counter studied.<q>, every base model of the page); order = 'min' order
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
    ('Vans', 0x5f3ef66d, ('boxville', 'burrito', 'journey', 'minivan', 'moocher', 'rumpo', 'shifter', 'shuttle', 'speedo',
                          'spritz', 'trotter', 'vivanite', 'youga2', 'yougaxl')),
    ('Utility', 0x7fe14bbb, ('airtug', 'caddy', 'caddy2', 'forklift', 'golfcarthotrod', 'ripley', 'taco', 'telehandler',
                             'towtruck')),
    ('Muscle Cars', 0x797cf81e, ('buccaneer', 'chino', 'coquette2', 'declasse500', 'devanity', 'deviant', 'dominator', 'dominator7',
                                 'dominator9', 'dominatorclassic', 'ganado', 'gauntlet4', 'gauntlet5', 'hermes', 'manana', 'phoenix',
                                 'picador', 'slamvan', 'stallion', 'stanier55', 'transgressor', 'tulip', 'tulip2', 'vamos',
                                 'vigero3', 'yosemite')),
    ('Sedans', 0xb34a29b2, ('animus', 'asterope2', 'bogan', 'buffalo', 'buffalo6', 'chavosxs', 'emperor', 'feroci', 'greta',
                            'grouse', 'impaler5', 'impaler6', 'intruder', 'jugular', 'lowline', 'meritlx', 'parkland', 'pmp700',
                            'primo', 'raiden', 'schafters', 'stanier', 'stanierg2', 'sugoi', 'sungrazer', 'tailgater2', 'vstr',
                            'willard', 'woodland')),
    ('Bikes', 0x8e0937f5, ('alvinov1', 'aphid', 'avarus', 'blazer4', 'bmx', 'carbonrs', 'cliffhanger', 'cruiser', 'crusher',
                           'double', 'eboost', 'enduro', 'erode', 'esskey', 'fcr', 'lectro', 'lombike', 'manchez',
                           'mobilityscooter', 'nightblade2', 'nimbe', 'ragno', 'sanchez', 'scorcher', 'sfb1000', 'sovereign107',
                           'tribike', 'verus', 'zombieb')),
    ('Watercraft', 0x1022c6ab, ('airgator', 'azure', 'blade500', 'bombora', 'calder', 'clarion', 'cretacean', 'dibnah', 'dinghy',
                                'flatdeck', 'fortune', 'hemming', 'kayak', 'lurepredator', 'marquis', 'nepa', 'pontoon', 'rhode',
                                'seaenchantress', 'seashark', 'sedna', 'shasa', 'skivvy', 'speeder700gt', 'squalo', 'tao', 'torlan',
                                'yakuruna')),
    ('Aircraft', 0x436bbda1, ('216cstreamer', 'crake', 'dodo', 'duster', 'duster2', 'jet', 'jet2', 'mallard', 'mammatus',
                              'maverick', 'nimbus', 'seasparrow', 'shamal', 'supervolito', 'swift', 'volatus')),
)
# page members that are never added, with the reason
NOT_OFFERED = dict(
    [(m, 'key weak: no name key for the model, or several game-text keys carry its display name')
     for m in ('216cstreamer', 'calder', 'swift')] +
    [(m, 'Ultimate Edition vehicle') for m in ('deviant', 'riataclassic', 'transgressor', 'wymankitcar')] +
    [('stanier55', 'pack vehicle (Vintage Vice City)')])
# offered models whose key is inferred from the game text alone (the rest are confirmed)
LIKELY = frozenset(('aleutian', 'azure', 'esskey', 'shamal', 'taco', 'woodland'))
# confirmed by the game's own vehicle data rather than a save list: DurtyFree's GTA VI vehicles.json (build 1.0.2.1)
# gives these models' gameName, and it is the model name, so the key is joaat(model)
VEHICLE_DATA = frozenset((
    'aphid', 'arcturus', 'blazer4', 'bobcatxl', 'buccaneer', 'caddy2', 'carbonrs', 'chino', 'cliffhanger', 'cometretro',
    'coquette2', 'crake', 'cretacean', 'crusher', 'declasse500', 'devanity', 'dibnah', 'dominator7', 'double', 'drafter',
    'duster', 'emerus', 'fcr', 'flatdeck', 'forklift', 'fortune', 'fr36', 'gauntlet5', 'golfcarthotrod', 'gresleyxt',
    'growler', 'hermes', 'journey', 'kamacho', 'lectro', 'mallard', 'marquis', 'mesa', 'montagnepu', 'moocher', 'nimbus',
    'penumbraff', 'pmp700', 'pontoon', 'primo', 'reclaimerclassic', 'ripley', 'sandkingxt', 'sedna', 'shuttle', 'skivvy',
    'slamvan', 'spritz', 'sungrazer', 'tao', 'telehandler', 'torlan', 'tribike', 'trotter', 'tulip2', 'verus', 'vigero3',
    'volatus', 'walton', 'windsor2', 'yosemite', 'youga2', 'yougaxl', 'zombieb'))
# the other page counters identified by series (not used for adding; documented and tested)
OTHER_PAGES = {'Emergency': (0x32f90aa2,), 'Military': (0x0085e736,), 'Trucks': (0xadeae663, 0xea384fd4),
               'Transport Vehicles': (0x8b30431d, 0x704b9a5f), 'Industrial': (0xbd646822, 0x8bd2aa53),
               'Off-Road Vehicles': (0xacc5c529, 0x7ac90154),
               'base model 865b7f60 (name unknown) and one more entry': (0x127d7901,)}
PAGE_OF = {m: (cat, q) for cat, q, models in PAGES for m in models}
ORDER = [m for _, _, models in PAGES for m in models if m not in NOT_OFFERED]


def grade(model):
    if model in NOT_OFFERED:
        return 'held back'
    return 'likely' if model in LIKELY else 'confirmed'


def _listed(t):
    return {h for h, _ in compendium._lists(t).get(T_VEHICLES, [])}


def _studied_pages(st):
    """{page qualifier: value} of every studied.<q>/story000 row that is not one of the six totals."""
    tot = {fl.joaat('vehicles'), fl.joaat('animals'), fl.joaat('weapons'), 0x2b12592f, 0x8dc8c123, 0x4fa68fa3}
    out = {}
    for (b, q, o), (g, r) in st.where.items():
        if b == fl.joaat(STUDIED) and o == fl.joaat('story000') and q not in tot:
            out[q] = st.value(b, q)
    return out


def read(b):
    s = fl.Save(b)
    st = fl.Stats(s.text(fl.STATS))
    listed = _listed(s.text(SEC))
    base = st.value(STUDIED, C_BASE)
    pool = [m for m in ORDER if key_of(m) not in listed]
    need = max(0, FOR_100 - (base or 0))
    take = pool[:need]
    pages = []
    for cat, q, models in PAGES:
        have = [m for m in models if key_of(m) in listed]
        missing = [m for m in models if key_of(m) not in listed and m not in NOT_OFFERED]
        pages.append({'category': cat, 'counter': fl.hexid(q), 'value': st.value(STUDIED, q), 'models': len(models),
                      'listed': len(have), 'consistent': st.value(STUDIED, q) == len(have), 'missing': missing,
                      'candidates': [{'model': m, 'key': fl.hexid(key_of(m)), 'grade': grade(m)} for m in missing],
                      'heldBack': [{'model': m, 'why': NOT_OFFERED[m]} for m in models if key_of(m) not in listed and m in NOT_OFFERED],
                      'minAdds': sum(1 for m in take if PAGE_OF[m][0] == cat)})
    allpages = _studied_pages(st)
    tools = len(compendium._lists(s.text(SEC)).get(compendium.T_EQUIPMENT, []))
    return {'feature': FEATURE, 'checklist': {'label': 'BASE MODEL VEHICLES', 'value': base, 'of': FOR_100},
            'percent': st.value(*PCT), 'studiedVehicles': st.value(STUDIED, C_VEHICLES), 'listed': len(listed),
            'pages': pages, 'candidates': len(pool), 'needed': need,
            'min': {'adds': len(take), 'reaches': (base or 0) + len(take), 'short': need - len(take),
                    'likelyKeys': sum(1 for m in take if m in LIKELY),
                    'byPage': {p['category']: p['minAdds'] for p in pages if p['minAdds']}},
            'pageSumConsistent': sum(allpages.values()) == (st.value(STUDIED, C_VEHICLES) or 0) + tools,
            'possible': pool, 'risk': 'medium',
            'notes': ['Adds base models from twelve pages whose page counters match the saves exactly, with their page counters, so '
                      "'COUPES 13 / 18' and the other pages stay right. Boats, aircraft, bikes and sedans are included since round 16.",
                      'Keys are joaat(gameName): seen in a save (confirmed) or inferred from the game text (likely). Weak keys, '
                      'Emergency, Military, the four pages with two possible counters and Ultimate Edition / pack vehicles are left out.',
                      'The models show as discovered but never driven.']}


def apply(b, choice=None):
    """choice: {'count': 'min' | 'all' | int, 'models': [model names] (optional filter)} -> (new bytes, log)."""
    choice = choice or {}
    count = choice.get('count', 'min')
    want = choice.get('models')
    if want is not None:
        if isinstance(want, (str, bytes)) or any(m not in PAGE_OF for m in want):
            raise fl.FeatureError('unknown_model')
        if any(m in NOT_OFFERED for m in want):
            raise fl.FeatureError('not_offered')
    if not (count in ('min', 'all') or (isinstance(count, int) and not isinstance(count, bool) and count >= 0)):
        raise fl.FeatureError('bad_request')
    s = fl.Save(b)
    t = s.text(SEC)
    listed = _listed(t)
    st = fl.Stats(s.text(fl.STATS))
    base = st.value(STUDIED, C_BASE)
    if base is None:
        raise fl.FeatureError('layout_changed')
    pool = [m for m in ORDER if key_of(m) not in listed and (want is None or m in want)]
    n = len(pool) if count == 'all' else (max(0, FOR_100 - base) if count == 'min' else count)
    add = pool[:n]
    log = []
    if count == 'min' and len(add) < FOR_100 - base:
        log.append({'what': 'short_of_target', 'base': base, 'added': len(add), 'needed': FOR_100 - base})
    if not add:
        return b, log
    t = compendium._append(t, T_VEHICLES, [key_of(m) for m in add], FLAG)
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
                'likelyKeys': [m for m in add if m in LIKELY], 'pages': {cat: k for (cat, _), k in per.items()}})
    import activities2
    ct = s.text(challenges.SEC)
    ct2, tlog = activities2.mirror_trackers(ct, moved)
    if ct2 != ct:
        s.set_text(challenges.SEC, ct2)
    txt, slog = st.apply()
    s.set_text(fl.STATS, txt)
    return s.build(), log + tlog + slog
