import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
import player


class RelationshipEdits(unittest.TestCase):
    def edit(self, target, overrides=None):
        fields = {player.K_REL: 9, player.K_REL_LEVEL: 0, player.K_REL_LOW: 0, player.K_REL_CAP: 69,
                  player.K_REL_LOCKED: False, player.K_REL_OFF: False}
        fields.update(overrides or {})
        text = json.dumps({player.fl.CODE: {player.fl.key(player.CHAR): fields}}, separators=(',', ':')).encode()
        with patch.object(player.fl, 'Save') as factory:
            save = factory.return_value
            save.text.return_value = text
            _, log = player.apply(b'slot', {'relationship': target})
            result = save.set_text.call_args.args[1] if log else text
        return player.fl.payload(result, player.CHAR)

    def test_score_updates_level_across_each_estimated_boundary(self):
        for score, level in ((0, 0), (19, 0), (20, 1), (46, 1), (47, 2), (90, 2), (91, 3), (100, 3)):
            with self.subTest(score=score):
                data = self.edit(score, {player.K_REL_LOW: 22, player.K_REL_LEVEL: 3})
                self.assertEqual((data[player.K_REL], data[player.K_REL_LEVEL]), (score, level))
                self.assertEqual((data[player.K_REL_LOW], data[player.K_REL_CAP]), (22, 69))

    def test_legacy_presets_use_the_score_and_repair_a_stale_level(self):
        data = self.edit({'value': 69, 'level': 2}, {player.K_REL: 69, player.K_REL_LEVEL: 0})
        self.assertEqual((data[player.K_REL], data[player.K_REL_LEVEL]), (69, 2))

    def test_rejects_invalid_scores_and_respects_story_switches(self):
        for target, overrides, error in [
                (-1, {}, 'out_of_range'), (101, {}, 'out_of_range'), (True, {}, 'bad_value'),
                (42.5, {}, 'bad_value'), (69, {player.K_REL_LOCKED: True}, 'relationship_locked'),
                (69, {player.K_REL_OFF: True}, 'relationship_disabled')]:
            with self.subTest(target=target, error=error), self.assertRaisesRegex(player.fl.FeatureError, error):
                self.edit(target, overrides)
