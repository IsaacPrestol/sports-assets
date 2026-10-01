from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

from football_catalog import load_catalog, normalize_name

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from football_clubs import (
    CLUBS_FILE,
    ROSTERS_FILE,
    auto_aliases,
    build_club_lookup,
    club_assets,
    finalize_clubs,
    load_json,
    luuk_index,
    merge_clubs,
    propose,
    propose_slug,
    roster_errors,
    roster_index,
    slug_name,
    slugify,
    strip_affixes,
    unknown_folders,
    validate_clubs,
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

    def test_slug_words_contained_in_name(self):
        slugs = ["newcastle", "leicester", "gloucester-city", "west-ham", "evesham-united"]
        self.assertEqual(propose_slug("Newcastle United", slugs), ("newcastle", "partial"))
        self.assertEqual(propose_slug("Leicester City", slugs), ("leicester", "partial"))
        self.assertEqual(propose_slug("West Ham United", slugs), ("west-ham", "partial"))

    def test_partial_prefers_longest_slug(self):
        slugs = ["real", "real-betis"]
        self.assertEqual(propose_slug("Real Betis Balompié", slugs), ("real-betis", "partial"))


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

    def test_entries_carry_league_id(self):
        index = luuk_index(PATHS)
        self.assertEqual(index["Spain|Real Madrid"]["league"], "laliga")
        self.assertIsNone(index["Spain|UD Almería"]["league"])


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


LEAGUES = [{"id": "laliga", "type": "league"}, {"id": "copa-del-rey", "type": "cup"}]


def club(**overrides):
    entry = {"id": "real-madrid", "name": "Real Madrid", "aliases": [], "country": "ES",
             "league": "laliga", "logo": None}
    entry.update(overrides)
    return entry


class ValidateClubsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def png(self, rel, size=(500, 500), alpha=0):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGBA", size, (255, 0, 0, alpha)).save(path)
        return rel

    def validate(self, *clubs, mapping=None):
        return validate_clubs(self.root, {"version": 1, "clubs": list(clubs)}, LEAGUES, mapping or {})

    def test_valid(self):
        logo = self.png("football/clubs/es/real-madrid.png")
        self.assertEqual(self.validate(club(logo=logo)), ([], []))

    def test_missing_logo_is_warning(self):
        errors, warnings = self.validate(club())
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)

    def test_low_resolution_is_warning(self):
        logo = self.png("football/clubs/es/real-madrid.png", size=(139, 181))
        errors, warnings = self.validate(club(logo=logo))
        self.assertEqual(errors, [])
        self.assertTrue(any("low resolution" in w for w in warnings))

    def test_bad_structure(self):
        self.assertEqual(len(self.validate(club(country="Spain"))[0]), 1)
        self.assertEqual(len(self.validate(club(id="Real Madrid"))[0]), 1)
        entry = club()
        del entry["league"]
        self.assertEqual(len(self.validate(entry)[0]), 1)
        self.assertEqual(len(validate_clubs(self.root, {}, LEAGUES, {})[0]), 1)

    def test_league_must_be_a_league(self):
        errors, _ = self.validate(club(league="copa-del-rey"))
        self.assertTrue(any("league" in e for e in errors))

    def test_duplicate_id(self):
        errors, _ = self.validate(club(), club(name="Other"))
        self.assertTrue(any("Duplicate id" in e for e in errors))

    def test_logo_path_and_existence(self):
        errors, _ = self.validate(club(logo="football/clubs/gb-eng/real-madrid.png"))
        self.assertTrue(any("must be" in e for e in errors))
        errors, _ = self.validate(club(logo="football/clubs/es/real-madrid.png"))
        self.assertTrue(any("not found" in e for e in errors))

    def test_opaque_logo(self):
        logo = self.png("football/clubs/es/real-madrid.png", alpha=255)
        errors, _ = self.validate(club(logo=logo))
        self.assertTrue(any("transparent" in e for e in errors))

    def test_orphan_image(self):
        self.png("football/clubs/es/other.png")
        errors, _ = self.validate(club())
        self.assertTrue(any("not referenced" in e for e in errors))

    def test_alias_collision_in_country(self):
        errors, _ = self.validate(club(), club(id="other", name="Other", aliases=["Real Madrid"]))
        self.assertTrue(any("collides" in e for e in errors))

    def test_url_source_needs_https_url(self):
        for entry in ({"id": "real-madrid", "source": "url", "slug": None},
                      {"id": "real-madrid", "source": "url", "slug": None, "url": None},
                      {"id": "real-madrid", "source": "url", "slug": None, "url": "http://x/y.png"}):
            errors, _ = self.validate(club(), mapping={"Spain|Real Madrid": entry})
            self.assertTrue(any("https" in e for e in errors), entry)
        ok = {"id": "real-madrid", "source": "url", "slug": None, "url": "https://upload.wikimedia.org/x.png"}
        self.assertEqual(self.validate(club(), mapping={"Spain|Real Madrid": ok})[0], [])

    def test_mapping_id_must_exist(self):
        mapping = {"Spain|Ghost": {"id": "ghost", "source": "luukhopman", "slug": None}}
        errors, _ = self.validate(club(), mapping=mapping)
        self.assertTrue(any("ghost" in e for e in errors))


class SyncSafetyTest(unittest.TestCase):
    def test_unknown_league_and_country_folders(self):
        luuk = luuk_index(PATHS + [
            "logos/Poland - Betclic Ekstraklasa/Legia Warszawa.png",
            "history/2025-26/Atlantis - Premier/Ghost FC.png",
        ])
        problems = unknown_folders(luuk)
        self.assertTrue(any("Poland - Betclic Ekstraklasa" in p for p in problems))
        self.assertTrue(any("Atlantis" in p for p in problems))
        self.assertEqual(unknown_folders(luuk_index(PATHS)), [])

    def test_existing_club_learns_new_names_as_aliases(self):
        mapping = {key: dict(entry, id="banik") if key.startswith("Czech") else entry
                   for key, entry in MAPPING.items()}
        existing = {"id": "banik", "name": "FC Banik Ostrava", "aliases": ["Baník"],
                    "country": "CZ", "league": None, "logo": None}
        clubs, _ = merge_clubs([existing], mapping, luuk_index(PATHS))
        banik = next(c for c in clubs if c["id"] == "banik")
        self.assertEqual(banik["aliases"], ["Baník", "Banik Ostrava"])

    def test_finalize_reports_name_collisions_before_writing(self):
        existing = {"id": "other", "name": "Other", "aliases": ["Real Madrid"], "country": "ES",
                    "league": None, "logo": None}
        _, _, errors = finalize_clubs([existing], MAPPING, luuk_index(PATHS))
        self.assertTrue(any("collides" in e for e in errors))

    def test_finalize_clean(self):
        clubs, skipped, errors = finalize_clubs([], MAPPING, luuk_index(PATHS))
        self.assertEqual((len(clubs), errors), (3, []))


ROSTERS = {
    "brasileirao-serie-a": {
        "2025": ["Flamengo", "Sport Recife"],
        "2026": ["Flamengo", "Coritiba"],
    },
    "canadian-premier-league": {
        "2025": ["York United"],
        "2026": ["Inter Toronto FC"],
    },
    "mls": {"2026": ["Toronto FC"]},
}
COMPETITIONS = [
    {"id": "brasileirao-serie-a", "type": "league", "country": "BR"},
    {"id": "canadian-premier-league", "type": "league", "country": "CA"},
    {"id": "mls", "type": "league", "country": "US"},
    {"id": "copa-libertadores", "type": "international", "country": None},
]


class RosterIndexTest(unittest.TestCase):
    def setUp(self):
        self.index = roster_index(ROSTERS, COMPETITIONS)

    def test_current_club(self):
        self.assertEqual(self.index["Brazil|Flamengo"], {
            "country_folder": "Brazil", "name": "Flamengo", "league_folder": None,
            "league": "brasileirao-serie-a", "latest_season": "2026", "latest_path": None,
        })

    def test_relegated_club_has_no_league(self):
        club = self.index["Brazil|Sport Recife"]
        self.assertIsNone(club["league"])
        self.assertEqual(club["latest_season"], "2025")

    def test_country_comes_from_the_league(self):
        self.assertEqual(self.index["United States|Toronto FC"]["country_folder"], "United States")
        self.assertEqual(len(self.index), 6)

    def test_merge_uses_roster_league_and_country(self):
        mapping = {
            "Brazil|Flamengo": {"id": "flamengo", "source": "football-logos", "slug": "flamengo"},
            "Brazil|Sport Recife": {"id": "sport-recife", "source": "url", "slug": None,
                                    "url": "https://example.org/sport.png"},
        }
        clubs, _ = merge_clubs([], mapping, self.index)
        by_id = {c["id"]: c for c in clubs}
        self.assertEqual(by_id["flamengo"]["league"], "brasileirao-serie-a")
        self.assertEqual(by_id["flamengo"]["country"], "BR")
        self.assertEqual(by_id["flamengo"]["logo"], "football/clubs/br/flamengo.png")
        self.assertIsNone(by_id["sport-recife"]["league"])

    def test_renamed_club_is_one_club(self):
        mapping = {
            "Canada|York United": {"id": "inter-toronto", "source": "football-logos", "slug": "inter-toronto-fc"},
            "Canada|Inter Toronto FC": {"id": "inter-toronto", "source": "football-logos", "slug": "inter-toronto-fc"},
        }
        clubs, _ = merge_clubs([], mapping, self.index)
        self.assertEqual(len(clubs), 1)
        self.assertEqual(clubs[0]["name"], "Inter Toronto FC")
        self.assertIn("York United", clubs[0]["aliases"])
        self.assertEqual(clubs[0]["league"], "canadian-premier-league")

    def test_propose_without_slug_asks_for_url(self):
        proposals = propose(self.index, {}, {"Brazil": ["flamengo"], "Canada": [], "United States": []}, {})
        self.assertEqual(proposals["Brazil|Flamengo"]["source"], "football-logos")
        self.assertEqual(proposals["United States|Toronto FC"],
                         {"id": "toronto", "source": "url", "slug": None, "match": "none"})


class RosterErrorsTest(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(roster_errors(ROSTERS, COMPETITIONS), [])

    def test_not_an_object(self):
        self.assertEqual(len(roster_errors([], COMPETITIONS)), 1)

    def test_unknown_non_league_or_countryless_league(self):
        competitions = COMPETITIONS + [{"id": "j-league", "type": "league", "country": "JP"}]
        rosters = {"nope": {"2026": ["A"]}, "copa-libertadores": {"2026": ["A"]}, "j-league": {"2026": ["A"]}}
        self.assertEqual(len(roster_errors(rosters, competitions)), 3)

    def test_season_format(self):
        errors = roster_errors({"mls": {"2025-26": ["A"], "2026": ["B"]}}, COMPETITIONS)
        self.assertTrue(any("same format" in e for e in errors))
        errors = roster_errors({"mls": {"26": ["A"]}}, COMPETITIONS)
        self.assertTrue(any("YYYY" in e for e in errors))

    def test_empty_season(self):
        self.assertEqual(len(roster_errors({"mls": {"2026": []}}, COMPETITIONS)), 1)
        self.assertEqual(len(roster_errors({"mls": {}}, COMPETITIONS)), 1)

    def test_club_names(self):
        errors = roster_errors({"mls": {"2026": ["Club Nacional", " B", "", "club nacional"]}}, COMPETITIONS)
        self.assertEqual(len(errors), 3)
        self.assertTrue(any("repeated" in e for e in errors))
        self.assertTrue(any("spaces" in e for e in errors))
        self.assertTrue(any("empty" in e for e in errors))


class RealRostersTest(unittest.TestCase):
    def test_every_american_league_has_a_valid_roster_up_to_2026(self):
        competitions = load_catalog()["competitions"]
        rosters = load_json(ROSTERS_FILE, {})
        self.assertEqual(roster_errors(rosters, competitions), [])
        american = {c["id"] for c in competitions
                    if c["type"] == "league" and c["continent"] in ("south-america", "north-america")}
        self.assertEqual(set(rosters), american)
        for league, seasons in rosters.items():
            self.assertGreaterEqual(max(seasons), "2026", league)
            self.assertLessEqual(min(seasons), "2022-23" if len(min(seasons)) == 7 else "2022", league)


class RealClubsCatalogTest(unittest.TestCase):
    def setUp(self):
        lookup, errors = build_club_lookup(load_json(CLUBS_FILE, {"clubs": []})["clubs"])
        self.assertEqual(errors, [])
        self.lookup = lookup

    def find(self, country, name):
        return self.lookup.get(country, {}).get(normalize_name(name))

    def test_ambiguous_names_do_not_point_to_the_wrong_club(self):
        self.assertNotEqual(self.find("ES", "Deportivo"), "alaves")
        self.assertNotEqual(self.find("FR", "Paris"), "paris-fc")

    def test_american_clubs_resolve(self):
        self.assertEqual(self.find("BR", "Flamengo"), "flamengo")
        self.assertEqual(self.find("AR", "Boca Juniors"), "boca-juniors")
        self.assertEqual(self.find("US", "Toronto FC"), "toronto-fc")
        self.assertEqual(self.find("MX", "Club América"), "america")
        self.assertEqual(self.find("CA", "York United"), "inter-toronto-fc")
        self.assertIsNone(self.find("CA", "Toronto FC"))

    def test_native_spellings_resolve(self):
        self.assertEqual(self.find("PL", "Wisła Kraków"), "wisla-krakow")
        self.assertEqual(self.find("DK", "Brøndby IF"), "brondby")
        self.assertEqual(self.find("TR", "Kasımpaşa"), "kasimpasa")


if __name__ == "__main__":
    unittest.main()
