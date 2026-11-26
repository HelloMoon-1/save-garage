# Save Garage - Copyright (C) 2026 NotHGM - GNU GPL v3 with the additional terms in NOTICE; see LICENSE.
"""What a number in the save stands for, when it is the ID of something the app already has a name for.

Many values in the save are joaat hashes used as IDs: inventory items and slots, stat names, locations, vehicles,
missions. The Save data tab shows the name next to such a value. A large number matches a known ID by chance about
once in a million values, so only numbers of 65,536 or more (or negative) are looked up.
"""
import gamelabels
import itemnames
import money
import savekeys
import statnames
import textlabels

M32 = 0xffffffff
_D = None
KIND_WORDS = {'item': 'Item', 'slot': 'Inventory slot', 'stat': 'Stat', 'name': 'Name', 'mission': 'Mission or task', 'place': 'Place',
              'text': 'Game text', 'post': 'Social media post', 'article': 'News article', 'account': 'Social media account', 'collectible': 'Collectible',
              'key': 'Save data key', 'section': 'Section'}


def _table():
    """hash -> (kind, label or None, name or None)"""
    global _D
    if _D is not None:
        return _D
    J = money.joaat
    d = {}

    def put(h, kind, label=None, name=None):
        h &= M32
        k, l, n = d.get(h, (kind, None, None))
        d[h] = (k, l or label, n or name)

    for n in itemnames.ITEM_NAMES:
        put(J(n), 'item', name=n)
    for h, l in itemnames.ITEM_LABELS.items():
        put(h, 'item', label=l)
    for n in itemnames.SLOT_NAMES:
        put(J(n), 'slot', name=n)
    for n in statnames.BASE_NAMES:
        put(J(n), 'stat', name=n)
    for n in statnames.QUALIFIER_NAMES + statnames.OWNER_NAMES:
        put(J(n), 'name', name=n)
    for h, l in list(gamelabels.QUALIFIER_LABELS.items()) + list(gamelabels.OWNER_LABELS.items()):
        put(h, 'name', label=l)
    import gangs, robberies, tasks               # titles and places known to the Completion modules
    for h, (title, mission) in tasks.KNOWN_OPTIONAL.items():
        if title or mission:
            put(h, 'mission', label=title, name=mission)
    for h, title in tasks.STORY_TITLES.items():
        put(h, 'mission', label=title)
    for x in robberies.LOCATIONS:
        if x[2]:
            put(x[0], 'place', label=x[2])
    for h, l in gangs.ITEM_LABELS.items():
        put(h, 'item', label=l)
    for h, t in textlabels.TEXT.items():         # IDs that are the key of their own on-screen text
        put(h, 'text', label=t)
    for h, (kind, t) in textlabels.SUFFIX_TEXT.items():    # posts, articles and accounts: text keyed by name + suffix
        put(h, kind, label=t)
    import collectibles2 as c2                    # the keyed collectible tables: hoops, flamingos, magazines, watches, ...
    for i, h in enumerate(c2.HOOPS):
        put(h, 'collectible', name='basketballhoop%d' % i)
    for i, h in enumerate(c2.AHOL, 1):
        put(h, 'collectible', name='streetartaholtrashloc%03d' % i)
    for i, h in enumerate(c2.GOLD_DOUBLOONS, 1):
        put(h, 'collectible', name='golddoubloonlocation%03d' % i)
    for prefix, table in (('pinkflamingoslocation', c2.FLAMINGOS), ('collectiblemagazine', c2.MAGAZINES), ('collectiblelibrarybook', c2.BOOKSWAPS),
                          ('watch', c2.WATCHES), ('uniquelook', c2.MAGSTYLES)):
        for suffix, h in table.items():
            put(h, 'collectible', name=prefix + suffix)
    for car, h in c2.WYMAN.items():
        put(h, 'collectible', name='wyman%svehicle' % car)
    for h, n in savekeys.KEY_NAMES.items():
        put(h, 'key', name=n)
    for h, n in savekeys.SECTION_NAMES.items():
        put(h, 'section', name=n)
    _D = d
    return d


def lookup(v):
    """-> {'kind': word, 'text': name} for an integer that is a known ID, else None."""
    if isinstance(v, bool) or not isinstance(v, int) or not (-2**31 <= v < 2**32) or -65536 < v < 65536:
        return None
    e = _table().get(v & M32)
    if not e:
        return None
    kind, label, name = e
    text = '%s (%s)' % (label, name) if label and name and label.lower() != name.lower() else (label or name)
    return {'kind': KIND_WORDS.get(kind, 'Name'), 'text': text}
