from pathlib import Path
import copy
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
import io

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class BaseballCatalogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.competitions = {'version': 1, 'competitions': [
            {'id': 'mlb', 'name': 'Major League Baseball', 'aliases': ['MLB'],
             'type': 'league', 'scope': 'club', 'continent': 'north-america',
             'country': None, 'logo': 'baseball/competitions/north-america/mlb.png'}]}
        self.teams = {'version': 1, 'teams': [
            {'id': 'toronto-blue-jays', 'name': 'Toronto Blue Jays', 'aliases': ['Blue Jays'],
             'abbreviation': 'TOR', 'mlb_id': 141, 'country': 'CA', 'league': 'mlb',
             'division': 'AL East', 'logo': 'baseball/teams/ca/toronto-blue-jays.png'}]}
        for rel in [self.competitions['competitions'][0]['logo'], self.teams['teams'][0]['logo']]:
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            image = Image.new('RGBA', (10, 10), (255, 0, 0, 255))
            image.putpixel((0, 0), (0, 0, 0, 0))
            image.save(path)

    def validate(self):
        from baseball_catalog import validate_baseball
        return validate_baseball(self.root, self.competitions, self.teams)

    def test_valid_catalog_and_alias_resolution(self):
        from baseball_catalog import build_team_lookup
        self.assertEqual(self.validate(), ([], []))
        lookup, errors = build_team_lookup(self.teams['teams'])
        self.assertEqual(errors, [])
        self.assertEqual(lookup['mlb']['tor'], 'toronto-blue-jays')
        self.assertEqual(lookup['mlb']['blue jays'], 'toronto-blue-jays')

    def test_rejects_ambiguous_alias_within_league(self):
        other = dict(self.teams['teams'][0], id='other', name='Other', mlb_id=1)
        self.teams['teams'].append(other)
        self.assertTrue(any('collides' in e for e in self.validate()[0]))

    def test_rejects_missing_wrong_opaque_and_oversized_logo(self):
        path = self.root / self.teams['teams'][0]['logo']
        path.unlink()
        self.assertTrue(any('not found' in e for e in self.validate()[0]))
        Image.new('RGB', (10, 10), 'white').save(path)
        self.assertTrue(any('transparent' in e for e in self.validate()[0]))
        Image.new('RGBA', (1025, 2), (0, 0, 0, 0)).save(path)
        self.assertTrue(any('1024' in e for e in self.validate()[0]))
        self.teams['teams'][0]['logo'] = 'baseball/teams/us/toronto-blue-jays.png'
        self.assertTrue(any('must be' in e for e in self.validate()[0]))

    def test_rejects_unknown_league_duplicate_id_and_orphan(self):
        self.teams['teams'][0]['league'] = 'unknown'
        self.assertTrue(any('league' in e for e in self.validate()[0]))
        self.teams['teams'][0]['league'] = 'mlb'
        self.teams['teams'].append(copy.deepcopy(self.teams['teams'][0]))
        self.assertTrue(any('Duplicate' in e for e in self.validate()[0]))
        Image.new('RGBA', (2, 2)).save(self.root / 'baseball/teams/ca/orphan.png')
        self.assertTrue(any('not referenced' in e for e in self.validate()[0]))

    def test_malformed_data_reports_errors(self):
        self.teams['teams'][0]['aliases'] = None
        self.assertTrue(self.validate()[0])

    def test_sync_rejects_wrong_path_before_downloading(self):
        import sync_mlb
        self.teams['teams'][0]['logo'] = 'baseball/teams/us/toronto-blue-jays.png'
        with patch.object(sync_mlb, 'ROOT', self.root), \
             patch.object(sync_mlb, 'load_baseball', return_value=(self.competitions, self.teams)), \
             patch.object(sync_mlb, 'urlopen', side_effect=AssertionError('network must not run')), \
             patch.object(sys, 'argv', ['sync_mlb.py']), redirect_stdout(io.StringIO()):
            self.assertEqual(sync_mlb.main(), 1)
        self.assertFalse((self.root / 'data/sources.json').exists())


if __name__ == '__main__':
    unittest.main()
