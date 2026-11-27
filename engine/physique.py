"""The three per-character level stats and their script-side copies in story saves."""
import json

import featurelib as fl
import jsonedit as je

SECTION = 0x46f14889
ROOT = ('$0x24d043f2', fl.key(SECTION), '$0x45a134ec')
MODEL = '$0xcd1245e5'
OWNERS = {'Lucia': 0xb3634b85, 'Jason': 0x25350e5c}
# Cardio and focus are distinguishable in saves where their levels differ (issue #4).
LEVELS = {'muscle': ('Strength level', '$0x2c4379f2', 4),
          'cardio': ('Cardio level', '$0x381bd0ae', 3),
          'focus': ('Focus level', '$0xd3de8c6b', 3)}

CURRENT_LEVEL = fl.h('currentlevel')
STAT_KEYS = {(fl.h(qual), owner): (who, qual) for who, owner in OWNERS.items() for qual in LEVELS}


def character_blocks(text):
    root = json.loads(text)
    for key in ROOT:
        root = root.get(key) if isinstance(root, dict) else None
    if not isinstance(root, dict):
        return {}
    blocks = {}
    for who in OWNERS:
        model = fl.h('player_' + who.lower())
        matches = [(key, block) for key, block in root.items() if isinstance(block, dict)
                   and type(block.get(MODEL)) is int and block[MODEL] & 0xffffffff == model]
        if len(matches) == 1:
            blocks[who] = matches[0]
    return blocks


def stat_entries(stats):
    for who, owner in OWNERS.items():
        for qual, (label, field, limit) in LEVELS.items():
            row = stats.row('currentlevel', qual, owner)
            if row and row['type'] == 'int32':
                yield who, label, field, limit, row


def read(text, stats):
    blocks = character_blocks(text)
    rows = []
    for who, label, field, limit, row in stat_entries(stats):
        if who not in blocks:
            continue
        stored = blocks[who][1].get(field)
        if type(stored) is int and 0 <= stored <= limit:
            rows.append(dict(row, who=who, label=label, maximum=limit, physique=stored))
    return rows


def sync(entities, sections, targets):
    """Patch just the requested fields using the script's model IDs, including on previously edited saves."""
    from savedit import SaveError
    indices = [i for i, entry in enumerate(entities) if entry[0] == SECTION]
    if len(indices) != 1:
        raise SaveError('physique_layout')
    index = indices[0]
    text = sections[index]
    blocks = character_blocks(text)
    log = []
    for (who, qual), target in targets.items():
        label, field, limit = LEVELS[qual]
        if not 0 <= target <= limit:
            raise SaveError('out_of_range')
        key, block = blocks.get(who, (None, {}))
        old = block.get(field)
        if type(old) is not int or not 0 <= old <= limit:
            raise SaveError('physique_layout')
        if old != target:
            text = je.put(text, (*ROOT, key, field), je.fmt_int(target))
            log.append({'what': 'physique', 'label': who + ' / ' + label + ' (physique)', 'from': old, 'to': target})
    sections[index] = text
    return log
