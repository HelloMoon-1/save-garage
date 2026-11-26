# Save Garage - Copyright (C) 2026 NotHGM - GNU GPL v3 with the additional terms in NOTICE; see LICENSE.
"""Complete challenges (Save Garage feature module).

THE 212 SAVED CHALLENGES (section 3000010d Challenges: codeVersion + savedChallengeSets[11])
  * 8 sets x 10 = the 80 challenges of the CHALLENGES menu, in menu order (category order is alphabetical, as on
    screen): f5d004cf COMBAT, 073d2400 CRIMINAL, 8d42de3f EXPLORATION, b246908b FITNESS, 10ee1f26 SHOPPING,
    c7cd04f0 SPORTS, afab26e8 SURVIVAL, fa3d2fd7 VEHICLE. Each has a stats counter challengescompleted.<set id>.
    Evidence: the first challenge of every category matches the screenshots' done/not-done state (Speed Kills done,
    Mugging not, ...), FITNESS #1 'Gym Member' completed exactly when the first gym membership was bought (A0->A1),
    and the linked progress stats fit the categories (holdups -> CRIMINAL, vehicle mods -> SHOPPING, a hoop row ->
    SPORTS, fish and animals -> SURVIVAL, wheelies and top speed -> VEHICLE).
  * 348d4be2 (54): profile-wide awards. A fresh playthrough (B7as_a) starts with exactly the 23 completions of the
    other playthrough, so these follow the console profile (very likely the trophy mirror). Not edited.
  * e7c89bfd (16): per-save goals with per-character progress (swim/run distances since a baseline). Not edited.
  * d6d53427 (62): the cheat unlock trackers, one per cheat ('Spawns a Bravado Banshee. To unlock: Complete all combat
    challenges.' and so on: 5-of-10 and all-10 per category, one for all challenges, plus others linked to stunt,
    money and collection stats). Completed only on request, by apply_cheats (see CHEATS below); see also MIRRORS.

WHAT IT CHANGES
  For each chosen menu challenge that is not complete (section 3000010d):
    * isComplete false -> true;
    * pSaveParam -> {"$type":"0x209f39e2"} (the empty parameter). In all 3,240 challenge records of the 20 saves
      every complete challenge has exactly this parameter, and in every completion seen the game replaced the
      progress parameter with it.
  Stats (0635cbd9, owner story000):
    * challengescompleted.<set> += completed in that set; challengescompleted (no qualifier) += total completed.
      In every game save the set counters equal the completed records and the total equals their sum.
    * totalprogressmade.challengescompleted = float32(total / 70) * 100, capped at 100 ('CHALLENGES COMPLETED
      x / 70' on the 100% checklist; 70 of the 80 are needed).
  MIRRORS: any incomplete tracker whose (sub-)parameter points at challengescompleted.<set or total>/story000 and
  whose score equals the old counter gets the new counter as its score (216 of 216 such scores in the saves equal
  the counter). The trackers themselves are not completed.
  Counters change by the number completed rather than being recomputed, so values edited earlier are kept (the PS5
  kept an edited total of 1000 as-is).

NOT CHANGED: the progress stats a challenge watched (kills, mods, distances...), challengecompletedbits (mission
challenges), the three non-menu sets (the cheat trackers only by apply_cheats, on their own), rewards, and the overall
100% figure (its weights can't be derived).

RISK: medium-high. Completion flags and counters are exactly what the game writes, but the category rewards (vehicle
spawns) are granted by the game's own completion event and may not unlock; the game might also re-check a tracker
only when its stat changes again.

CHEATS (read_cheats, apply_cheats: the Completion tab's cheat list)
  GTA VI's cheats are rewards. The game's text has 62, each '<what it does>. To unlock: <how>.' (65 texts: three
  give the distance in feet and in metres). Set d6d53427 holds one tracker per cheat, and its pSaveParam follows the
  stat the condition counts. 39 trackers are matched to their cheat:
    * 23 by the stat they watch (CHEATS): litonfire.enemy (burn 100 enemies), killsorknockouts.melee, kills.runover,
      numworkoutscompleted, stuntscompleted.stuntjumps, drawbridgejump, survivedfreefalls, totalcaught.fish,
      totalmeditations, robbed.shop/withpartner, stolen.copveh, lifetimemoneyspent.alcohol, lifetimemoneyearned
      .soldfence and .soldvehicles, successfulhits.allgangs/withpartner, numpartneractivities, playing time holding
      hands and with the partner, headshots.enemy, evadedwantedlevel.level3 and explosivedamagehits.enemy. Where two
      cheats count the same stat, the game completed the one with the lower target as the stat passed it:
      headshots.enemy 73 -> 104 (100), soldfence $194,005 -> $276,465 ($250,000), evadedwantedlevel.level3 17 -> 25
      (25 times, so the other is 50) and explosivedamagehits.enemy 17 -> 21 (20 enemies, so the other is 100).
    * 1 by a sum: 2185857e keeps exploded.aircraft + landcraft + watercraft in every save ('Blow up 100 vehicles').
    * 15 by the menu challenge counters: 'Complete all challenges' follows all eight, and each category but sports has
      two trackers on its challengescompleted counter, one for 5 challenges and one for all 10. No category has
      reached 5 in any save, so which of the two is which can't be told: they are completed together (CHEAT_PAIRS).
  The other 23 trackers held no progress in any save (the sports pair among them: no sports challenge was ever done),
  so which is which can't be told either. Together they are the 23 cheats left (CHEATS_UNMATCHED), completed only all
  at once. Cheat names are the game's own where its text has one that plainly matches; the others go by what they do.
  Completing a tracker writes what the game writes when a condition is met: isComplete true and the empty parameter,
  nothing else. No counter or 100% line counts these trackers (challengescompleted equals the menu challenges done in
  every save), so the checklist is unchanged. Whether the cheat then shows in the game's Progress menu, or also needs
  its unlock-catalog byte, isn't known. The profile-wide awards, the goals and the unlock catalogs are never changed.
  Using a cheat in the game turns off trophies and saving for that session (the game's own warning).
  REFUSED: cheats_layout (the set isn't the 62 known trackers, or a record has keys other than the game writes, or a
  parameter that isn't an object), not_editable (a record of another set), unknown_challenge, bad_request,
  verify_failed. RISK: experimental, not tested on a PS5.
"""
import copy
import json
import re

import featurelib as fl

FEATURE = 'challenges'
SEC = 0x3000010d
FOR_100 = 70
TOTAL = 80
EMPTY_PARAM = b'{"$type":"0x209f39e2"}'
K_SETS, K_SETID, K_LIST = fl.key('savedChallengeSets'), fl.key('challengeSetId'), fl.key('savedChallenges')
K_PARAM, K_ID, K_DONE = fl.key('pSaveParam'), fl.key('challengeId'), fl.key('isComplete')
K_SCORE, K_SRC, K_SUB = fl.key('score'), fl.key('sourceId'), fl.key('saveParams')
K_BASE, K_ITEM, K_SCOPE = fl.key('BaseId'), fl.key('ItemId'), fl.key('Scope')
B_COUNTER = fl.joaat('challengescompleted')
STORY = fl.joaat('story000')

CATEGORIES = (
    (0xf5d004cf, 'combat', 'Combat'), (0x073d2400, 'criminal', 'Criminal'), (0x8d42de3f, 'exploration', 'Exploration'),
    (0xb246908b, 'fitness', 'Fitness'), (0x10ee1f26, 'shopping', 'Shopping'), (0xc7cd04f0, 'sports', 'Sports'),
    (0xafab26e8, 'survival', 'Survival'), (0xfa3d2fd7, 'vehicle', 'Vehicle'),
)
CATEGORY_OF = {sid: (k, label) for sid, k, label in CATEGORIES}
OTHER_SETS = {
    0x348d4be2: ('profile_awards', 'Profile-wide awards (carried into new playthroughs; likely the trophy mirror)'),
    0xe7c89bfd: ('goals', 'Per-save goals with per-character progress'),
    0xd6d53427: ('reward_trackers', 'Per-save cheat unlock trackers (completed on their own: read_cheats, apply_cheats)'),
}
# First challenge of each category, from the stats screens (title, description).
KNOWN = {
    0x624b005d: ('Speed Kills', 'Kill 3 enemies in under 30 seconds.'),
    0x9cc2329b: ('Mugging', 'Rob 5 pedestrians.'),
    0x8244cf1e: ('WAiNK Locations', 'Scan any 4 landmarks, curiosities, or sculptures with WAiNK.'),
    0xd5dae49d: ('Gym Member', 'Become a member at any gym.'),
    0xc58c59c7: ('Vehicle Modder', 'Make 5 modifications to your vehicle using a mod shop.'),
    0xa3649639: ('Basketball Rookie', 'Score a basketball shot at 3 different hoops in a day.'),
    0x2621d002: ('Alligator Kills', 'Kill 3 wild alligators.'),
    0x450d7231: ('Vehicle Discovery', 'Examine or discover 6 different vehicles.'),
}
REWARDS = {   # game text: 'Spawns a <vehicle>. To unlock: Complete 5 / all <category> challenges.'
    'combat': ('Speeder 700 GT', 'Bravado Banshee'), 'criminal': ('Maibatsu Sanchez', 'Western Zombie Bobber'),
    'exploration': ('Nagasaki Sea Sparrow', 'Nagasaki Carbon RS'), 'fitness': ('Tuff BMX', "'65 Vapid Dominator"),
    'shopping': ('Maibatsu Boomazoom', 'Truffade Thrax'), 'sports': ('Vapid Stanier G2 Taxi', 'Brimstone Golfer'),
    'survival': ('Airboat 09', 'Hauners Rhino Tank'), 'vehicle': ('Lapwing Mallard', 'Progen Emerus'),
    'all': ('Hauners P-996 LAZER',),
}

# ---------------------------------------------------------------- cheats (set d6d53427; see CHEATS in the docstring)
CHEAT_SET = 0xd6d53427
CHEAT_RECORDS = 62
CHEAT_RECORD_KEYS = {'$type', K_ID, K_DONE, K_PARAM}
# tracker -> (the game's name for the cheat, or None where it isn't known; what it does; how to unlock it), in the
# game's words (metric where it gives both). In the order the Completion tab lists them.
CHEATS = {
    0xa976680f: (None, 'Spawns a Hauners P-996 LAZER.', 'Complete all challenges.'),
    0x0c7d4ae2: ('Super Jump', 'Increases the height of your jump by 10x with no fall damage.',
                 'Jump a vehicle 15 meters or more over a drawbridge 50 times.'),
    0x91a70a6b: ('No Fall Damage', 'You are immune to fall damage.', 'Survive a freefall from 12 meters 20 times.'),
    0x1c461386: ('Unlimited Focus', 'Focus never runs out.', 'Get 100 headshot kills on enemies.'),
    0x33ac72c7: ('Body Armor', 'Adds body armor to your loadout.', 'Complete 100 workouts.'),
    0x731194da: ('Drunk', 'Instantly makes you and your partner drunk.', 'Spend $2,500 on alcohol.'),
    0x93c167e8: ('Fast Cash', 'Instantly gives you $250,000.', 'Make $250,000 from fenced goods.'),
    0xb47e7a74: ('Incendiary Ammo', 'All ammo is incendiary.', 'Burn 100 enemies with fire damage.'),
    0x4d256389: ('Explosive Shotgun', 'Adds a Mason & Keen Shortstraw to your loadout that fires explosive shells.',
                 'Hit 100 enemies with explosive damage.'),
    0x2185857e: (None, 'Adds a Hauners H-AT to your loadout.', 'Blow up 100 vehicles.'),
    0x7251a43b: ('Attack Force', 'Bullets and melee attacks launch targets on impact.', 'Kill or knock out 100 enemies with melee attacks.'),
    0x9b29a915: ('Vehicle Force', 'Vehicle collisions launch targets.', 'Kill 25 enemies with a vehicle.'),
    0x357874b7: ('Exploding Balls', 'Sports balls explode on impact.', 'Hit 20 enemies with explosive damage.'),
    0x25f5ca4f: ('Unlimited Nitrous', 'Nitrous and fuel never runs out on vehicles.', 'Complete 50 stunt jumps.'),
    0xeb403ceb: ('Raise Heat Level', 'Raises your level of heat across the map.', 'Lose a 3-star wanted level 25 times.'),
    0x6ea8045f: ('Raise Wanted Level', 'Raises your wanted level across the map.', 'Lose a 3-star wanted level 50 times.'),
    0x95f34935: ('Golden Hour', 'Applies a golden filter with a widescreen aspect ratio.', 'Spend 4 hours holding hands.'),
    0x38d30eda: (None, 'Applies a vivid filter with a narrow aspect ratio.', 'Spend 8 hours with your partner.'),
    0xb0f97f25: ('Pinhole', 'Applies a pinhole camera filter.', 'Clear 25 gang operations with your partner.'),
    0x6683ea3b: ('Videotape', 'Applies a videotape-style filter.', 'Complete 50 activities with your partner.'),
    0x4664be1b: (None, 'Applies a color CRT TV filter.', 'Rob 50 stores with your partner.'),
    0x303291b7: ('Fisheye', 'Applies a fisheye filter.', 'Catch 100 fish.'),
    0x5ae6671e: (None, 'Applies a motion blur and accelerates cloud movements.', 'Complete 50 meditations.'),
    0x0bfc4957: (None, 'Turns the world red and orange with a heat haze.', 'Steal 100 cop vehicles.'),
    0x5428c585: (None, 'Flips the world upside down and turns it black.', 'Make $500,000 selling vehicles.'),
}
# A menu category's two trackers (5 challenges, all 10) and their cheats; which tracker is which isn't known.
CHEAT_PAIRS = {
    'combat': ((0xd40c07aa, 0xc2737d73), (('Spawns a Speeder 700 GT.', 'Complete 5 combat challenges.'),
                                          ('Spawns a Bravado Banshee.', 'Complete all combat challenges.'))),
    'criminal': ((0xd67c8051, 0x9896d0e2), (('Spawns a Maibatsu Sanchez.', 'Complete 5 criminal challenges.'),
                                            ('Spawns a Western Zombie Bobber.', 'Complete all criminal challenges.'))),
    'exploration': ((0x73049a44, 0x6ca2e622), (('Spawns a Nagasaki Sea Sparrow.', 'Complete 5 exploration challenges.'),
                                               ('Spawns a Nagasaki Carbon RS.', 'Complete all exploration challenges.'))),
    'fitness': ((0x69d73f42, 0x95e3faca), (('Spawns a Tuff BMX.', 'Complete 5 fitness challenges.'),
                                           ("Spawns a '65 Vapid Dominator.", 'Complete all fitness challenges.'))),
    'shopping': ((0xfb6c7959, 0xe9902a97), (('Spawns a Maibatsu Boomazoom.', 'Complete 5 shopping challenges.'),
                                            ('Spawns a Truffade Thrax.', 'Complete all shopping challenges.'))),
    'survival': ((0xf01756a3, 0xfbd6b7fe), (('Spawns an Airboat 09.', 'Complete 5 survival challenges.'),
                                            ('Spawns a Hauners Rhino Tank.', 'Complete all survival challenges.'))),
    'vehicle': ((0x81b4c218, 0x71d02e27), (('Spawns a Lapwing Mallard.', 'Complete 5 vehicle challenges.'),
                                           ('Spawns a Progen Emerus.', 'Complete all vehicle challenges.'))),
}
# The 23 trackers that held no progress in any save, and the 23 cheats they are between them.
CHEATS_UNMATCHED_IDS = (
    0x45114a22, 0xab40ebc9, 0x69ea7515, 0xe7fb8d9d, 0x03ace5ed, 0xce2b3393, 0xcc6427bc, 0x869e9aa8, 0x5d5dc42e, 0xccda9645,
    0x3ad12871, 0xe29bc6d2, 0x9a79a2b4, 0x676be3fa, 0xd7c77713, 0x6ae016a0, 0xc77c2c46, 0x9f3bdbaa, 0x8194a05c, 0x7f9c9c6c,
    0x1bb8d4be, 0x54a75aa0, 0xfe29adb2)
CHEATS_UNMATCHED = (
    (None, 'Spawns a Vapid Stanier G2 Taxi.', 'Complete 5 sports challenges.'),
    (None, 'Spawns a Brimstone Golfer.', 'Complete all sports challenges.'),
    (None, 'Spawns an Interstate Ambulance.', 'Discover the Interstate Ambulance in the Progress menu.'),
    (None, 'Spawns an MTL Pumper.', 'Discover the MTL Pumper in the Progress menu.'),
    (None, 'Spawns an HVY Bulldozer.', 'Discover the HVY Bulldozer in the Progress menu.'),
    (None, 'Spawns an Inflatable Flamingo.', 'Destroy 50 cocaine flamingos.'),
    ('Parachute', 'Adds a parachute to your loadout.', 'Complete 50 skydives or base jumps from 91.5 meters or higher.'),
    ('All Explosive Weapons', 'Adds all explosive weapons to your loadout with full ammo.', 'Throw 100 grenades.'),
    ('Exploding Bottles', 'All bottles explode when damaged.', 'Throw 100 molotovs.'),
    ('Max Ammo', 'Fills all ammo to maximum.', 'Win 25 bronze medals or higher at shooting ranges.'),
    ('Infinite Ammo', 'Ammo never runs out.', 'Win 25 silver medals or higher at shooting ranges.'),
    ('No Reload', 'Ammo never runs out with no need to reload.', 'Win 25 gold medals at shooting ranges.'),
    ('Repair Vehicle', 'Fully repairs your current vehicle.',
     'Get 1st place in 10 races at Gellhorn Raceway, Thrillbilly Mud Club, and Boone Speedway.'),
    ('Move Time Forward', 'Moves the time of day forward.', 'Find 10 collectible watches.'),
    ('Pause Time of Day', 'Pauses the current time of day.', 'Find 20 collectible watches.'),
    ('Cycle Weather', 'Adjusts the weather conditions.', 'Reveal the entire map.'),
    (None, 'Applies a pixelated filter.', 'Make $250,000 selling collectibles.'),
    (None, 'Applies neon highlights to the world.', 'Discover all 16 Girlypop Vehicles.'),
    (None, 'Applies a black & white CRT TV filter.', 'Discover the Ridgway.'),
    (None, 'Applies a blurred, distorted filter.', 'Survive 6 minutes with a 6-star wanted level.'),
    (None, 'Turns the world purple and yellow with sparkling highlights.', 'Find all 24 collectible cards for the Vice City Flamingos.'),
    (None, 'Turns the world white with sparkling highlights.', 'Scan all space debris with WAiNK.'),
    (None, 'Fills the world with murky smoke.', "Discover Martha's Vamos in the Progress menu."),
)
CHEAT_IDS = frozenset(CHEATS) | {i for ids, _ in CHEAT_PAIRS.values() for i in ids} | frozenset(CHEATS_UNMATCHED_IDS)


def _hexval(t, s, e):
    """Value of {"$data":"0x...."} at t[s:e]."""
    for k, a, z in fl.members(t, s):
        if k == '$data':
            return int(t[a + 1:z - 1], 16) & fl.M32
    raise fl.FeatureError('layout_changed')


def _scores(t, ps, pe):
    """Score spans inside a pSaveParam object: [(score_start, score_end, (base, item, scope))]."""
    out = []
    if t[ps] != ord('{'):
        return out
    mem = {k: (a, z) for k, a, z in fl.members(t, ps)}
    if K_SUB in mem:
        for a, z in fl.elements(t, mem[K_SUB][0]):
            out += _scores(t, a, z)
    if K_SCORE in mem and K_SRC in mem and t[mem[K_SRC][0]] == ord('{'):
        src = {k: (a, z) for k, a, z in fl.members(t, mem[K_SRC][0])}
        if K_BASE in src:
            key = tuple(_hexval(t, *src[k]) for k in (K_BASE, K_ITEM, K_SCOPE))
            out.append((mem[K_SCORE][0], mem[K_SCORE][1], key))
    return out


def _records(t):
    """[{set, index, id, done, rec, param, done_span}] in text order."""
    s, _ = fl.walk(t, fl.CODE, fl.key(SEC), K_SETS)
    out = []
    for a, z in fl.elements(t, s):
        mem = {k: (x, y) for k, x, y in fl.members(t, a)}
        sid = _hexval(t, *mem[K_SETID])
        for i, (ra, rz) in enumerate(fl.elements(t, mem[K_LIST][0])):
            rm = {k: (x, y) for k, x, y in fl.members(t, ra)}
            done = t[rm[K_DONE][0]:rm[K_DONE][1]]
            if done not in (b'true', b'false'):
                raise fl.FeatureError('layout_changed')
            out.append({'set': sid, 'index': i, 'id': _hexval(t, *rm[K_ID]), 'done': done == b'true', 'rec': (ra, rz),
                        'param': rm[K_PARAM], 'done_span': rm[K_DONE]})
    return out


def _label(r):
    if r['id'] in KNOWN:
        return KNOWN[r['id']][0]
    cat = CATEGORY_OF.get(r['set'])
    return '%s challenge %d' % (cat[1], r['index'] + 1) if cat else 'Challenge %08x' % r['id']


def read(b):
    s = fl.Save(b)
    t = s.text(SEC)
    st = fl.Stats(s.text(fl.STATS))
    recs = _records(t)
    cats = []
    for sid, k, label in CATEGORIES:
        rs = [r for r in recs if r['set'] == sid]
        items = []
        for r in rs:
            sc = _scores(t, *r['param'])
            prog = None
            if sc and not r['done']:
                a, z, (bb, ii, oo) = sc[0]
                prog = {'score': t[a:z].decode(), 'stat': '%08x/%08x/%08x' % (bb, ii, oo)}
            items.append({'id': fl.hexid(r['id']), 'n': r['index'] + 1, 'title': _label(r),
                          'description': KNOWN.get(r['id'], (None, None))[1], 'done': r['done'], 'progress': prog})
        done = sum(1 for r in rs if r['done'])
        counter = st.value(B_COUNTER, sid)
        cats.append({'id': fl.hexid(sid), 'key': k, 'label': label, 'done': done, 'of': len(rs), 'counter': counter,
                     'consistent': counter == done, 'rewards': REWARDS.get(k), 'challenges': items})
    total = st.value(B_COUNTER, 0)
    other = []
    for sid, (k, label) in OTHER_SETS.items():
        rs = [r for r in recs if r['set'] == sid]
        other.append({'id': fl.hexid(sid), 'key': k, 'label': label, 'done': sum(1 for r in rs if r['done']), 'of': len(rs),
                      'editable': sid == CHEAT_SET})
    return {'feature': FEATURE, 'categories': cats,
            'done': sum(c['done'] for c in cats), 'of': TOTAL,
            'possible': [i['id'] for c in cats for i in c['challenges'] if not i['done']],
            'counter': {'value': total, 'consistent': total == sum(c['counter'] or 0 for c in cats)},
            'checklist': {'label': 'CHALLENGES COMPLETED', 'value': total, 'of': FOR_100},
            'percent': st.value('totalprogressmade', 'challengescompleted'),
            'otherSets': other, 'records': len(recs), 'risk': 'medium-high',
            'notes': ['Completes menu challenges the way the game records them and keeps the counters and the 100% row in step.',
                      'Category rewards (vehicle spawns) are granted by the game when it completes a challenge itself; they may not unlock.',
                      'Only the eight menu categories are completed here; the cheat trackers are completed on their own (apply_cheats), and the profile awards and goals are read-only.']}


def apply(b, choice):
    """choice: {'challenges': [hex ids]} or {'categories': ['combat', ...] | 'all'} -> (new bytes, log)."""
    choice = choice or {}
    s = fl.Save(b)
    t = s.text(SEC)
    recs = _records(t)
    menu = [r for r in recs if r['set'] in CATEGORY_OF]
    if 'challenges' in choice:
        want = {fl.h(x if isinstance(x, int) else ('0x' + x if not x.startswith('0x') else x)) for x in choice['challenges']}
        known_ids = {r['id'] for r in recs}
        if want - known_ids:
            raise fl.FeatureError('unknown_challenge')
        if any(r['id'] in want and r['set'] not in CATEGORY_OF for r in recs):
            raise fl.FeatureError('not_editable')
        targets = [r for r in menu if r['id'] in want]
    else:
        cats = choice.get('categories', 'all')
        keys = {k for _, k, _ in CATEGORIES} if cats == 'all' else set(cats)
        if keys - {k for _, k, _ in CATEGORIES}:
            raise fl.FeatureError('unknown_category')
        targets = [r for r in menu if CATEGORY_OF[r['set']][0] in keys]
    targets = [r for r in targets if not r['done']]
    if not targets:
        return b, []
    st = fl.Stats(s.text(fl.STATS))
    per_set = {}
    for r in targets:
        per_set[r['set']] = per_set.get(r['set'], 0) + 1
    new_counter, log = {}, []
    for sid, n in per_set.items():
        cur = st.value(B_COUNTER, sid)
        if cur is None:
            raise fl.FeatureError('layout_changed')
        new_counter[sid] = (cur, cur + n)
        st.set(B_COUNTER, sid, cur + n, 'Challenges completed: ' + CATEGORY_OF[sid][1])
    cur = st.value(B_COUNTER, 0)
    new_counter[0] = (cur, cur + len(targets))
    st.set(B_COUNTER, 0, cur + len(targets), 'Challenges completed')
    st.set('totalprogressmade', 'challengescompleted', fl.pct32(cur + len(targets), FOR_100), 'Challenges, part of 100% completion')
    # text edits: completed records, then mirrored tracker scores; applied from the end of the text backwards
    edits = []
    done_ids = {r['id'] for r in targets}
    for r in targets:
        edits.append((r['done_span'][0], r['done_span'][1], b'true'))
        edits.append((r['param'][0], r['param'][1], EMPTY_PARAM))
        log.append({'what': 'challenge', 'id': fl.hexid(r['id']), 'category': CATEGORY_OF[r['set']][0], 'n': r['index'] + 1, 'title': _label(r)})
    for r in recs:
        if r['done'] or r['id'] in done_ids:
            continue
        for a, z, (bb, ii, oo) in _scores(t, *r['param']):
            if bb != B_COUNTER or oo != STORY or ii not in new_counter:
                continue
            old, new = new_counter[ii]
            tok = t[a:z]
            if tok != b'%d' % old:
                log.append({'what': 'tracker_kept', 'id': fl.hexid(r['id']), 'score': tok.decode(), 'counter': old})
                continue
            edits.append((a, z, b'%d' % new))
            log.append({'what': 'tracker_score', 'id': fl.hexid(r['id']), 'set': fl.hexid(r['set']), 'from': old, 'to': new})
    edits.sort(key=lambda x: -x[0])
    last = len(t) + 1
    for a, z, new in edits:
        if z > last:
            raise fl.FeatureError('layout_changed')
        t = t[:a] + new + t[z:]
        last = a
    s.set_text(SEC, t)
    txt, slog = st.apply()
    s.set_text(fl.STATS, txt)
    return s.build(), log + slog


# ---------------------------------------------------------------- cheats
_HEX8 = re.compile(r'(?:0x)?([0-9a-fA-F]{8})')


def _cheat_records(t):
    """{tracker id: record} of the 62 cheat trackers, after checking the set; raises FeatureError('cheats_layout')."""
    try:
        recs = [r for r in _records(t) if r['set'] == CHEAT_SET]
    except (fl.FeatureError, KeyError, ValueError, IndexError):
        raise fl.FeatureError('cheats_layout')
    ids = {r['id'] for r in recs}
    if len(recs) != CHEAT_RECORDS or ids != CHEAT_IDS:
        raise fl.FeatureError('cheats_layout')
    for r in recs:
        if {k for k, _, _ in fl.members(t, r['rec'][0])} != CHEAT_RECORD_KEYS or t[r['param'][0]] != ord('{'):
            raise fl.FeatureError('cheats_layout')
    return {r['id']: r for r in recs}


def _cheat_entries():
    """[(key, kind, tracker ids, cheats)] in the order the Completion tab lists them: the category pairs, the trackers
    matched one by one, then the 23 that can only be completed together."""
    cheat = lambda n, e, u: {'name': n, 'effect': e, 'unlock': u}
    out = [(k, 'pair', ids, [cheat(None, e, u) for e, u in texts]) for k, (ids, texts) in CHEAT_PAIRS.items()]
    out += [(fl.hexid(i), 'single', (i,), [cheat(*c)]) for i, c in CHEATS.items()]
    out.append(('unmatched', 'unmatched', CHEATS_UNMATCHED_IDS, [cheat(*c) for c in CHEATS_UNMATCHED]))
    return out


def _cheat_of(i):
    """What a tracker unlocks, for the log: the cheat's name or effect, the category of a pair, or None."""
    if i in CHEATS:
        return CHEATS[i][0] or CHEATS[i][1]
    return next((k for k, (ids, _) in CHEAT_PAIRS.items() if i in ids), None)


def read_cheats(b):
    t = fl.Save(b).text(SEC)
    try:
        recs, problem = _cheat_records(t), None
    except fl.FeatureError as e:
        recs, problem = {}, str(e)
    entries = []
    if not problem:
        for key, kind, ids, cheats in _cheat_entries():
            entries.append({'key': key, 'kind': kind, 'ids': [fl.hexid(i) for i in ids], 'of': len(ids),
                            'done': sum(1 for i in ids if recs[i]['done']), 'cheats': cheats})
    return {'feature': 'cheats', 'set': fl.hexid(CHEAT_SET), 'records': len(recs), 'of': CHEAT_RECORDS,
            'done': sum(1 for r in recs.values() if r['done']), 'entries': entries, 'problem': problem,
            'matched': len(CHEATS) + 2 * len(CHEAT_PAIRS), 'risk': 'experimental'}


def apply_cheats(b, choice):
    """choice: {'trackers': [hex ids] | 'all'} -> (new bytes, log). Each chosen tracker that isn't complete gets
    isComplete true and the empty parameter; nothing else changes. Applying the result again changes nothing."""
    if not isinstance(choice, dict) or set(choice) != {'trackers'}:
        raise fl.FeatureError('bad_request')
    want = choice['trackers']
    s = fl.Save(b)
    t = s.text(SEC)
    recs = _cheat_records(t)
    if want == 'all':
        ids = set(CHEAT_IDS)
    else:
        if not isinstance(want, list) or not all(isinstance(x, str) for x in want):
            raise fl.FeatureError('bad_request')
        ids, others = set(), None
        for x in want:
            m = _HEX8.fullmatch(x)
            if not m:
                raise fl.FeatureError('bad_request')
            i = int(m.group(1), 16)
            if i not in CHEAT_IDS:
                others = others or {r['id'] for r in _records(t)}
                raise fl.FeatureError('not_editable' if i in others else 'unknown_challenge')
            ids.add(i)
    targets = sorted((recs[i] for i in ids if not recs[i]['done']), key=lambda r: r['rec'][0])
    if not targets:
        return b, []
    edits = []
    for r in targets:
        edits += [(r['done_span'][0], r['done_span'][1], b'true'), (r['param'][0], r['param'][1], EMPTY_PARAM)]
    old = t
    for a, z, new in sorted(edits, key=lambda x: -x[0]):          # from the end, so the earlier spans stay valid
        t = t[:a] + new + t[z:]
    # read back: the chosen trackers complete with the empty parameter, everything else exactly as it was
    expect = copy.deepcopy(fl.payload(old, SEC))
    done = {r['id'] for r in targets}
    for st in expect[K_SETS]:
        if int(st[K_SETID]['$data'], 16) == CHEAT_SET:
            for rec in st[K_LIST]:
                if int(rec[K_ID]['$data'], 16) in done:
                    rec[K_DONE] = True
                    rec[K_PARAM] = json.loads(EMPTY_PARAM)
    if fl.payload(t, SEC) != expect or {i for i, r in _cheat_records(t).items() if r['done']} != {i for i, r in recs.items() if r['done']} | done:
        raise fl.FeatureError('verify_failed')
    s.set_text(SEC, t)
    log = [{'what': 'cheat', 'id': fl.hexid(r['id']), 'label': 'Cheat tracker completed', 'cheat': _cheat_of(r['id'])} for r in targets]
    return s.build(), log
