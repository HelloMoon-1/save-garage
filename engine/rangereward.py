"""Experimental M306 TMR shop entry for story saves. No inventory or currency edits."""
import featurelib as fl

PAGES = (0x6df5d2cf, 0x7f587594, 0x038b7dfc, 0x84ca8078)
HASHES = fl.key('UnlockItemHashArray')
FLAGS = fl.key('UnlockItemPackedDataArray')
PAGE = '$0x56585b94'
TARGET = fl.h('weaponspec_tacrifle_marksman_adv')
PEERS = {fl.h('weaponspec_tacrifle_' + name + '_default') for name in ('marksman', 'hunting', 'carbine')}


def locate(save):
    candidates = []
    reference = set()
    existing = []
    # The game buckets these entries by the low hash bits. Use the active
    # pages and neighbouring entries in this save, never a fixed row number.
    suffix = TARGET & 0xffff
    for number, sec in enumerate(PAGES):
        data = fl.payload(save.text(sec), sec)
        keys, values = data[HASHES], data[FLAGS]
        ids, flags = keys.get('$data', []), values.get('$data', [])
        if (data[PAGE] != number or keys['$content'] != 'int_array' or values['$content'] != 'char_array'
                or len(ids) != len(flags) or len(set(ids)) != len(ids)):
            raise fl.FeatureError('range_reward_layout')
        reference.update(h for h in PEERS.intersection(ids) if flags[ids.index(h)] == 14)
        if TARGET in ids:
            idx = ids.index(TARGET)
            existing.append((sec, idx, flags[idx]))
        else:
            for idx in range(1, len(ids)):
                if (ids[idx - 1] & 0xffff) < suffix < (ids[idx] & 0xffff):
                    candidates.append((sec, idx, None))
    if len(reference) < 2:
        raise fl.FeatureError('range_reward_layout')
    matches = existing or candidates
    if len(matches) != 1 or matches[0][2] not in (None, 0, 14, 15):
        raise fl.FeatureError('range_reward_layout')
    return matches[0]


def status(data):
    try:
        _, _, value = locate(fl.Save(data))
        return 'set' if value == 15 else 'available'
    except (KeyError, TypeError, ValueError, IndexError, fl.savedit.SaveError):
        return 'unavailable'


def apply(data):
    save = fl.Save(data)
    sec, idx, old = locate(save)
    if old == 15:
        return data, []
    text = save.text(sec)
    for key, new in ((HASHES, TARGET), (FLAGS, 15)):
        start, _ = fl.walk(text, fl.CODE, fl.key(sec), key)
        if old is None:
            (begin, end), tokens = fl.typed_values(text, start)
            tokens.insert(idx, str(new).encode())
            text = fl.splice(text, begin, end, b','.join(tokens))
        elif key == FLAGS:
            text = fl.typed_set(text, start, idx, str(old).encode(), b'15')
    save.set_text(sec, text)
    result = save.build()
    if locate(fl.Save(result)) != (sec, idx, 15):
        raise fl.FeatureError('verify_failed')
    return result, [{'what': 'completion', 'label': 'Hillinger M306 TMR shop entry', 'from': old, 'to': 15}]
