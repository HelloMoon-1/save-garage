from collections import Counter
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
import activities2 as ranges


class RangeCard:
    def __init__(self):
        self.rows = Counter()
        for venue, _ in ranges.VENUES:
            self.rows['unlocked', 0, venue] = True
        for venue, course, tier in ranges._courses():
            for field, value in [('highestmedal', 7), ('bestscore', 101), ('recentscore', 99),
                                 ('timescompleted', 2), ('unlocked', True)]:
                self.rows[field, tier, course] = value
            for qual, owner in ((0, course), (tier, venue), (0, venue), (0, ranges.ST)):
                for medal in ('bronze', 'silver', 'gold'):
                    self.rows['shootingrange' + medal + 'medals', qual, owner] += 1
                self.rows[ranges.TOTAL_MEDALS, qual, owner] += 3

    def value(self, base, qual=0, owner=ranges.ST):
        return self.rows[base, qual, owner]

    def set(self, base, qual, new, label, owner):
        self.rows[base, qual, owner] = new


class RangeReplay(unittest.TestCase):
    def test_closed_venue_keeps_gold_calibration_from_the_played_courses(self):
        card = RangeCard()
        card.rows['unlocked', 0, 'rodgers'] = False
        info = ranges.range_access(card)
        self.assertFalse(info['venues'][1]['open'])
        self.assertIsNotNone(info['last'])

    def test_full_card_leaves_exactly_one_replay_and_preserves_other_scores(self):
        card = RangeCard()
        recipe = ranges.gold_recipe(card)
        venue, course, tier, _ = recipe[2]
        ranges.prepare_gold(ranges.Edit(card), recipe)
        info = ranges.range_access(card)
        self.assertEqual((info['recorded'], info['checklist'], info['last']), (41, 41, [venue, course, tier]))
        for v, c, t in ranges._courses():
            replay = (v, c, t) == (venue, course, tier)
            self.assertEqual(card.value('highestmedal', t, c), 0 if replay else 7)
            self.assertEqual(card.value('bestscore', t, c), 0 if replay else 101)
            self.assertEqual(card.value('recentscore', t, c), 0 if replay else 99)
            self.assertEqual(card.value('timescompleted', t, c), 2)
        before = card.rows.copy()
        ranges.prepare_gold(ranges.Edit(card), ranges.gold_recipe(card))
        self.assertEqual(card.rows, before)
        card.rows['unlocked', tier, course] = False
        self.assertTrue(ranges.range_access(card)['lastLocked'])

    def test_skip_completes_the_remaining_course_and_keeps_a_full_card(self):
        card = RangeCard()
        ranges.prepare_gold(ranges.Edit(card), ranges.gold_recipe(card))
        ranges.prepare_gold(ranges.Edit(card), ranges.gold_recipe(card), complete=True)
        self.assertEqual(ranges.range_access(card)['recorded'], 42)
        for venue, course, tier in ranges._courses():
            self.assertEqual(card.value('highestmedal', tier, course), 7)
        before = card.rows.copy()
        ranges.prepare_gold(ranges.Edit(card), ranges.gold_recipe(card), complete=True)
        self.assertEqual(card.rows, before)

    def test_inconsistent_venue_record_disables_replay(self):
        card = RangeCard()
        card.rows['shootingrangesilvermedals', 0, 'griffin'] -= 1
        self.assertIsNone(ranges.range_access(card)['last'])

    def test_reference_gold_prepares_silver_threshold_from_an_empty_card(self):
        card = RangeCard()
        for key in list(card.rows):
            if key[0] != 'unlocked':
                card.rows[key] = 0
        info = ranges.range_access(card)['ammo']['infiniteAmmo']
        self.assertEqual(info['count'], 0)
        self.assertIsNotNone(info['course'])
        ranges.prepare_gold(ranges.Edit(card), ranges.gold_recipe(card), medal='infiniteAmmo')
        updated = ranges.range_access(card)['ammo']['infiniteAmmo']
        self.assertEqual(updated['count'], 24)
        self.assertEqual(updated['course'], info['course'])
        venue, course, tier = info['course']
        self.assertEqual(card.value('highestmedal', tier, course), 0)
        self.assertEqual(card.value('shootingrangesilvermedals'), 24)
        self.assertEqual(card.value('shootingrangegoldmedals'), 24)
        self.assertEqual(sum(card.value('bestscore', t, r) > 0 for _, r, t in ranges._courses()), 24)

    def test_cheat_threshold_does_not_roll_back_an_existing_card(self):
        card = RangeCard()
        before = card.rows.copy()
        self.assertIsNone(ranges.range_access(card)['ammo']['noReload']['course'])
        with self.assertRaises(ranges.fl.FeatureError):
            ranges.prepare_gold(ranges.Edit(card), ranges.gold_recipe(card), medal='noReload')
        self.assertEqual(card.rows, before)
