import json
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
import featurelib as fl
import money
import physique
import savedit


def sample(*, ambiguous=False):
    # Reorder both owners and script records so positional addressing cannot pass.
    owners = [physique.OWNERS['Jason'], physique.OWNERS['Lucia']]
    quals = list(physique.LEVELS)
    stats = {savedit.T_BASE: [fl.h('currentlevel'), fl.h('numlevelups')],
             savedit.T_QUAL: [fl.h(q) for q in quals], savedit.T_OWNER: owners,
             '$0x085ee24c': {savedit.K_BASE: [0] * 6 + [1], savedit.K_QUAL: [0, 1, 2] * 2 + [0],
                             savedit.K_OWNER: [0] * 3 + [1] * 3 + [0], savedit.K_VAL: [1, 0, 2, 4, 2, 1, 9]}}
    records = {}
    for who, strength, cardio, focus in [('Jason', 0, 0, 2), ('Lucia', 4, 2, 1)]:
        records[who] = {physique.MODEL: fl.h('player_' + who.lower()), '$0x2c4379f2': strength,
                        '$0x381bd0ae': cardio, '$0xd3de8c6b': focus, '$0xd8540c1f': -2.0}
    if ambiguous:
        records['duplicate'] = records['Jason'].copy()
    root, section, data = physique.ROOT
    texts = [json.dumps(x, separators=(',', ':')).encode() for x in
             ({fl.CODE: {fl.key(fl.STATS): stats}}, {root: {section: {data: records}}})]
    head = struct.pack('<4sIII', b'JSAV', 3, 2, 0) + bytes(40)
    entries = [[h, 0, 0, 0, 0] for h in (fl.STATS, physique.SECTION)]
    return money._rebuild(head, entries, texts, [b''], bytes(4), 0)


def stat(save, who, name):
    return fl.Stats(savedit.section(save, fl.STATS)).row('currentlevel', name, physique.OWNERS[who])


def records(save):
    return physique.character_blocks(savedit.section(save, physique.SECTION))


class PhysiqueLevels(unittest.TestCase):
    def test_independent_levels_and_cross_tab_stat_payload(self):
        original = sample()
        edits = [dict(stat(original, 'Jason', 'cardio'), newValue=3), dict(stat(original, 'Lucia', 'focus'), newValue=0)]
        changed, _ = savedit.apply(original, {'stats': edits})
        expected = records(original)
        expected['Jason'][1]['$0x381bd0ae'] = 3
        expected['Lucia'][1]['$0xd3de8c6b'] = 0
        self.assertEqual(records(changed), expected)
        self.assertEqual(stat(changed, 'Jason', 'cardio')['value'], 3)
        self.assertEqual(stat(changed, 'Lucia', 'focus')['value'], 0)

    def test_repair_existing_disagreement_without_changing_stats_or_counters(self):
        original = sample()
        row = stat(original, 'Jason', 'muscle')
        payload = {'stats': [dict(row, newValue=row['value'])]}
        changed, log = savedit.apply(original, payload)
        self.assertEqual(records(changed)['Jason'][1]['$0x2c4379f2'], 1)
        self.assertEqual(savedit.section(original, fl.STATS), savedit.section(changed, fl.STATS))
        self.assertEqual([e['what'] for e in log], ['physique'])
        self.assertEqual(savedit.apply(changed, payload), (changed, []))

    def test_bad_range_stale_stat_and_ambiguous_model(self):
        for ambiguous, target, old, reason in ((False, 4, 0, 'out_of_range'), (False, 2, 1, 'stale_item'),
                                                (True, 1, 0, 'physique_layout')):
            original = sample(ambiguous=ambiguous)
            row = stat(original, 'Jason', 'cardio')
            with self.subTest(reason=reason), self.assertRaisesRegex(savedit.SaveError, reason):
                savedit.apply(original, {'stats': [dict(row, value=old, newValue=target)]})
