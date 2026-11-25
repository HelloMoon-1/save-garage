"""The 100% checklist and the overall '100% COMPLETION' figure (Save Garage feature module).

WHAT IT READS
  Every line of PROGRESS / STATS / GENERAL / 100% Completion, in screen order: the cached percentage
  totalprogressmade.<category>/story000 that the game keeps for the line, the counter it is computed from where that
  counter is known, the game's total, the line's weight in the overall figure, and the grade and module from
  research_notes/checklist-map.md (a = a module completes it, b = possible but risky, c = not from the save,
  done = an existing module).

WHAT IT CHANGES (apply)
  Stats section 0635cbd9, one row: totalprogressmade/story000 with no qualifier, the '100% COMPLETION' figure,
  recomputed from the 35 cached category percentages. Nothing else. The other feature modules (stunts, challenges,
  compendium, hoops...) change a category percentage but leave this figure as it was; run this after them.
  activities.py calls refresh_overall() itself.

THE FORMULA AND ITS EVIDENCE
  overall = sum, over the 35 lines in screen order, of float32(weight / 100) * percentage, accumulated in float32.
  Weights (sum 100): story 50, optional tasks 6, gang operations 3, bank jobs, payday loan jobs, smash 'n' grabs,
  stick ups, the four fenced lines and vaults 2 each, every other line 1.
  * B7a: 0.50 * 5.94 (story) + 0.01 * 10 (weapons) + 0.01 * 2 (vehicles) = 3.09, the stored value.
  * B7a -> B7as_b, A5 -> A5as and A5as -> A6as each move a few categories; the whole-percent weights that explain
    them are unique (optional tasks 6; drugs, cash, jewelry, vehicles fenced, smash 'n' grabs, payday loans and bank
    jobs 2; stunts, styles, challenges 1). What is left is exactly 1% of the gang percentage in every save, so gang
    operations weigh 3.
  * The game's re-save of the 1,000 edit (A6b_mod -> A6c_as) recomputed totalprogressmade.challengescompleted
    18.571428 -> 100.0 from the edited counter and the overall figure 67.508736 -> 68.323021 (+0.814285 = 1% of
    +81.428572). So the game rebuilds both when it saves.
  * Accumulated in float32 in screen order, the formula gives the stored figure to the last printed digit in all 15
    game-written saves (A0..A6c_as, B7a..B7b); other summation orders match 5 to 8 of them.
  * Not pinned by data: the 11 lines that are 0 in every save (Kenton, cards, WAiNK, flamingos, playlists, race
    challenges, shooting ranges, pool, mini golf, drones, Bret). Weight 1 each is what makes the total exactly 100.
  * Each line's percentage is float32(min(count, total) / total) * 100 (fl.pct32) for every line whose counter is
    known (all 15 saves, 24 lines); optional tasks use count * 0.99 instead (14 of 15 saves to the last digit, one
    float32 step off in the 15th), and story is computed from ScriptGameCompletion.

LIMITS
  * Which of the two unnamed percentages 66d7b9dd / 69ed6abb is COCAINE FLAMINGOS DESTROYED (x / 100) and which is
    UNIQUE PLAYLISTS COMPLETED (x / 2) is not known: both are 0 in every save. Both weigh 1, so the overall figure
    does not depend on the answer.
  * Values of lines without a known counter are derived from their percentage (round(pct * total / 100)).
  * 'shown' caps the counter at the line's total, as the screen did for STANDARD ISSUE WEAPONS (counter 54, '50 / 50');
    whether every line caps that way is not known.

RISK: low. One cached float that the game rewrites on its next save anyway.
"""
import featurelib as fl

FEATURE = 'checklist'
TP = 'totalprogressmade'
ST = 'story000'
OVERALL = (TP, 0)

S_STORY, S_EXPLORE, S_DISCOVERY = 'STORY & TASKS', 'EXPLORATION & ACTIVITIES', 'DISCOVERY'


def _l(key, qual, label, section, of, weight, counter=None, grade='c', module=None, unit='count'):
    return {'key': key, 'qual': qual, 'label': label, 'section': section, 'of': of, 'weight': weight,
            'counter': counter, 'grade': grade, 'module': module, 'unit': unit}


# Screen order. counter = (base, qualifier, owner); qualifier 0 = none. Hex ints are names not yet cracked.
LINES = (
    _l('story', 'story', 'STORY COMPLETION', S_STORY, None, 50, unit='percent'),
    _l('optionaltasks', 'optionaltasks', 'OPTIONAL TASKS COMPLETED', S_STORY, 100, 6, ('sidetaskscompleted', 0, ST)),
    _l('gangs', 'allgangs', 'GANG OPERATIONS CLEARED', S_STORY, 39, 3, ('ganglocationscleared', 'allgangs', ST), 'b'),
    _l('bankjobs', 'bankrobbery', 'BANK JOBS FULLY COMPLETED', S_STORY, 22, 2, (0x85209c63, 'bankrobbery', ST), 'a', 'robberies'),
    _l('paydayloans', 'paydayloanrobbery', 'PAYDAY LOAN JOBS FULLY COMPLETED', S_STORY, 7, 2, (0x85209c63, 'paydayloanrobbery', ST), 'a', 'robberies'),
    _l('smashngrabs', 'smashngrabsrobbery', "SMASH 'N' GRABS FULLY COMPLETED", S_STORY, 34, 2, (0x85209c63, 'smashngrabsrobbery', ST), 'a', 'robberies'),
    _l('stickups', 'holdupsrobbery', 'STICK UPS FULLY COMPLETED', S_STORY, 50, 2, (0x85209c63, 'holdupsrobbery', ST), 'a', 'robberies'),
    _l('narcotics', 'solddrugs', 'NARCOTICS FENCED', S_STORY, 100000, 2, ('lifetimemoneyearned', 'solddrugs', ST), 'a', 'fencing', unit='dollars'),
    _l('jewelry', 'soldjewelry', 'JEWELRY FENCED', S_STORY, 100000, 2, ('lifetimemoneyearned', 'soldjewelry', ST), 'a', 'fencing', unit='dollars'),
    _l('markedbills', 'soldcash', 'MARKED BILLS FENCED', S_STORY, 250000, 2, ('lifetimemoneyearned', 'soldcash', ST), 'a', 'fencing', unit='dollars'),
    _l('vaults', 'bankvaultrobbed', 'VAULTS HIT', S_STORY, 8, 2, ('robbedvaultsunique', 0, ST), 'a', 'robberies'),
    _l('vehiclesfenced', 'soldvehicles', 'VEHICLES FENCED', S_STORY, 200000, 2, ('lifetimemoneyearned', 'soldvehicles', ST), 'a', 'fencing', unit='dollars'),
    _l('kenton', 'soldkentontreasures', 'KENTON SETS COMPLETED', S_EXPLORE, 5, 1),
    _l('cardsets', 'soldsportscards', 'COLLECTIBLE CARD SETS FOUND', S_EXPLORE, 15, 1),
    _l('waink', 'wainklocations', 'WAiNK LOCATIONS SCANNED', S_EXPLORE, 100, 1),
    _l('underwater', 0x3c1ff692, 'UNDERWATER DISCOVERIES FOUND', S_EXPLORE, 33, 1),
    _l('magazines', 'booksandmagazines', 'MAGAZINES, BOOKS & COMICS FOUND', S_EXPLORE, 30, 1),
    _l('meditation', 'uniquemeditations', 'MEDITATION SPOTS COMPLETED', S_EXPLORE, 15, 1, ('uniquemeditations', 0, ST), 'a', 'activities'),
    _l('flamingos_or_playlists_1', 0x66d7b9dd, 'COCAINE FLAMINGOS DESTROYED or UNIQUE PLAYLISTS COMPLETED', S_EXPLORE, None, 1),
    _l('flamingos_or_playlists_2', 0x69ed6abb, 'COCAINE FLAMINGOS DESTROYED or UNIQUE PLAYLISTS COMPLETED', S_EXPLORE, None, 1),
    _l('styles', 'styles', 'DISCOVERED STYLES', S_EXPLORE, 70, 1),
    _l('races', 'uniqueraceswon', 'UNIQUE RACES WON', S_EXPLORE, 30, 1, ('uniqueraceswon', 0, ST), 'b'),
    _l('racechallenges', 'racechallenges', 'RACE CHALLENGE GOLD MEDALS', S_EXPLORE, 10, 1, ('numgoldmedals', 'racechallenges', ST), 'b'),
    _l('shootingranges', 'shootingrangegoldmedals', 'SHOOTING RANGE GOLD MEDALS', S_EXPLORE, 42, 1, ('shootingrangegoldmedals', 0, ST), 'b'),
    _l('videogames', 'arcadegameany', 'VIDEO GAMES PLAYED', S_EXPLORE, 4, 1, (0x40af8eca, 0, 'arcadegameany'), 'b'),
    _l('pool', 'pool', 'POOL OPPONENTS DEFEATED', S_EXPLORE, 5, 1, ('opponentsdefeated', 'pool', ST), 'b'),
    _l('minigolf', 'golfcoursescompleted', 'MINI GOLF LOCATIONS PLAYED', S_EXPLORE, 2, 1, ('golfcoursescompleted', 0, ST), 'b'),
    _l('hoops', 'basketballhoopalllocations', 'BASKETBALL HOOPS', S_EXPLORE, 90, 1, ('hoopscored', 'basketballhoopalllocations', ST), 'b', 'hoops'),
    _l('drones', 'droneracesroutescompleted', 'DRONE TIME TRIALS COMPLETED', S_EXPLORE, 42, 1, ('droneracesroutescompleted', 0, ST), 'b'),
    _l('stunts', 'totalstunts', 'STUNTS COMPLETED', S_EXPLORE, 300, 1, ('uniquestuntscompleted', 'totalstunts', ST), 'done', 'savedit.stunt_edits'),
    _l('challenges', 'challengescompleted', 'CHALLENGES COMPLETED', S_EXPLORE, 70, 1, ('challengescompleted', 0, ST), 'done', 'challenges'),
    _l('bret', 0xa49f352b, "BRET'S TARGET DECKS", S_EXPLORE, 15, 1, (0xa49f352b, 'cs_bret_vogel', ST)),
    _l('vehicles', 'vehiclesdiscovered', 'BASE MODEL VEHICLES', S_DISCOVERY, 200, 1, ('studied', 0x2b12592f, ST), 'done', 'compendium'),
    _l('weapons', 'weaponsdiscovered', 'STANDARD ISSUE WEAPONS', S_DISCOVERY, 50, 1, ('studied', 0x8dc8c123, ST), 'done', 'compendium'),
    _l('animals', 'animalsdiscovered', 'ANIMALS', S_DISCOVERY, 100, 1, ('studied', 'animals', ST), 'done', 'compendium'),
)
BY_KEY = {ln['key']: ln for ln in LINES}
WEIGHTS = {ln['key']: ln['weight'] for ln in LINES}
OPTIONAL_FACTOR = fl.f32(0.99)        # optional tasks: percentage = count * 0.99 (see docstring)


def percent_for(key, count):
    """The cached percentage the game keeps for a line with the given counter value."""
    ln = BY_KEY[key]
    if key == 'optionaltasks':
        return min(100.0, fl.f32(count * OPTIONAL_FACTOR))
    return fl.pct32(count, ln['of'])


def overall_of(pcts):
    """The overall figure from {line key: cached percentage}, as the game computes it (float32, screen order)."""
    acc = 0.0
    for ln in LINES:
        acc = fl.f32(acc + fl.f32(fl.f32(ln['weight'] / 100.0) * fl.f32(pcts.get(ln['key']) or 0.0)))
    return acc


def percents(st):
    """{line key: cached percentage} from a featurelib.Stats (pending changes included)."""
    return {ln['key']: st.value(TP, ln['qual'], default=0.0) for ln in LINES}


def overall(st):
    return overall_of(percents(st))


def refresh_overall(st, label='100% completion (overall figure)'):
    """Queue the recomputed overall figure in st. Returns (old, new) or None when the row is missing."""
    old = st.value(*OVERALL)
    if old is None:
        return None
    new = overall(st)
    st.set(OVERALL[0], OVERALL[1], new, label)
    return old, new


def _counter(st, ln):
    if not ln['counter']:
        return None
    base, qual, owner = ln['counter']
    return st.value(base, qual, owner)


def read(b):
    s = fl.Save(b)
    st = fl.Stats(s.text(fl.STATS))
    lines = []
    for ln in LINES:
        pct = st.value(TP, ln['qual'])
        cnt = _counter(st, ln)
        if cnt is not None and not isinstance(cnt, bool):
            value, source = cnt, 'counter'
        elif pct is not None and ln['of']:
            value, source = int(round(pct * ln['of'] / 100.0)), 'percent'
        else:
            value, source = pct, 'percent'
        consistent = None
        if source == 'counter' and pct is not None and ln['of']:
            exp = percent_for(ln['key'], cnt)
            consistent = abs(exp - pct) <= max(2e-6, abs(pct) * 2e-7)
        base, qual, owner = ln['counter'] or (None, None, None)
        shown = min(value, ln['of']) if source == 'counter' and ln['of'] else value       # the screen caps (54 weapons show 50 / 50)
        lines.append({'key': ln['key'], 'label': ln['label'], 'section': ln['section'], 'value': value, 'shown': shown, 'of': ln['of'],
                      'unit': ln['unit'], 'percent': pct, 'weight': ln['weight'], 'source': source,
                      'percentRow': 'totalprogressmade.%s/story000' % (ln['qual'] if isinstance(ln['qual'], str) else fl.hexid(ln['qual'])),
                      'counterRow': None if base is None else '%s.%s/%s' % (base if isinstance(base, str) else fl.hexid(base),
                                                                              (qual if isinstance(qual, str) else fl.hexid(qual)) if qual else '-', owner),
                      'counterMatchesPercent': consistent, 'grade': ln['grade'], 'module': ln['module'],
                      'done': bool(pct is not None and pct >= 100.0)})
    stored = st.value(*OVERALL)
    computed = overall(st)
    return {'feature': FEATURE, 'lines': lines,
            'overall': {'label': '100% COMPLETION', 'stored': stored, 'computed': computed,
                        'consistent': stored is not None and abs(stored - computed) <= 2e-6},
            'complete': sum(1 for x in lines if x['done']), 'of': len(lines),
            'possible': [x['key'] for x in lines if x['grade'] == 'a' and not x['done']],
            'risk': 'low',
            'notes': ['The overall figure is a weighted sum of the cached line percentages (story 50%, optional tasks 6%, gangs 3%, '
                      'robberies, fencing and vaults 2% each, the rest 1% each); the game recomputes it when it saves.',
                      'Grades: a = a module completes it, b = possible but risky, c = not possible from the save, done = existing module.',
                      'Two percentages (66d7b9dd, 69ed6abb) belong to COCAINE FLAMINGOS and UNIQUE PLAYLISTS; which is which is unknown.']}


def apply(b, choice=None):
    """choice: {'overall': 'recompute'} (the default) -> (new bytes, log). Unchanged bytes when already in step."""
    choice = choice or {'overall': 'recompute'}
    if choice.get('overall', 'recompute') != 'recompute':
        raise fl.FeatureError('bad_request')
    s = fl.Save(b)
    st = fl.Stats(s.text(fl.STATS))
    if refresh_overall(st) is None:
        raise fl.FeatureError('layout_changed')
    txt, log = st.apply()
    if not log:
        return b, []
    s.set_text(fl.STATS, txt)
    return s.build(), log
