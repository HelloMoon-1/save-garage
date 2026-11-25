"""Activity lines of the 100% checklist (Save Garage feature module): races, race challenges, shooting ranges, video
games, pool, mini golf, drone time trials and Bret's target decks. Hoops are in hoops.py, vehicles in
vehicles_compendium.py.

All rows are stats rows (section 0635cbd9). Owner story000 unless another owner is named. Names in <> are hashes not
cracked. 'pct' = featurelib.pct32(count, total) = the cached percentage totalprogressmade.<q>/story000, which the game
recomputes from the counter when it saves (A6b_mod -> A6c_as) and which the overall figure is built from
(checklist.overall_of). Every apply() ends with checklist.refresh_overall().

LINE BY LINE (value at 67.5% -> what the module writes)

VIDEO GAMES PLAYED 2/4 (videogames; verified)
  item rows   started.<game>/<game> (bool) for arcadegamesurvivor, arcadegametenebrae, arcadegamebangforyourbuck,
              arcadegametimejackersrewind; started/arcadegameany (bool) = any started.
  counter     <40af8eca>/arcadegameany (u8) = number of started games (2 in all 11 playthrough-A saves, 0 in B).
  percent     totalprogressmade.arcadegameany = pct(n, 4) (50.0 = 2/4).
  evidence    the counter equals the true started.<game> flags in every save; the aggregate owner arcadegameany
              mirrors the games (totalplayingtimems.arcadegameany = sum of the games' times, 605177 = 318860 + 286317
              at A0, 2027723 = 1741406 + 286317 at A5; A4 -> A5 completed.survivor -> <57e18f3a>.arcadegameany 0 -> 1
              is the games-completed count, not this line). The GAMES page showed 2 of 4 games, the two started.
  not touched completed.* and <57e18f3a> (games finished), play times, high scores, ScriptArcadeGames (8f773abc).

UNIQUE RACES WON 1/30 (races; group sizes from guides)
  item rows   raceswon.<race>, racesplayed.<race> (u32) for 41 race qualifiers (racescompleted/raceslost/cashwon per
              race exist but the game left them 0 even for the race it scored).
  groups      vcgroup (HIT 'N' RUN VC), thrillbillymudclubgroup, gellhornracewaygroup, hamletboonespeedwaygroup,
              ambrosiagroup, lcgroup: uniqueraceswon, uniqueracesplayed, raceswon, racesplayed, racescompleted,
              raceslost, cashwon, firstplacereached, uniqueracescompleted.
  counter     uniqueraceswon/story000 (u32; 'UNIQUE RACES WON', the screen showed 1 / 30).
  percent     totalprogressmade.uniqueraceswon = pct(n, 30) (3.333333 = 1/30).
  evidence    A0 -> A1, the only race data: c85c8052 played 5, won 1; ba1e9b50 and ff7f818a played 1 each. vcgroup:
              played 6, won 1, lost 5, completed 2, firstplacereached 1, cashwon 4900, uniqueplayed 2, uniquewon 1;
              mud club: played 1, completed 1, lost 1, uniqueplayed 1. So group played/won = the sums of the per-race
              rows (6 + 1 = 5 + 1 + 1), the story counter = the won race rows = vcgroup uniqueraceswon. The RACING page
              showed 'HIT 'N' RUN VC: UNIQUE RACES WON 1 / 9'.
  limits      Which group each race belongs to is not in the save: only c85c8052 is known to be VC (ba1e9b50/ff7f818a
              are VC and Mud Club in some order). So only 'all' is offered; group counters then go to the group
              sizes, which need no mapping. Sizes: VC 9 (stats screen); the other five from public guides (Mud Club 8,
              Gellhorn 11, Boone Speedway 2, Ambrosia 2, Animal Crackers 8 = lcgroup by elimination), 40 in all
              against 41 race rows, so one row is outside the guides' groups: the story counter becomes 41 (the won
              rows, the rule the one example shows) while the groups sum to 40. cashwon, raceslost and
              uniqueracescompleted are left alone (no prize table; uniqueracescompleted/story000 = 4 does not follow
              any other row).

RACE CHALLENGE GOLD MEDALS 0/10 (racechallenges; gold encoding inferred)
  item rows   highestmedal.<challenge> (u8) for 13 challenges: besttime (int64) on 10 of them, bestscore (u32) and
              highestjump (float) on 3 (hamletbackyardbmx, <5d16f293>, mudclubairtime). Cracked here:
              gellhornracewaydragstrip, hamletbackyardbmx, mountkalagadownhillmtb, mudclubdragstrip.
  counter     numgoldmedals.racechallenges (int32). percent totalprogressmade.racechallenges = pct(min(n, 10), 10).
  evidence    never played in these saves. Text: 'Race Challenge Gold Medals', 'Earn gold in every racing challenge
              except those at the Mud Club' (4 Mud Club challenges here, so 9 elsewhere: the checklist's 10 is 'any 10
              of 13', so the counter counts all 13), medals Bronze/Silver/Gold.
  writes      highestmedal = 3 (GOLD) where lower, counter += newly gold. Times and scores are left at 0.

SHOOTING RANGE GOLD MEDALS 0/42 (shootingranges; gold encoding and unlock counters inferred)
  courses     griffin<3point|hook|loop>range x beginner/intermediate/advanced, griffin<compound|maze|villa>range x
              intermediate/advanced/master, rodgers<alien|copsandrobbers|hunting|market|saloon|undead>range x all
              four tiers = 18 + 24 = 42 (owner = range, qualifier = tier). Each: highestmedal (u8), bestscore,
              recentscore, accuracy, hits, bullseyes, shots, timescompleted, timescancelled, unlocked (bool).
  counters    shootingrange{bronze,silver,gold,total}medals per range (12), per venue griffin/rodgers (no qualifier
              and per tier) and story000; unlocked per range/venue; challengesunlocked and uniquechallengescompleted
              per range/venue; shootingrangecoursesunlocked per venue ('RANGES UNLOCKED 0 / 6') and story000;
              shootingrangelocationsunlocked and shootingrangechallengesunlocked (story000).
  checklist   shootingrangegoldmedals/story000; percent totalprogressmade.shootingrangegoldmedals = pct(n, 42).
  evidence    never played. The Rodgers page showed 'MEDALS 0 / 72' = 24 courses x 3, and the rewards text says
              'Win 25 bronze medals or higher', 'silver medals or higher', 'gold medals': medals count cumulatively,
              so a course's highestmedal 0..3 = none/bronze/silver/gold and totalmedals = the sum of highestmedal.
  writes      every course highestmedal = 3 and unlocked; timescompleted >= 1; every medal counter moved by the
              change of its recount (bronze/silver/gold = courses at >= 1/2/3, total = sum of medals); unlock
              counters raised to their full values (courses, ranges, venues). Scores, accuracy, hits, shots, times
              are left at 0.

POOL OPPONENTS DEFEATED 0/5 (pool; per-venue flag meaning inferred)
  rows        <68ea5b9f>.pool<venue> (bool) and gameswon.pool<venue> (int32) at 7 venues (delights, kowaachobee,
              rustyanchor, skeetersbar, thethirstywolf, zoticos, <02ee1e5a>); <fcc85334> ('tablecompleted', weak) at
              17 tables (+poolflemingkey, poolfleamarket cracked here); gameswon/gameslost/gamesstarted/
              gameswithpartner.pool, <4a9631c8>.pool, <fc9aa40d>.pool.
  counter     opponentsdefeated.pool (int32; text 'Pool Opponents Defeated'); percent totalprogressmade.pool.
  evidence    never played (gamesstarted.pool = 1 since A0, nothing won or lost). Seven venues carry an opponent
              flag and a games-won row; five are needed (the same 'more items than needed' pattern as 18/15
              meditation spots, 100/90 hoops, 80/70 challenges).
  writes      <68ea5b9f> = true at all 7 venues; gameswon.<venue> += 1, gameswon.pool and gamesstarted.pool += the
              same, opponentsdefeated.pool += the same (7, shown capped 5 / 5).

MINI GOLF LOCATIONS PLAYED 0/2 (minigolf; meaning of coursecompleted inferred)
  rows        owners frontieradventuregolf and kinggatoradventuregolf (the two 'Adventure Golf' mini golf courses;
              dinogolf, leaflinksgolf, mounthailesgolf are golf challenges): coursecompleted (bool),
              gamescompleted.holes18/holes09 (holes09 = feaaaa45, cracked here), gameswon, gameslost,
              gameswithinpar, gameswithpartner, per-hole bestscore and holesinone; story000 gamescompleted and
              gamesstarted .holes18/.holes09 and <02076db6>.holes18/.holes09.
  counter     golfcoursescompleted (int32; text 'Mini Golf Locations Played'); percent
              totalprogressmade.golfcoursescompleted = pct(n, 2).
  writes      coursecompleted = true; for each newly completed course one 18-hole game: gamescompleted.holes18
              (course and story000) and gamesstarted.holes18 (story000) += 1; golfcoursescompleted += 1. Scores and
              the course rewards (Frontier and King Gator outfits) are not given.

DRONE TIME TRIALS COMPLETED 0/42 (drones; completionstate value inferred)
  rows        14 venue owners (ambrosia, balsero, buckskinswamp, capri, daltonisland, downtown, draperisland,
              hamlet, millport, moreausawmill, portgellhorn, vicebeach, waningsands, watsonbay): found (bool),
              routescompleted (u8), besttime; per route a/b/c: completionstate (u8), besttime (int64), attempts.
  counters    droneracesfound (u8; text 'Top Fun Drones ~1~ / 14'), droneracesroutescompleted (int32; 'Drone Time
              Trials Completed'); percent totalprogressmade.droneracesroutescompleted = pct(n, 42).
  evidence    never played. completionstate is the base the stunts use, where 1 = completed (10 game-written stunt
              completions, 3 = completed with its challenge).
  writes      found = true; completionstate = 1 where 0; attempts >= 1; routescompleted per venue and the two
              story counters += what was newly set. Best times are left at 0.

BRET'S TARGET DECKS 0/15 (bret; counter only)
  rows        <a49f352b>.cs_bret_vogel (per contact: the CONTACTS page 'TARGET DECKS COMPLETED 0 / 15') and
              <a49f352b> with no qualifier (story-wide); percent totalprogressmade.<a49f352b>; also
              huntinganimalssold / huntingcashcollected per species and .cs_bret_vogel (all 0).
  deck state  not located: nothing in any save was ever sold to Bret (all hunting-sale rows are 0) and no section
              holds a deck index or per-deck progress; joaat('bret_vogel') appears only in ScriptSocialMedia. The
              deck contents (15 decks x 3 animals) are only in the game text. A save before and after one completed
              deck would show where the game keeps it.
  writes      both counters (the story-wide one only where it equalled the per-contact one) = 15, percent 100.

LEVELS AND RISK
  choice['level'][line] = 'full' (the default) writes the rows above; 'counter' writes only the line counter and
  its percentage (the mechanism the PS5 test of 25 Nov showed on screen and kept). 'full' on an inferred line, and
  any level on bret, needs choice['unverified_ok'] = True, otherwise FeatureError('unverified').
  MIRRORS: incomplete challenge trackers whose score points at a changed row and equals its old value follow it
  (the rule of challenges.py and activities.py); none exist in the playthrough-A saves for these rows.
  Trophies, unlock rewards (tattoos, outfits, cheats) and cash prizes are granted by the game's own events and are
  not given. Nothing has been loaded on a PS5.

RISK: low for videogames; medium for the rest (counters are what the screen reads; per-item encodings inferred).
"""
import challenges
import checklist
import featurelib as fl

FEATURE = 'activities2'
ST = 'story000'
TP = 'totalprogressmade'
GOLD = 3                                   # highestmedal: 0 none, 1 bronze, 2 silver, 3 gold (inferred, see docstring)


def H(x):
    return fl.h(x)


# ---------------------------------------------------------------------------------------------- tables
ARCADE = (('arcadegamesurvivor', 'Street Trash III Dezombifier (survivor)'), ('arcadegametenebrae', 'Tenebrae Lux'),
          ('arcadegamebangforyourbuck', 'Bang for Your Buck'), ('arcadegametimejackersrewind', 'Time Jackers Rewind'))
ARCADE_ANY = 'arcadegameany'
B_GAMES_PLAYED = 0x40af8eca

RACES = (0x063f3aef, 0x138ed13e, 0x1545ad16, 0x1759b54c, 0x1cd960c4, 0x2c40df1a, 0x2df90ee6, 0x35dfe3cc, 0x3998e6ec,
         0x39ef7a77, 0x3a97b294, 0x3bc1fa0e, 0x3cb1207f, 0x40500734, 0x45ed32eb, 0x4849131c, 0x520f3da1, 0x62fc6d09,
         0x7a88f79b, 0x8a528867, 0x933828f9, 0x959544ac, 0x968b33a9, 0xa9710164, 0xaad55c3d, 0xb9dffa52, 0xba1e9b50,
         0xbc6ebba5, 0xbf54853b, 0xc84cb7ac, 0xc85c8052, 0xcd8a21a6, 0xd88ca927, 0xdc4de70d, 0xe2b74c00, 0xe9bf7da0,
         0xecd5c9f9, 0xf2f6f630, 0xf600aec8, 0xfc237a04, 0xff7f818a)
KNOWN_RACE_GROUP = {0xc85c8052: 'vcgroup'}            # A0 -> A1 (won once, 5 of vcgroup's 6 plays)
RACE_GROUPS = (('vcgroup', "Hit 'n' Run VC", 9, 'stats screen'), ('thrillbillymudclubgroup', 'Thrillbilly Mud Club', 8, 'guides'),
               ('gellhornracewaygroup', 'Gellhorn Raceway', 11, 'guides'), ('hamletboonespeedwaygroup', 'Boone Speedway', 2, 'guides'),
               ('ambrosiagroup', 'Ambrosia Raceway', 2, 'guides'), ('lcgroup', 'Animal Crackers (by elimination)', 8, 'guides'))

RACE_CHALLENGES = ((0x5f1c728d, None), (0x751cc590, None), (0x83bc934e, None), (0x9caae678, None), (0xf1ce4060, None),
                   ('gellhornracewaydragstrip', 'Gellhorn Raceway drag strip'), ('mountkalagadownhillmtb', 'Mount Kalaga downhill MTB'),
                   ('hamletbackyardbmx', 'Hamlet backyard BMX'), (0x5d16f293, None),
                   ('mudclubairtime', 'Mud Club air time'), ('mudclubhillclimb', 'Mud Club hill climb'),
                   ('mudclubswamprun', 'Mud Club swamp run'), ('mudclubdragstrip', 'Mud Club drag strip'))

RANGE_TIERS = ('beginner', 'intermediate', 'advanced', 'master')
RANGES = (('griffin', '3point', ('beginner', 'intermediate', 'advanced')), ('griffin', 'hook', ('beginner', 'intermediate', 'advanced')),
          ('griffin', 'loop', ('beginner', 'intermediate', 'advanced')), ('griffin', 'compound', ('intermediate', 'advanced', 'master')),
          ('griffin', 'maze', ('intermediate', 'advanced', 'master')), ('griffin', 'villa', ('intermediate', 'advanced', 'master')),
          ('rodgers', 'alien', RANGE_TIERS), ('rodgers', 'copsandrobbers', RANGE_TIERS), ('rodgers', 'hunting', RANGE_TIERS),
          ('rodgers', 'market', RANGE_TIERS), ('rodgers', 'saloon', RANGE_TIERS), ('rodgers', 'undead', RANGE_TIERS))
VENUES = (('griffin', 'Griffin Shooting Range'), ('rodgers', 'Rodgers Ranch & Shooting Range'))
MEDAL_BASES = (('shootingrangebronzemedals', 1), ('shootingrangesilvermedals', 2), ('shootingrangegoldmedals', 3))
TOTAL_MEDALS = 'shootingrangetotalmedals'

POOL_VENUES = ('pooldelights', 'poolkowaachobee', 'poolrustyanchor', 'poolskeetersbar', 'poolthethirstywolf', 'poolzoticos', 0x02ee1e5a)
B_POOL_FLAG = 0x68ea5b9f

MINIGOLF = (('frontieradventuregolf', 'Frontier Adventure Golf'), ('kinggatoradventuregolf', 'King Gator Adventure Golf'))
HOLES18 = 'holes18'

DRONE_VENUES = ('ambrosia', 'balsero', 'buckskinswamp', 'capri', 'daltonisland', 'downtown', 'draperisland', 'hamlet',
                'millport', 'moreausawmill', 'portgellhorn', 'vicebeach', 'waningsands', 'watsonbay')
DRONE_ROUTES = ('routea', 'routeb', 'routec')

B_DECKS = 0xa49f352b
BRET = 'cs_bret_vogel'

# key, checklist label, counter (base, qual, owner), percent qualifier, total for 100%, confidence
LINES = (
    ('videogames', 'VIDEO GAMES PLAYED', (B_GAMES_PLAYED, 0, ARCADE_ANY), ARCADE_ANY, 4, 'verified'),
    ('races', 'UNIQUE RACES WON', ('uniqueraceswon', 0, ST), 'uniqueraceswon', 30, 'inferred'),
    ('racechallenges', 'RACE CHALLENGE GOLD MEDALS', ('numgoldmedals', 'racechallenges', ST), 'racechallenges', 10, 'inferred'),
    ('shootingranges', 'SHOOTING RANGE GOLD MEDALS', ('shootingrangegoldmedals', 0, ST), 'shootingrangegoldmedals', 42, 'inferred'),
    ('pool', 'POOL OPPONENTS DEFEATED', ('opponentsdefeated', 'pool', ST), 'pool', 5, 'inferred'),
    ('minigolf', 'MINI GOLF LOCATIONS PLAYED', ('golfcoursescompleted', 0, ST), 'golfcoursescompleted', 2, 'inferred'),
    ('drones', 'DRONE TIME TRIALS COMPLETED', ('droneracesroutescompleted', 0, ST), 'droneracesroutescompleted', 42, 'inferred'),
    ('bret', "BRET'S TARGET DECKS", (B_DECKS, BRET, ST), B_DECKS, 15, 'counter_only'),
)
LINE = {x[0]: x for x in LINES}
LEVELS = ('full', 'counter')


def _name(x):
    return x if isinstance(x, str) else fl.hexid(x)


# ---------------------------------------------------------------------------------------------- edit helpers
class Edit:
    """Queues stat changes on a featurelib.Stats and remembers (row key -> (old, new)) for the tracker mirrors."""

    def __init__(self, st):
        self.st = st
        self.moved = {}

    def get(self, base, qual=0, owner=ST):
        v = self.st.value(base, qual, owner)
        if v is None:
            raise fl.FeatureError('layout_changed')
        return v

    def put(self, base, qual, owner, new, label):
        old = self.get(base, qual, owner)
        if old == new and type(old) is type(new):
            return False
        self.st.set(base, qual, new, label, owner)
        key = (H(base), H(qual) if qual else 0, H(owner))
        first = self.moved.get(key, (old, None))[0]
        self.moved[key] = (first, self.st.value(base, qual, owner))
        return True

    def add(self, base, qual, owner, n, label):
        if n:
            self.put(base, qual, owner, self.get(base, qual, owner) + n, label)


def _percent(ed, key, count):
    _, label, _, q, total, _ = LINE[key]
    ed.put(TP, q, ST, fl.pct32(count, total), label.capitalize() + ', part of 100% completion')


def _counter(ed, key, n_new, label=None):
    """Raise the line counter by n_new and set its percentage; returns the new counter."""
    _, lab, (b, q, o), _, _, _ = LINE[key]
    ed.add(b, q, o, n_new, label or lab.capitalize())
    new = ed.get(b, q, o)
    _percent(ed, key, new)
    return new


# ---------------------------------------------------------------------------------------------- per-line readers
def _read_videogames(st):
    games = [{'id': g, 'label': lab, 'started': bool(st.value('started', 0, g)), 'completed': bool(st.value('completed', 0, g))}
             for g, lab in ARCADE]
    n = sum(1 for g in games if g['started'])
    return {'items': games, 'done': n, 'itemsTotal': len(games), 'consistent': n == st.value(B_GAMES_PLAYED, 0, ARCADE_ANY)}


def _read_races(st):
    races = [{'id': fl.hexid(r), 'group': KNOWN_RACE_GROUP.get(r), 'won': st.value('raceswon', r), 'played': st.value('racesplayed', r)}
             for r in RACES]
    groups = [{'id': g, 'label': lab, 'size': n, 'sizeSource': src,
               'uniqueWon': st.value('uniqueraceswon', g), 'uniquePlayed': st.value('uniqueracesplayed', g),
               'won': st.value('raceswon', g), 'played': st.value('racesplayed', g), 'completed': st.value('racescompleted', g),
               'lost': st.value('raceslost', g), 'cash': st.value('cashwon', g)} for g, lab, n, src in RACE_GROUPS]
    won = sum(1 for r in races if r['won'])
    gap = {'uniqueWon': won - sum(g['uniqueWon'] or 0 for g in groups),
           'won': sum(r['won'] or 0 for r in races) - sum(g['won'] or 0 for g in groups),
           'played': sum(r['played'] or 0 for r in races) - sum(g['played'] or 0 for g in groups)}
    return {'items': races, 'groups': groups, 'done': won, 'itemsTotal': len(races),
            'consistent': won == st.value('uniqueraceswon'),
            'groupGap': gap,                 # race rows minus group sums: 0 in every game save, 1 after 'all' (41 rows, 40 in the guides' groups)
            'groupsConsistent': not any(gap.values())}


def _read_racechallenges(st):
    items = [{'id': _name(c), 'label': lab, 'medal': st.value('highestmedal', c),
              'gold': (st.value('highestmedal', c) or 0) >= GOLD} for c, lab in RACE_CHALLENGES]
    n = sum(1 for x in items if x['gold'])
    return {'items': items, 'done': n, 'itemsTotal': len(items), 'consistent': n == st.value('numgoldmedals', 'racechallenges')}


def _courses():
    for venue, rng, tiers in RANGES:
        for tier in tiers:
            yield venue, '%s%srange' % (venue, rng), tier


def _medal_counts(medals):
    """{(base, qual, owner): count} recount of every medal counter from {(range_owner, tier): highestmedal}."""
    out = {}

    def bump(k, v):
        out[k] = out.get(k, 0) + v
    for venue, rng, tier in _courses():
        m = medals[(rng, tier)]
        for base, need in MEDAL_BASES:
            hit = 1 if m >= need else 0
            for k in ((base, 0, rng), (base, tier, venue), (base, 0, venue), (base, 0, ST)):
                bump(k, hit)
        for k in ((TOTAL_MEDALS, 0, rng), (TOTAL_MEDALS, tier, venue), (TOTAL_MEDALS, 0, venue), (TOTAL_MEDALS, 0, ST)):
            bump(k, min(m, GOLD))
    return out


def _read_shootingranges(st):
    courses = [{'venue': v, 'range': r, 'tier': t, 'medal': st.value('highestmedal', t, r), 'unlocked': st.value('unlocked', t, r),
                'bestScore': st.value('bestscore', t, r)} for v, r, t in _courses()]
    medals = {(c['range'], c['tier']): c['medal'] or 0 for c in courses}
    rec = _medal_counts(medals)
    mism = sorted('%s.%s/%s' % k for k, v in rec.items() if st.value(*k) != v)
    gold = sum(1 for c in courses if (c['medal'] or 0) >= GOLD)
    return {'items': courses, 'done': gold, 'itemsTotal': len(courses), 'consistent': not mism, 'counterMismatches': mism[:20],
            'venues': [{'id': v, 'label': lab, 'medals': st.value(TOTAL_MEDALS, 0, v), 'rangesUnlocked': st.value('shootingrangecoursesunlocked', 0, v)}
                       for v, lab in VENUES]}


def _read_pool(st):
    items = [{'id': _name(v), 'flag': st.value(B_POOL_FLAG, v), 'gamesWon': st.value('gameswon', v)} for v in POOL_VENUES]
    n = sum(1 for x in items if x['flag'])
    return {'items': items, 'done': n, 'itemsTotal': len(items), 'consistent': n == st.value('opponentsdefeated', 'pool'),
            'gamesStarted': st.value('gamesstarted', 'pool'), 'gamesWon': st.value('gameswon', 'pool')}


def _read_minigolf(st):
    items = [{'id': o, 'label': lab, 'completed': st.value('coursecompleted', 0, o), 'games18': st.value('gamescompleted', HOLES18, o),
              'games9': st.value('gamescompleted', 'holes09', o)} for o, lab in MINIGOLF]
    n = sum(1 for x in items if x['completed'])
    return {'items': items, 'done': n, 'itemsTotal': len(items), 'consistent': n == st.value('golfcoursescompleted')}


def _read_drones(st):
    venues = []
    for v in DRONE_VENUES:
        routes = [{'route': r, 'state': st.value('completionstate', r, v), 'attempts': st.value('attempts', r, v)} for r in DRONE_ROUTES]
        venues.append({'id': v, 'found': st.value('found', 0, v), 'routesCompleted': st.value('routescompleted', 0, v), 'routes': routes,
                       'consistent': st.value('routescompleted', 0, v) == sum(1 for r in routes if r['state'])})
    done = sum(1 for x in venues for r in x['routes'] if r['state'])
    found = sum(1 for x in venues if x['found'])
    return {'items': venues, 'done': done, 'itemsTotal': len(venues) * len(DRONE_ROUTES), 'found': found,
            'consistent': done == st.value('droneracesroutescompleted') and found == st.value('droneracesfound')
            and all(x['consistent'] for x in venues)}


def _read_bret(st):
    return {'items': [], 'done': st.value(B_DECKS, BRET), 'itemsTotal': 15, 'storyWide': st.value(B_DECKS),
            'consistent': st.value(B_DECKS, BRET) == st.value(B_DECKS),
            'speciesSold': st.value('uniquehuntinganimalssold'), 'animalsSold': st.value('huntinganimalssold', BRET)}


READERS = {'videogames': _read_videogames, 'races': _read_races, 'racechallenges': _read_racechallenges,
           'shootingranges': _read_shootingranges, 'pool': _read_pool, 'minigolf': _read_minigolf, 'drones': _read_drones,
           'bret': _read_bret}


def read(b):
    s = fl.Save(b)
    st = fl.Stats(s.text(fl.STATS))
    lines = []
    for key, label, (cb, cq, co), q, total, conf in LINES:
        cnt = st.value(cb, cq, co)
        pct = st.value(TP, q)
        r = READERS[key](st)
        lines.append(dict(r, key=key, label=label, counter=cnt, of=total, shown=None if cnt is None else min(cnt, total),
                          percent=pct, percentConsistent=None if cnt is None or pct is None else abs(fl.pct32(cnt, total) - pct) <= 2e-6,
                          confidence=conf, levels=['counter'] if key == 'bret' else list(LEVELS),
                          done_line=bool(pct is not None and pct >= 100.0)))
    return {'feature': FEATURE, 'lines': lines, 'overall': st.value(*checklist.OVERALL),
            'possible': [x['key'] for x in lines if not x['done_line']], 'risk': 'medium',
            'notes': ['Video games: the started flags and the games-played counter (verified in every save).',
                      'Races, race challenges, shooting ranges, pool, mini golf and drones were never played in these saves: '
                      "the counters are what the 100% screen reads; 'full' also writes the per-item rows with inferred "
                      "values (gold = 3, completed = 1) and needs unverified_ok.",
                      "Bret's target decks: only the counters; the deck progress is not in any save."]}


# ---------------------------------------------------------------------------------------------- per-line writers
def _apply_videogames(ed, level):
    new = 0
    for g, lab in ARCADE:
        if not ed.get('started', 0, g):
            new += 1
            if level == 'full':
                ed.put('started', 0, g, True, 'Video game started: ' + lab)
    if level == 'full' and new:
        ed.put('started', 0, ARCADE_ANY, True, 'Video games: any started')
    if level == 'counter':
        _, _, (b, q, o), _, total, _ = LINE['videogames']
        new = max(0, total - ed.get(b, q, o))
    return _counter(ed, 'videogames', new), new


def _apply_races(ed, level):
    if level == 'counter':
        new = max(0, LINE['races'][4] - ed.get('uniqueraceswon'))
        return _counter(ed, 'races', new), new
    new_rows = 0
    for r in RACES:
        if not ed.get('raceswon', r):
            new_rows += 1
            ed.put('raceswon', r, ST, 1, 'Race %s won' % fl.hexid(r))
            ed.add('racesplayed', r, ST, 1, 'Race %s played' % fl.hexid(r))
    for g, lab, size, _ in RACE_GROUPS:
        k = size - ed.get('uniqueraceswon', g)
        if k <= 0:
            continue
        ed.put('uniqueraceswon', g, ST, size, lab + ': unique races won')
        if ed.get('uniqueracesplayed', g) < size:
            ed.put('uniqueracesplayed', g, ST, size, lab + ': unique races entered')
        for base, what in (('raceswon', 'races won'), ('racesplayed', 'races entered'), ('racescompleted', 'races completed'),
                           ('firstplacereached', 'first places')):
            ed.add(base, g, ST, k, '%s: %s' % (lab, what))
    return _counter(ed, 'races', new_rows), new_rows


def _apply_racechallenges(ed, level):
    if level == 'counter':
        new = max(0, LINE['racechallenges'][4] - ed.get('numgoldmedals', 'racechallenges'))
        return _counter(ed, 'racechallenges', new), new
    new = 0
    for c, lab in RACE_CHALLENGES:
        if ed.get('highestmedal', c) < GOLD:
            new += 1
            ed.put('highestmedal', c, ST, GOLD, 'Race challenge %s: gold medal' % (lab or _name(c)))
    return _counter(ed, 'racechallenges', new), new


def _apply_shootingranges(ed, level):
    if level == 'counter':
        new = max(0, LINE['shootingranges'][4] - ed.get('shootingrangegoldmedals'))
        return _counter(ed, 'shootingranges', new), new
    before = {(r, t): ed.get('highestmedal', t, r) for _, r, t in _courses()}
    after = {}
    for venue, rng, tier in _courses():
        after[(rng, tier)] = max(before[(rng, tier)], GOLD)
        if before[(rng, tier)] < GOLD:
            ed.put('highestmedal', tier, rng, GOLD, '%s %s: gold medal' % (rng, tier))
        if not ed.get('unlocked', tier, rng):
            ed.put('unlocked', tier, rng, True, '%s %s: unlocked' % (rng, tier))
        if ed.get('timescompleted', tier, rng) < 1:
            ed.put('timescompleted', tier, rng, 1, '%s %s: times completed' % (rng, tier))
    r0, r1 = _medal_counts(before), _medal_counts(after)
    gold_new = r1[('shootingrangegoldmedals', 0, ST)] - r0[('shootingrangegoldmedals', 0, ST)]
    for k in sorted(r1, key=str):
        if k == ('shootingrangegoldmedals', 0, ST):
            continue
        ed.add(k[0], k[1], k[2], r1[k] - r0[k], '%s %s' % (k[0], k[2] if not k[1] else '%s/%s' % (k[1], k[2])))
    # unlocks: every range and venue, all courses and ranges
    n_courses = {}
    for venue, rng, tier in _courses():
        n_courses[rng] = n_courses.get(rng, 0) + 1
        n_courses[venue] = n_courses.get(venue, 0) + 1
    for owner, n in n_courses.items():
        if not ed.get('unlocked', 0, owner):
            ed.put('unlocked', 0, owner, True, owner + ': unlocked')
        for base in ('challengesunlocked', 'uniquechallengescompleted'):
            if ed.get(base, 0, owner) < n:
                ed.put(base, 0, owner, n, '%s: %s' % (owner, base))
    for venue, _ in VENUES:
        ranges = sum(1 for v, _, _ in RANGES if v == venue)
        if ed.get('shootingrangecoursesunlocked', 0, venue) < ranges:
            ed.put('shootingrangecoursesunlocked', 0, venue, ranges, venue + ': ranges unlocked')
    for base, n in (('shootingrangelocationsunlocked', len(VENUES)), ('shootingrangecoursesunlocked', len(RANGES)),
                    ('shootingrangechallengesunlocked', sum(n_courses[v] for v, _ in VENUES))):
        if ed.get(base) < n:
            ed.put(base, 0, ST, n, 'Shooting ranges: ' + base)
    return _counter(ed, 'shootingranges', gold_new), gold_new


def _apply_pool(ed, level):
    if level == 'counter':
        new = max(0, LINE['pool'][4] - ed.get('opponentsdefeated', 'pool'))
        return _counter(ed, 'pool', new), new
    new = 0
    for v in POOL_VENUES:
        if not ed.get(B_POOL_FLAG, v):
            new += 1
            ed.put(B_POOL_FLAG, v, ST, True, 'Pool opponent defeated: %s' % _name(v))
            ed.add('gameswon', v, ST, 1, 'Pool games won: %s' % _name(v))
    ed.add('gameswon', 'pool', ST, new, 'Pool games won')
    ed.add('gamesstarted', 'pool', ST, new, 'Pool games started')
    return _counter(ed, 'pool', new), new


def _apply_minigolf(ed, level):
    if level == 'counter':
        new = max(0, LINE['minigolf'][4] - ed.get('golfcoursescompleted'))
        return _counter(ed, 'minigolf', new), new
    new = 0
    for o, lab in MINIGOLF:
        if not ed.get('coursecompleted', 0, o):
            new += 1
            ed.put('coursecompleted', 0, o, True, lab + ': course completed')
            ed.add('gamescompleted', HOLES18, o, 1, lab + ': 18-hole games completed')
    ed.add('gamescompleted', HOLES18, ST, new, 'Mini golf: 18-hole games completed')
    ed.add('gamesstarted', HOLES18, ST, new, 'Mini golf: 18-hole games started')
    return _counter(ed, 'minigolf', new), new


def _apply_drones(ed, level):
    if level == 'counter':
        new = max(0, LINE['drones'][4] - ed.get('droneracesroutescompleted'))
        return _counter(ed, 'drones', new), new
    new_routes = new_found = 0
    for v in DRONE_VENUES:
        if not ed.get('found', 0, v):
            new_found += 1
            ed.put('found', 0, v, True, 'Top Fun Drones %s: unlocked' % v)
        k = 0
        for r in DRONE_ROUTES:
            if not ed.get('completionstate', r, v):
                k += 1
                ed.put('completionstate', r, v, 1, 'Drone time trial %s %s: completed' % (v, r))
            if ed.get('attempts', r, v) < 1:
                ed.put('attempts', r, v, 1, 'Drone time trial %s %s: attempts' % (v, r))
        ed.add('routescompleted', 0, v, k, 'Top Fun Drones %s: routes completed' % v)
        new_routes += k
    ed.add('droneracesfound', 0, ST, new_found, 'Top Fun Drones unlocked')
    return _counter(ed, 'drones', new_routes), new_routes


def _apply_bret(ed, level):
    cur = ed.get(B_DECKS, BRET)
    story = ed.get(B_DECKS)
    new = max(0, LINE['bret'][4] - cur)
    _counter(ed, 'bret', new, "Bret's target decks completed")
    if story == cur:
        ed.add(B_DECKS, 0, ST, new, "Target decks completed (all contacts)")
    return ed.get(B_DECKS, BRET), new


WRITERS = {'videogames': _apply_videogames, 'races': _apply_races, 'racechallenges': _apply_racechallenges,
           'shootingranges': _apply_shootingranges, 'pool': _apply_pool, 'minigolf': _apply_minigolf, 'drones': _apply_drones,
           'bret': _apply_bret}


# ---------------------------------------------------------------------------------------------- mirrors
def mirror_trackers(t, moved):
    """Incomplete challenge trackers whose score points at a moved stat row and equals its old value get the new value.
    moved: {(base, qual, owner) hashes: (old, new)}. Returns (new text, log)."""
    edits, log = [], []
    for r in challenges._records(t):
        if r['done']:
            continue
        for a, z, key in challenges._scores(t, *r['param']):
            if key not in moved:
                continue
            old, new = moved[key]
            tok = t[a:z].lstrip(b'-')
            if isinstance(old, (bool, float)) or not tok.isdigit():
                continue                         # bool sub-conditions ('true', e.g. SPORTS 9f75f7b8 per county) and floats
            if t[a:z] != b'%d' % old:
                log.append({'what': 'tracker_kept', 'challenge': fl.hexid(r['id']), 'score': t[a:z].decode(), 'counter': old})
                continue
            edits.append((a, z, b'%d' % new))
            log.append({'what': 'tracker_score', 'challenge': fl.hexid(r['id']), 'set': fl.hexid(r['set']), 'from': old, 'to': new})
    for a, z, tok in sorted(edits, key=lambda x: -x[0]):
        t = t[:a] + tok + t[z:]
    return t, log


def finish(s, st, moved, log):
    """Recompute the overall figure, mirror trackers, write both sections; -> (bytes, log)."""
    checklist.refresh_overall(st)
    t = s.text(challenges.SEC)
    t2, tlog = mirror_trackers(t, moved)
    if t2 != t:
        s.set_text(challenges.SEC, t2)
    txt, slog = st.apply()
    if not slog and t2 == t:
        return s.orig, log + tlog
    s.set_text(fl.STATS, txt)
    return s.build(), log + tlog + slog


# ---------------------------------------------------------------------------------------------- apply
def apply(b, choice=None):
    """choice: {'lines': 'all' | [line keys], 'level': 'full' | 'counter' | {line: level}, 'unverified_ok': False}
    -> (new bytes, log). 'full' on an inferred line, and bret at any level, need unverified_ok."""
    choice = choice or {}
    want = choice.get('lines', 'all')
    keys = [x[0] for x in LINES] if want == 'all' else want
    if isinstance(keys, (str, bytes)) or not hasattr(keys, '__iter__'):
        raise fl.FeatureError('bad_request')
    keys = list(dict.fromkeys(keys))
    if any(k not in LINE for k in keys):
        raise fl.FeatureError('unknown_line')
    lv = choice.get('level', 'full')
    levels = {k: (lv.get(k, 'full') if isinstance(lv, dict) else lv) for k in keys}
    if any(v not in LEVELS for v in levels.values()):
        raise fl.FeatureError('bad_request')
    levels['bret'] = 'counter' if 'bret' in levels else None
    unverified = bool(choice.get('unverified_ok'))
    blocked = [k for k in keys if (LINE[k][5] == 'inferred' and levels[k] == 'full') or LINE[k][5] == 'counter_only']
    if blocked and not unverified:
        raise fl.FeatureError('unverified')
    s = fl.Save(b)
    st = fl.Stats(s.text(fl.STATS))
    ed = Edit(st)
    log = []
    for k in keys:
        value, new = WRITERS[k](ed, levels[k])
        if new:
            log.append({'what': 'line', 'line': k, 'level': levels[k], 'added': new, 'counter': value, 'of': LINE[k][4],
                        'confidence': LINE[k][5]})
    if not log:
        return b, []
    return finish(s, st, ed.moved, log)
