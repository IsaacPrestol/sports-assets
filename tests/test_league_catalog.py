"""Guard catalog resolution and rejection of broken CDN entries."""
from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class LeagueCatalogTest(unittest.TestCase):
    def setUp(self):
        from league_catalog import LEAGUES
        config_patch = patch.dict(LEAGUES['nba'], {'count': 1})
        config_patch.start()
        self.addCleanup(config_patch.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.competitions = {'version': 1, 'competitions': [
            {'id': 'nba', 'name': 'National Basketball Association', 'aliases': ['NBA'],
             'type': 'league', 'scope': 'club', 'continent': 'north-america', 'country': None,
             'logo': 'basketball/competitions/north-america/nba.png'}]}
        self.teams = {'version': 1, 'teams': [
            {'id': 'toronto-raptors', 'name': 'Toronto Raptors', 'aliases': ['Raptors'],
             'abbreviation': 'TOR', 'espn_id': 28, 'country': 'CA', 'league': 'nba',
             'conference': 'Eastern', 'division': 'Atlantic',
             'logo': 'basketball/teams/ca/toronto-raptors.png'}]}
        for e in self.competitions['competitions'] + self.teams['teams']:
            self.png(e['logo'])

    def png(self, relative, size=(10, 10), color=(255, 0, 0, 255)):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new('RGBA', size, color)
        image.putpixel((0, 0), (0, 0, 0, 0))
        image.save(path)
        return path

    def validate(self):
        from league_catalog import validate_league
        return validate_league(self.root, 'nba', self.competitions, self.teams)

    def test_names_abbreviations_and_aliases_resolve_within_league(self):
        from league_catalog import build_team_lookup
        self.assertEqual(self.validate(), ([], []))
        lookup, errors = build_team_lookup(self.teams['teams'])
        self.assertEqual(errors, [])
        self.assertEqual(lookup['nba']['tor'], 'toronto-raptors')
        self.assertEqual(lookup['nba']['raptors'], 'toronto-raptors')

    def test_ambiguous_names_are_rejected(self):
        self.teams['teams'].append(dict(self.teams['teams'][0], id='other', espn_id=2))
        self.assertTrue(any('collides' in e for e in self.validate()[0]))

    def test_invalid_fields_report_errors_instead_of_crashing(self):
        for field, value in [('aliases', None), ('espn_id', True), ('league', []), ('country', 1), ('id', '../escape')]:
            original = copy.deepcopy(self.teams)
            self.teams['teams'][0][field] = value
            self.assertTrue(self.validate()[0], field)
            self.teams = original

    def test_wrong_path_league_and_conference_division_are_rejected(self):
        for field, value, fragment in [('logo', '../escape.png', 'must be'), ('league', 'nhl', 'league'),
                                       ('conference', 'Western', 'division')]:
            original = copy.deepcopy(self.teams)
            self.teams['teams'][0][field] = value
            self.assertTrue(any(fragment in e for e in self.validate()[0]), field)
            self.teams = original

    def test_missing_opaque_empty_and_oversized_images_are_rejected(self):
        path = self.root / self.teams['teams'][0]['logo']
        path.unlink()
        self.assertTrue(any('not found' in e for e in self.validate()[0]))
        Image.new('RGB', (10, 10), 'white').save(path)
        self.assertTrue(any('transparent' in e for e in self.validate()[0]))
        Image.new('RGBA', (10, 10)).save(path)
        self.assertTrue(any('visible' in e for e in self.validate()[0]))
        self.png(self.teams['teams'][0]['logo'], (1025, 2))
        self.assertTrue(any('1024' in e for e in self.validate()[0]))

    def test_duplicate_ids_and_orphan_images_are_rejected(self):
        self.teams['teams'].append(copy.deepcopy(self.teams['teams'][0]))
        self.png('basketball/teams/us/orphan.png')
        errors = self.validate()[0]
        self.assertTrue(any('Duplicate' in e for e in errors))
        self.assertTrue(any('not referenced' in e for e in errors))

    def test_sync_bad_path_does_not_download_or_write(self):
        import sync_league
        self.teams['teams'][0]['logo'] = '../escape.png'
        with patch.object(sync_league, 'ROOT', self.root), \
             patch.object(sync_league, 'load_league', return_value=(self.competitions, self.teams)), \
             patch.object(sync_league, 'urlopen', side_effect=AssertionError('unexpected download')), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(sync_league.sync('nba'), 1)
        self.assertFalse((self.root / 'data/sources.json').exists())

    def test_sync_normalizes_download_updates_source_and_skips_existing(self):
        import sync_league
        path = self.root / self.teams['teams'][0]['logo']
        path.unlink()
        sources_path = self.root / 'data/sources.json'
        sources_path.parent.mkdir(parents=True)
        relative = self.teams['teams'][0]['logo']
        sources_path.write_text(json.dumps({
            relative: {'url': 'https://example.org/team.png'},
            self.competitions['competitions'][0]['logo']: {'url': 'https://example.org/league.png'},
        }))
        image = Image.new('RGBA', (20, 10))
        image.paste((255, 0, 0, 255), (4, 2, 16, 8))
        image.putpixel((4, 2), (0, 0, 0, 0))
        content = io.BytesIO()
        image.save(content, 'PNG')
        log = io.StringIO()
        with patch.object(sync_league, 'ROOT', self.root), \
             patch.object(sync_league, 'load_league', return_value=(self.competitions, self.teams)), \
             patch.object(sync_league, 'urlopen', side_effect=lambda *a, **kw: io.BytesIO(content.getvalue())), \
             patch.object(sync_league.subprocess, 'run'), redirect_stdout(log):
            self.assertEqual(sync_league.sync('nba'), 0, log.getvalue())
        with Image.open(path) as result:
            self.assertEqual(result.size, (12, 6))
        self.assertRegex(json.loads(sources_path.read_text())[relative]['retrieved'], r'^\d{4}-\d{2}-\d{2}$')
        before = path.read_bytes(), sources_path.read_bytes()
        with patch.object(sync_league, 'ROOT', self.root), \
             patch.object(sync_league, 'load_league', return_value=(self.competitions, self.teams)), \
             patch.object(sync_league, 'urlopen', side_effect=AssertionError('existing logo downloaded')), \
             patch.object(sync_league.subprocess, 'run'), redirect_stdout(io.StringIO()):
            self.assertEqual(sync_league.sync('nba'), 0)
        self.assertEqual((path.read_bytes(), sources_path.read_bytes()), before)
        Image.new('RGB', (10, 10), 'white').save(path)
        with patch.object(sync_league, 'ROOT', self.root), \
             patch.object(sync_league, 'load_league', return_value=(self.competitions, self.teams)), \
             patch.object(sync_league, 'urlopen', side_effect=lambda *a, **kw: io.BytesIO(content.getvalue())), \
             patch.object(sync_league.subprocess, 'run'), redirect_stdout(io.StringIO()):
            self.assertEqual(sync_league.sync('nba', force=True), 0)
        with Image.open(path) as result:
            self.assertEqual(result.size, (12, 6))


class RealLeagueCatalogTest(unittest.TestCase):
    def test_incomplete_league_is_rejected(self):
        from league_catalog import load_league, validate_league
        competitions, teams = load_league('nhl')
        teams['teams'].pop()
        with tempfile.TemporaryDirectory() as directory:
            errors, _ = validate_league(Path(directory), 'nhl', competitions, teams)
        self.assertTrue(any('team count' in error for error in errors))

    def test_current_team_coverage_and_common_name_resolution(self):
        from league_catalog import load_league, build_team_lookup
        for league, count, queries in [
            ('nba', 30, {'GSW': 'golden-state-warriors', 'Los Angeles Clippers': 'los-angeles-clippers',
                         'TOR': 'toronto-raptors'}),
            ('nhl', 32, {'Utah Hockey Club': 'utah-mammoth', 'Montréal Canadiens': 'montreal-canadiens',
                         'Jets': 'winnipeg-jets'}),
            ('nfl', 32, {'Jets': 'new-york-jets', 'Chiefs': 'kansas-city-chiefs',
                         'Washington Football Team': 'washington-commanders'}),
        ]:
            from football_catalog import normalize_name
            competitions, teams = load_league(league)
            self.assertEqual(len(competitions['competitions']), 1)
            self.assertEqual(len(teams['teams']), count)
            lookup, errors = build_team_lookup(teams['teams'])
            self.assertEqual(errors, [])
            for name, team_id in queries.items():
                self.assertEqual(lookup[league][normalize_name(name)], team_id)


if __name__ == '__main__':
    unittest.main()
