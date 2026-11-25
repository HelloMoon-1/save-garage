"""Optional tasks: the 100% checklist line 'OPTIONAL TASKS COMPLETED x / 100' (Save Garage feature module, READ-ONLY).

There is deliberately no apply(): completing optional tasks by editing the save is not offered (see WHY NOT EDITABLE).
read() shows what is done and what the save can say about what is missing, so the tasks can be played.

WHERE THE LINE LIVES
  * Counter: stats sidetaskscompleted/story000 (int32). The screen reads it: the 25 Nov test edit set it to 97 and the
    PS5 showed 'OPTIONAL TASKS COMPLETED 97 / 100' while nothing else had changed.
  * Records: ScriptGameCompletion (script section 5299e475), list 0x7ed0c5af of {0xea0ddfb4 content id hash,
    CompletionType}, unique ids sorted as signed int32. Type 1 = story, 2 = optional task, 3 = counts for both.
    The id is the joaat of the mission/task id and also the key of its title in the game text ('mtl_pain' ->
    91e56ead -> 'Slam Dunk'), so titled ids are named exactly; 57 of the 95 optional ids have no title in our text dump.
  * Percentage: totalprogressmade.optionaltasks = float32(counter * 0.99) (checklist.percent_for); the game rebuilds it
    from the counter when it saves (B7a: one type-2 record, counter 0, percentage 0.0). Weight 6 in the 100% figure.

WHAT THE GAME WRITES WHEN A TASK COMPLETES (game-written saves, diffed)
  * A new ScriptGameCompletion record {id, 2} (or 3), inserted in signed-int32 order.
  * sidetaskscompleted becomes the number of type 2 + type 3 records. In every save after a completion the counter
    equals the records: A0 22, A1 41, A2 56, A3 58, A4 75, A5 91, A6as 94 (+19, +15, +2, +17, +16, +3 for the same
    numbers of new records). Playthrough B shows it is a recount, not an increment: B7a held one type-2 record
    (449725be) with the counter at 0; after two more tasks (B7as_b) the counter was 3, not 2.
  * Discovery (940e954d) FlagState for the id: 0x40 -> 0xc0, or a new entry with 0x80 / 0xc0 (0x80 = done). The
    id's membership of the Discovered and DiscoveryOrder lists changes too, both ways (of the 74 new optional
    records in the game-written saves, 25 left Discovered and 27 joined it), so those lists behave like a 'new'
    marker, not a done flag.
  * Tasks that are ambient objectives (45 of the 94): ScriptAmbientObjective (86572177) AmbientObjectiveSaveData
    State 2 (or 0/1) -> 3, Flags and the time field updated, and its 0x94a3467d CompletedTasks record removed.
    Example A5as -> A6as: 9f66e473 State 2 -> 3, Flags 0 -> 69; 57079dae State 2 -> 3, Flags 896 -> 1989.
  * Side missions that count (Mall Rats, PEACH!, Puff Puff Pass, Brother to Brother, Bumper to Bumper, Hometown
    Heroes, The Last Mile: Passing the Torch...) also run their mission flow (ScriptFlow, ContentTags, stats owner rows).
  * Then the percentage and the overall figure at the next save.

WHAT IS MISSING IN THE 67.5% SAVE (A6b): 94 of 100
  * 92 type-2 + 2 type-3 records (Twist Wrist, Smash, Grab and Thrillbillies count for both).
  * Identified missing task: d6b633ab (no title in the game text). Playthrough B completed it (B7as_b: type-2
    record, objective State 3, Flags 1089, map flag 0xc0, and it counted in the counter). In A6b it is an ambient
    objective that was never started (State 0, Flags 0) with map flag 0x40.
  * The other 5 cannot be identified: the save only records tasks once they are done (31 of the 72 optional ids
    completed in playthrough A appear in no section before completion, 12 of 19 in A0 -> A1; the rest appear only
    as ambient objectives or map flags, which do not mark a task as optional: A6b holds 134 unfinished ambient
    objectives), and the full list of optional tasks is game data, not save data. 'notPassed' lists the side missions that have stats rows but were never passed (medal 0, no record);
    some of them may be the missing tasks (See You Again is in the same strand as two optional tasks), others count
    as story (type 1) or not at all. It is a list to play from, not a list of the missing 5.

WHY NOT EDITABLE
  * The ids of 5 of the 6 missing tasks are not in the save, so their records cannot be written.
  * Writing records for tasks that were not played leaves their own state behind: the ambient objective stays
    State 0/1/2 and is still offered, side missions keep their flow nodes, and any reward the game gives on completion
    (vehicles to collect, gifts, contacts) is not granted. What the game does when a recorded task is offered again
    is unknown.
  * A counter-only edit (possible through the stats editor) changes the screen but completes nothing, and the next
    real optional task resets the counter to the record count (B7a -> B7as_b), so the line would drop back.
  * One identified task (d6b633ab) would give 95 / 100 and 0.06 points of the 100% figure, at the cost of an
    ambient objective whose content is unknown. Not worth the risk to a finished story save.

RISK: none (read-only).
"""
import json

import checklist
import featurelib as fl

FEATURE = 'tasks'
SEC_COMPLETION = 0x5299e475          # ScriptGameCompletion (script block)
SEC_DISCOVERY = 0x940e954d           # Discovery (code block)
SEC_AMBIENT = 0x86572177             # ScriptAmbientObjective (script block)
SCRIPT = '$0x24d043f2'               # ScriptSaveBlock wrapper
SCRIPT_INNER = '$0x45a134ec'
K_RECORDS, K_ID, K_TYPE = '$0x7ed0c5af', '$0xea0ddfb4', fl.key('CompletionType')
K_FLAGSTATE, K_NAME, K_STATEFLAGS = fl.key('FlagState'), fl.key('Name'), fl.key('StateFlags')
K_AO, K_AO_ID, K_AO_FLAGS, K_AO_STATE = fl.key('AmbientObjectiveSaveData'), fl.key('Id'), fl.key('Flags'), fl.key('State')
COUNTER = ('sidetaskscompleted', 0)
PCT = ('totalprogressmade', 'optionaltasks')
FOR_100 = 100
TYPES = {1: 'story', 2: 'optional', 3: 'story and optional'}
PROFILE_OWNERS = {fl.joaat(x) for x in ('story000', 'charlucia', 'charjason', 'withpartner', 'withpartnerfreeroam')}
B_MEDAL = fl.joaat('highestmedal')

# Every content id recorded as an optional task (CompletionType 2 or 3) in the 15 game-written saves of this console:
# id -> (title from the game text or None, mission id from the stats owner names or None).
KNOWN_OPTIONAL = {
    0x822e57a2: (None, None), 0x83598d66: (None, None), 0x845ad609: ('Mall Rats', 'csc_drt_mall'),
    0x8729196d: (None, None), 0x873335fd: (None, None), 0x8913a1db: (None, None), 0x897e7590: (None, None),
    0x8b8f432d: (None, None), 0x8bc5133b: (None, None), 0x8c9379f4: ('Collect your Venturas BLVD Elegy', None),
    0x8cfa0575: ('Explore Capri Together', None), 0x8d14cfe4: ('The Last Mile: Stormy Weather', None),
    0x8d988d0c: (None, None), 0x8da04fdf: (None, None), 0x900bf652: (None, None),
    0x94e786df: ('Twist Wrist, Smash, Grab', 'csc_drt_cnvy'), 0x9d73bcef: ('Save for the Future', None),
    0x9f66e473: (None, None), 0xa3bc7019: ('Veteran Hunted', 'collehunttut'), 0xabd9a24f: (None, None),
    0xad8c8a22: (None, None), 0xb16a68e5: ('Puff Puff Pass', 'csc_mlm_wrhs'), 0xb2ad7e36: ('Recover Stashed Cocaine', None),
    0xb9c704b2: (None, None), 0xc1805a52: (None, None), 0xc313872d: (None, None), 0xc655f1b7: (None, None),
    0xc6a4785b: (None, None), 0xc7a4a8c4: (None, None), 0xcc55096c: (None, None), 0xcd211559: (None, None),
    0xcef46b49: ('Read the Label', None), 0xd06a1205: ('PEACH!', 'csc_mlm_initi'), 0xd6b633ab: (None, None),
    0xda9123e7: (None, None), 0xdd3cb651: ('Go Home and Sleep', None), 0xdfa27b73: (None, None),
    0xe3d0f7e5: ('¡Dale Mamba!', None), 0xe77dd015: ('If the Clothes Fit', None), 0xe9ced5a4: ('Save for the Future', None),
    0xee5fe964: ('The Last Mile: Hostile Takeover', None), 0xf10c61e4: (None, None), 0xf51ef13e: ('Flowers For a Lady', None),
    0xf618ee38: ('Save for the Future', None), 0xf7806a93: (None, None), 0xfe519aab: (None, None),
    0xff9d7107: ("It's a Date!", None), 0x028f9e1c: ('Brother to Brother', 'csc_srs_bybst'),
    0x03cdad54: ('Thrillbillies', 'mtl_mud'), 0x05e84bf3: (None, None), 0x07d1d866: (None, None),
    0x0aabbf63: ('Bad Driver!', None), 0x0d1f3bb2: (None, None), 0x0ff67528: (None, None), 0x174e9b2c: (None, None),
    0x1a132d06: (None, None), 0x1a82f38d: (None, None), 0x1bb53970: ('Save for the Future', None), 0x1e92251a: (None, None),
    0x2007429b: ("Collect your '55 Vapid Stanier", None), 0x21069d86: (None, None),
    0x2590efe8: ('Collect your Dominator Buggy', None), 0x30d513e9: ('Pick Up Groceries', None), 0x33049e46: (None, None),
    0x381a4ecf: (None, None), 0x3ab5a176: (None, None), 0x3d8b5d44: ('Bumper to Bumper', 'csc_srs_ropes'),
    0x408331e8: ('The Impaler', None), 0x449725be: (None, None), 0x47dc640a: ('Join a Street Race', None),
    0x480b310b: (None, None), 0x4a4d3b03: (None, None), 0x4ac3eb03: ('The Last Mile: Passing the Torch', 'com_smglr_rp'),
    0x4d41c9ff: ("Collect Felipe's Gift", None), 0x50c7efbc: (None, None), 0x55224cae: ('Get the Chop', None),
    0x56fa677a: ("That's Where The Money Is...", None), 0x57079dae: (None, None), 0x57b4d816: (None, None),
    0x5dcd3cd3: ("Dre'Quan's Gift", None), 0x5e11feed: (None, None), 0x5e14f15d: (None, None),
    0x5efd1f79: ('Hometown Heroes', 'csc_drt_final'), 0x63fbdba0: (None, None), 0x64957eea: ('Keepsake', None),
    0x65531245: (None, None), 0x666760c3: (None, None), 0x6c1c74f9: (None, None), 0x6f54bf34: (None, None),
    0x72acea45: (None, None), 0x74ed2fe5: ('The Last Mile: Over and Out', None), 0x779dd79b: (None, None),
    0x78bbbfa1: (None, None), 0x795a52f3: (None, None), 0x79e44764: ('Find the Lost Drugs', None),
}
# Where an optional id was seen when it is not in the 67.5% save.
SEEN_IN = {0xd6b633ab: 'playthrough B (B7as_b, B7b): type-2 record, ambient objective State 3, counted in the counter'}
# Titles (game text) of story records whose id is not a stats owner, so gamelabels.OWNER_LABELS lacks them. Used to
# recognise multi-part missions that are done under another id (The End of the Road has three records).
STORY_TITLES = {
    0xcc9c15c2: 'Behind on Payments', 0x489055b6: 'Blood Sweat and Gear', 0x23bf8778: 'Checking Out',
    0xe5a812fe: 'Coming Home', 0xd30cf4ae: 'Crosstown Traffic', 0x0094c57a: "Donnie's Drop", 0xeab842ac: "Donnie's Drop",
    0x3aa96629: 'Down to Earth', 0x3ad0562c: 'Dubious Provenance', 0xc90e04b5: 'Dubious Provenance',
    0xaf46f8c6: 'Fully Catered', 0x5cb7db5c: 'Gear Up', 0xd244cb70: 'Just a Scratch', 0xe48c934a: 'Just a Scratch',
    0x98c85f2a: 'Prologue', 0x9530ab91: 'The End of the Road', 0x96f9a142: 'The End of the Road',
    0x9fd04b65: 'The End of the Road', 0xbbbbebf6: 'Tourist Trap', 0x360a9f27: 'VCIA Takedown',
}


def _s32(x):
    return x - (1 << 32) if x & 0x80000000 else x


def script_payload(sec_txt, sec_hash):
    """Parsed payload of a script-block section (wrapper and inner wrapper removed)."""
    return json.loads(sec_txt)[SCRIPT][fl.key(sec_hash)][SCRIPT_INNER]


def _hash(v):
    return int(v['$data'], 16) & fl.M32 if isinstance(v, dict) else v & fl.M32


def records(s):
    """[(content id, CompletionType)] of ScriptGameCompletion, in file order."""
    return [(_hash(e[K_ID]), e[K_TYPE]) for e in script_payload(s.text(SEC_COMPLETION), SEC_COMPLETION)[K_RECORDS]]


def _flagstates(s):
    return {_hash(e[K_NAME]): e[K_STATEFLAGS] for e in fl.payload(s.text(SEC_DISCOVERY), SEC_DISCOVERY)[K_FLAGSTATE]}


def _objectives(s):
    return {_hash(e[K_AO_ID]): {'state': e[K_AO_STATE], 'flags': e[K_AO_FLAGS]}
            for e in script_payload(s.text(SEC_AMBIENT), SEC_AMBIENT)[K_AO]}


def _titles():
    out = {}
    try:
        import gamelabels
        out.update(gamelabels.OWNER_LABELS)
    except ImportError:
        pass
    out.update(STORY_TITLES)
    out.update({h: t for h, (t, _) in KNOWN_OPTIONAL.items() if t})
    return out


def _owner_names():
    try:
        import statnames
        return {fl.joaat(n): n for n in statnames.OWNER_NAMES}
    except ImportError:
        return {}


def _entry(hh, ctype=None):
    title, mission = KNOWN_OPTIONAL.get(hh, (None, None))
    out = {'id': fl.hexid(hh), 'title': title, 'mission': mission}
    if ctype is not None:
        out['type'] = TYPES.get(ctype, str(ctype))
    return out


def _not_passed(st, recs, titles, names):
    """Missions with stats rows (highestmedal, no qualifier) that were never passed: medal 0, no completion record
    with that id, and no completed record with the same title (multi-part missions record other ids)."""
    done_titles = {titles.get(h) for h in recs} - {None}
    by_strand = {}
    for h, t in recs.items():
        n = names.get(h)
        if n and n.count('_') >= 2:
            by_strand.setdefault(n.rsplit('_', 1)[0], []).append(TYPES.get(t, str(t)))
    out = []
    for (b, q, o), (g, r) in sorted(st.where.items(), key=lambda kv: names.get(kv[0][2]) or 'zz%08x' % kv[0][2]):
        if b != B_MEDAL or q != 0 or o in PROFILE_OWNERS or o in recs:
            continue
        if st.groups[g]['value'][r]:
            continue
        title = titles.get(o)
        if title and title in done_titles:
            continue
        name = names.get(o)
        strand = name.rsplit('_', 1)[0] if name and name.count('_') >= 2 else None
        out.append({'id': fl.hexid(o), 'mission': name, 'title': title,
                    'strandDone': sorted(by_strand.get(strand, [])) if strand else []})
    return out


def read(b):
    s = fl.Save(b)
    st = fl.Stats(s.text(fl.STATS))
    recs_list = records(s)
    recs = dict(recs_list)
    counter = st.value(*COUNTER)
    pct = st.value(*PCT)
    optional = [(h, t) for h, t in recs_list if t in (2, 3)]
    flags = _flagstates(s)
    objectives = _objectives(s)
    titles, names = _titles(), _owner_names()

    done = []
    for h, t in sorted(optional, key=lambda x: _s32(x[0])):
        e = _entry(h, t)
        if not e['title']:
            e['title'] = titles.get(h)
        if not e['mission']:
            e['mission'] = names.get(h)
        e['ambientObjective'] = h in objectives
        done.append(e)
    missing = max(0, FOR_100 - (counter or 0))
    known_missing = []
    for h in sorted(KNOWN_OPTIONAL, key=_s32):
        if h in recs and recs[h] in (2, 3):
            continue
        e = _entry(h)
        e['seenIn'] = SEEN_IN.get(h, 'playthrough A of this console')
        e['ambientObjective'] = objectives.get(h)
        e['mapFlags'] = None if h not in flags else '0x%x' % flags[h]
        e['recordedAs'] = TYPES.get(recs[h]) if h in recs else None
        known_missing.append(e)
    expected = checklist.percent_for('optionaltasks', counter or 0)
    by_type = {name: sum(1 for t in recs.values() if t == k) for k, name in TYPES.items()}
    return {'feature': FEATURE,
            'checklist': {'label': 'OPTIONAL TASKS COMPLETED', 'value': counter, 'of': FOR_100, 'shown': min(counter or 0, FOR_100),
                          'percent': pct, 'percentExpected': expected,
                          'percentConsistent': pct is not None and abs(pct - expected) <= max(2e-6, abs(pct) * 2e-7),
                          'weight': checklist.WEIGHTS['optionaltasks']},
            'counter': {'row': 'sidetaskscompleted/story000', 'value': counter, 'records': len(optional),
                        'consistent': counter == len(optional)},
            'records': by_type,
            'done': done,
            'missing': missing,
            'knownMissing': known_missing,
            'unidentified': max(0, missing - len(known_missing)),
            'notPassed': _not_passed(st, recs, titles, names),
            'editable': False,
            'risk': 'not offered',
            'why': ['The ids of most missing tasks are not in the save: tasks are recorded only once done, and the list of all '
                    'optional tasks is game data.',
                    'Recording a task that was not played leaves its own state behind (the ambient objective is still offered, '
                    'mission flow and rewards are not given).',
                    'The game resets sidetaskscompleted to the number of records when the next task completes, so a counter-only '
                    'edit would not last.'],
            'notes': ['The screen reads sidetaskscompleted; the percentage (count x 0.99) is rebuilt from it when the game saves.',
                      'knownMissing: tasks recorded as optional in another save of this console but not done here.',
                      'notPassed: missions with stats rows that were never passed. Some may count as optional tasks; the save '
                      'does not say which. strandDone gives the types of the missions already done in the same strand.']}
