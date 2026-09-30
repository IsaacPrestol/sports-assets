from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from football_clubs import (
    auto_aliases,
    build_club_lookup,
    club_assets,
    luuk_index,
    merge_clubs,
    propose,
    propose_slug,
    slug_name,
    slugify,
    strip_affixes,
)


class NamesTest(unittest.TestCase):
    def test_strip_affixes(self):
        self.assertEqual(strip_affixes("Arsenal FC"), "arsenal")
        self.assertEqual(strip_affixes("FC Banik Ostrava"), "banik ostrava")
        self.assertEqual(strip_affixes("1. FC Köln"), "koln")

    def test_strip_affixes_keeps_name_made_only_of_affixes(self):
        self.assertEqual(strip_affixes("AC"), "ac")

    def test_slugify_and_slug_name(self):
        self.assertEqual(slugify("Atlético de Madrid"), "atletico-de-madrid")
        self.assertEqual(slug_name("real-madrid"), "Real Madrid")


class ProposeSlugTest(unittest.TestCase):
    SLUGS = ["arsenal", "aston-villa", "real-madrid", "salzburg"]

    def test_exact_after_stripping_affixes(self):
        self.assertEqual(propose_slug("Arsenal FC", self.SLUGS), ("arsenal", "exact"))

    def test_fuzzy(self):
        self.assertEqual(propose_slug("Aston Vila", self.SLUGS), ("aston-villa", "fuzzy"))

    def test_none(self):
        self.assertEqual(propose_slug("Kecskeméti TE", self.SLUGS), (None, "none"))


class AutoAliasesTest(unittest.TestCase):
    def test_collects_names_slug_and_stripped_forms(self):
        aliases = auto_aliases("Arsenal FC", ["Arsenal FC"], "arsenal")
        self.assertEqual(aliases, ["Arsenal"])

    def test_history_names_and_stripped_variants(self):
        aliases = auto_aliases(
            "FC Banik Ostrava", ["Banik Ostrava", "FC Banik Ostrava"], None,
        )
        self.assertEqual(aliases, ["Banik Ostrava"])

    def test_excludes_duplicates_of_name(self):
        self.assertEqual(auto_aliases("Real Madrid", ["Real Madrid"], "real-madrid"), [])


PATHS = [
    "README.md",
    "logos/Spain - LaLiga/Real Madrid.png",
    "history/2024-25/Spain - LaLiga/Real Madrid.png",
    "history/2023-24/Spain - LaLiga/UD Almería.png",
    "history/2024-25/Czech Republic - Chance Liga/Banik Ostrava.png",
    "history/2025-26/Czech Republic - Chance Liga/FC Banik Ostrava.png",
]


class LuukIndexTest(unittest.TestCase):
    def test_current_club(self):
        club = luuk_index(PATHS)["Spain|Real Madrid"]
        self.assertEqual(club["league_folder"], "Spain - LaLiga")
        self.assertEqual(club["latest_path"], "logos/Spain - LaLiga/Real Madrid.png")

    def test_history_only_club(self):
        club = luuk_index(PATHS)["Spain|UD Almería"]
        self.assertIsNone(club["league_folder"])
        self.assertEqual(club["latest_path"], "history/2023-24/Spain - LaLiga/UD Almería.png")

    def test_ignores_non_logo_paths(self):
        self.assertEqual(len(luuk_index(PATHS)), 4)


class ProposeTest(unittest.TestCase):
    def setUp(self):
        self.luuk = luuk_index(PATHS)
        self.fl = {"Spain": ["real-madrid", "almeria"], "Czech Republic": []}

    def test_matches_and_ids(self):
        proposals = propose(self.luuk, {}, self.fl, {})
        self.assertEqual(proposals["Spain|Real Madrid"],
                         {"id": "real-madrid", "source": "football-logos", "slug": "real-madrid", "match": "exact"})
        self.assertEqual(proposals["Spain|UD Almería"]["id"], "almeria")

    def test_name_variants_share_one_id(self):
        proposals = propose(self.luuk, {}, self.fl, {})
        self.assertEqual(proposals["Czech Republic|Banik Ostrava"]["id"], "banik-ostrava")
        self.assertEqual(proposals["Czech Republic|FC Banik Ostrava"]["id"], "banik-ostrava")
        self.assertEqual(proposals["Czech Republic|Banik Ostrava"]["source"], "luukhopman")

    def test_skips_mapped_keys(self):
        mapping = {"Spain|Real Madrid": {"id": "real-madrid", "source": "football-logos", "slug": "real-madrid"}}
        self.assertNotIn("Spain|Real Madrid", propose(self.luuk, mapping, self.fl, {}))

    def test_same_slug_in_other_country_gets_suffix(self):
        proposals = propose(self.luuk, {}, self.fl, {"real-madrid": "GB-ENG"})
        self.assertEqual(proposals["Spain|Real Madrid"]["id"], "real-madrid-es")

    def test_existing_id_in_same_country_is_reused(self):
        proposals = propose(self.luuk, {}, self.fl, {"real-madrid": "ES"})
        self.assertEqual(proposals["Spain|Real Madrid"]["id"], "real-madrid")


MAPPING = {
    "Spain|Real Madrid": {"id": "real-madrid", "source": "football-logos", "slug": "real-madrid"},
    "Spain|UD Almería": {"id": "ud-almeria", "source": "football-logos", "slug": "almeria"},
    "Czech Republic|Banik Ostrava": {"id": "banik-ostrava", "source": "luukhopman", "slug": None},
    "Czech Republic|FC Banik Ostrava": {"id": "banik-ostrava", "source": "luukhopman", "slug": None},
}


class MergeClubsTest(unittest.TestCase):
    def setUp(self):
        self.luuk = luuk_index(PATHS)

    def merged(self, existing=(), missing=frozenset()):
        clubs, skipped = merge_clubs(list(existing), MAPPING, self.luuk, missing)
        return {c["id"]: c for c in clubs}, skipped

    def test_new_current_club(self):
        clubs, _ = self.merged()
        self.assertEqual(clubs["real-madrid"], {
            "id": "real-madrid", "name": "Real Madrid", "aliases": [], "country": "ES",
            "league": "laliga", "logo": "football/clubs/es/real-madrid.png",
        })

    def test_history_only_club_has_no_league(self):
        clubs, _ = self.merged()
        self.assertIsNone(clubs["ud-almeria"]["league"])
        self.assertEqual(clubs["ud-almeria"]["aliases"], ["Almeria"])

    def test_name_variants_become_one_club_named_after_latest(self):
        clubs, _ = self.merged()
        self.assertEqual(clubs["banik-ostrava"]["name"], "FC Banik Ostrava")
        self.assertEqual(clubs["banik-ostrava"]["aliases"], ["Banik Ostrava"])
        self.assertEqual(len(clubs), 3)

    def test_existing_club_keeps_manual_fields_and_updates_league(self):
        existing = {"id": "real-madrid", "name": "Real Madrid CF", "aliases": ["Los Blancos"],
                    "country": "ES", "league": None, "logo": None}
        clubs, _ = self.merged([existing])
        self.assertEqual(clubs["real-madrid"]["name"], "Real Madrid CF")
        self.assertEqual(clubs["real-madrid"]["aliases"], ["Los Blancos"])
        self.assertEqual(clubs["real-madrid"]["league"], "laliga")
        self.assertEqual(clubs["real-madrid"]["logo"], "football/clubs/es/real-madrid.png")

    def test_relegated_existing_club_loses_league_only(self):
        existing = {"id": "ud-almeria", "name": "UD Almería", "aliases": ["Almeria"],
                    "country": "ES", "league": "laliga", "logo": "football/clubs/es/ud-almeria.png"}
        clubs, _ = self.merged([existing])
        self.assertIsNone(clubs["ud-almeria"]["league"])
        self.assertEqual(clubs["ud-almeria"]["aliases"], ["Almeria"])

    def test_missing_logo(self):
        clubs, _ = self.merged(missing={"ud-almeria"})
        self.assertIsNone(clubs["ud-almeria"]["logo"])

    def test_colliding_auto_alias_is_dropped_and_reported(self):
        existing = {"id": "other", "name": "Almeria", "aliases": [], "country": "ES",
                    "league": None, "logo": None}
        clubs, skipped = self.merged([existing])
        self.assertNotIn("Almeria", clubs["ud-almeria"]["aliases"])
        self.assertTrue(any("ud-almeria" in s and "other" in s for s in skipped))
        _, errors = build_club_lookup(list(clubs.values()))
        self.assertEqual(errors, [])

    def test_sorted_by_country_then_id(self):
        clubs, _ = merge_clubs([], MAPPING, self.luuk)
        self.assertEqual([c["id"] for c in clubs], ["banik-ostrava", "real-madrid", "ud-almeria"])


class ClubLookupTest(unittest.TestCase):
    def test_lookup_is_per_country(self):
        clubs = [
            {"id": "sporting-cp", "name": "Sporting CP", "aliases": ["Sporting"], "country": "PT", "league": None, "logo": None},
            {"id": "sporting-gijon", "name": "Sporting Gijón", "aliases": ["Sporting"], "country": "ES", "league": None, "logo": None},
        ]
        lookup, errors = build_club_lookup(clubs)
        self.assertEqual(errors, [])
        self.assertEqual(lookup["PT"]["sporting"], "sporting-cp")
        self.assertEqual(lookup["ES"]["sporting"], "sporting-gijon")
        self.assertEqual(list(lookup), ["ES", "PT"])

    def test_collision_within_country(self):
        clubs = [
            {"id": "a", "name": "Dinamo", "aliases": [], "country": "RO", "league": None, "logo": None},
            {"id": "b", "name": "Other", "aliases": ["Dinamo"], "country": "RO", "league": None, "logo": None},
        ]
        _, errors = build_club_lookup(clubs)
        self.assertEqual(len(errors), 1)

    def test_club_assets(self):
        clubs = [
            {"id": "a", "name": "A", "aliases": [], "country": "ES", "league": None, "logo": "football/clubs/es/a.png"},
            {"id": "b", "name": "B", "aliases": [], "country": "ES", "league": None, "logo": None},
        ]
        self.assertEqual(club_assets(clubs), {"a": {"name": "A", "path": "football/clubs/es/a.png"}})


if __name__ == "__main__":
    unittest.main()
