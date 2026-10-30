"""Prevent losing researched domestic entrants or merging distinct local clubs."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from football_catalog import normalize_name
from football_clubs import build_club_lookup


class DomesticCoverageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clubs = json.loads((ROOT / 'data/football/clubs.json').read_text(encoding='utf-8'))['clubs']
        cls.by_id = {c['id']: c for c in cls.clubs}
        cls.coverage = json.loads((ROOT / 'data/football/domestic-coverage.json').read_text(encoding='utf-8'))

    def test_verified_entrant_lists_are_complete_and_resolve_to_clubs(self):
        expected = {'premier-league': 20, 'laliga': 20, 'serie-a': 20,
                    'bundesliga': 18, 'ligue-1': 18, 'efl-cup': 92,
                    'fa-cup': 743, 'copa-del-rey': 126, 'coppa-italia': 44, 'dfb-pokal': 64,
                    'community-shield': 2, 'supercopa-de-espana': 4,
                    'supercoppa-italiana': 2, 'dfl-supercup': 2, 'trophee-des-champions': 2}
        for competition, count in expected.items():
            entry = self.coverage['competitions'][competition]
            self.assertTrue(entry['complete'], competition)
            self.assertEqual(len(entry['club_ids']), count, competition)
            self.assertEqual(len(set(entry['club_ids'])), count)
            self.assertTrue(entry['sources'])
        for competition, entry in self.coverage['competitions'].items():
            for club_id in entry['club_ids']:
                self.assertIn(club_id, self.by_id, competition)
                self.assertEqual(self.by_id[club_id]['country'], entry['country'])
            self.assertEqual(entry['missing_logos'],
                             [i for i in entry['club_ids'] if self.by_id[i]['logo'] is None])

    def test_french_regional_coverage_does_not_claim_complete_registration(self):
        entry = self.coverage['competitions']['coupe-de-france']
        self.assertFalse(entry['complete'])
        self.assertGreaterEqual(entry['regional_fixture_clubs'], 7002)
        self.assertTrue(entry['notes'])
        self.assertTrue(entry['regional_sources'])
        ids = [c['external_ids']['fff'] for c in self.clubs if 'fff' in c.get('external_ids', {})]
        self.assertEqual(len(ids), len(set(ids)))

    def test_affixes_do_not_merge_distinct_english_clubs(self):
        lookup, errors = build_club_lookup(self.clubs)
        self.assertEqual(errors, [])
        def find(name): return lookup['GB-ENG'][normalize_name(name)]
        self.assertNotEqual(find('AFC Liverpool'), find('Liverpool FC'))
        self.assertNotEqual(find('AFC Mansfield'), find('Mansfield Town FC'))
        self.assertNotEqual(find('FC Peterborough'), find('Peterborough United FC'))

    def test_existing_provider_spellings_resolve_without_duplicate_top_clubs(self):
        lookup, errors = build_club_lookup(self.clubs)
        self.assertEqual(errors, [])
        for country, name, club_id in [('ES', 'Celta Vigo', 'celta'), ('IT', 'Como', 'como-1907'),
                                       ('IT', 'Internazionale', 'inter'),
                                       ('DE', 'FC Cologne', 'koln'), ('DE', 'Hamburg SV', 'hamburger-sv'),
                                       ('FR', 'Strasbourg', 'rc-strasbourg-alsace')]:
            self.assertEqual(lookup[country][normalize_name(name)], club_id)
        for league in ('premier-league', 'laliga', 'serie-a', 'bundesliga', 'ligue-1'):
            expected = set(self.coverage['competitions'][league]['club_ids'])
            self.assertEqual({c['id'] for c in self.clubs if c['league'] == league}, expected)

    def test_trailing_afc_names_resolve_to_existing_club_ids(self):
        lookup, errors = build_club_lookup(self.clubs)
        self.assertEqual(errors, [])
        for name, club_id in [('Leeds United AFC', 'leeds-united'), ('Newport County AFC', 'newport-county'),
                              ('Oldham Athletic AFC', 'oldham-athletic'), ('Rochdale AFC', 'rochdale'),
                              ('Wrexham AFC', 'wrexham')]:
            self.assertEqual(lookup['GB-ENG'][normalize_name(name)], club_id)


if __name__ == '__main__':
    unittest.main()
