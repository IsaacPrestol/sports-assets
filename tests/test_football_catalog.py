from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from football_catalog import build_lookup, competition_assets, normalize_name


def make_entry(**overrides):
    entry = {
        "id": "laliga",
        "name": "LaLiga",
        "aliases": ["La Liga"],
        "type": "league",
        "scope": "club",
        "continent": "europe",
        "confederation": "UEFA",
        "country": "ES",
        "logo": None,
        "collage": None,
    }
    entry.update(overrides)
    return entry


class NormalizeNameTest(unittest.TestCase):
    def test_lowercases_and_keeps_words(self):
        self.assertEqual(normalize_name("LaLiga EA Sports"), "laliga ea sports")

    def test_strips_accents(self):
        self.assertEqual(normalize_name("Primera División"), "primera division")

    def test_punctuation_and_spacing_become_single_spaces(self):
        self.assertEqual(normalize_name("  Trophée   des-Champions "), "trophee des champions")
        self.assertEqual(normalize_name("DFB-Pokal"), "dfb pokal")

    def test_only_symbols_normalizes_to_empty(self):
        self.assertEqual(normalize_name("—!!"), "")


class BuildLookupTest(unittest.TestCase):
    def test_includes_id_name_and_aliases(self):
        lookup, errors = build_lookup([make_entry(aliases=["La Liga", "Primera División"])])
        self.assertEqual(errors, [])
        self.assertEqual(
            lookup,
            {"la liga": "laliga", "laliga": "laliga", "primera division": "laliga"},
        )

    def test_keys_are_sorted(self):
        lookup, _ = build_lookup([
            make_entry(),
            make_entry(id="serie-a", name="Serie A", aliases=["Italian Serie A"], country="IT"),
        ])
        self.assertEqual(list(lookup), sorted(lookup))

    def test_repeated_name_within_same_competition_is_fine(self):
        _, errors = build_lookup([make_entry(aliases=["LaLiga", "laliga"])])
        self.assertEqual(errors, [])

    def test_collision_between_competitions_is_an_error(self):
        _, errors = build_lookup([
            make_entry(id="supercopa-de-espana", name="Supercopa de España", aliases=["Supercopa"]),
            make_entry(id="uefa-super-cup", name="UEFA Super Cup", aliases=["Supercopa"]),
        ])
        self.assertEqual(len(errors), 1)
        self.assertIn("supercopa-de-espana", errors[0])
        self.assertIn("uefa-super-cup", errors[0])

    def test_alias_that_normalizes_to_empty_is_an_error(self):
        _, errors = build_lookup([make_entry(aliases=["—"])])
        self.assertEqual(len(errors), 1)
        self.assertIn("laliga", errors[0])


class CompetitionAssetsTest(unittest.TestCase):
    def test_only_entries_with_logo(self):
        assets = competition_assets([
            make_entry(logo="football/competitions/europe/laliga.png"),
            make_entry(id="serie-a", name="Serie A", aliases=[], logo=None),
        ])
        self.assertEqual(
            assets,
            {"laliga": {"name": "LaLiga", "path": "football/competitions/europe/laliga.png"}},
        )


if __name__ == "__main__":
    unittest.main()
