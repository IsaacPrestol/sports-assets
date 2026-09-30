from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from football_catalog import (
    build_lookup,
    competition_assets,
    has_alpha,
    load_catalog,
    normalize_name,
    validate_catalog,
)


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

    def test_transliterates_letters_without_decomposition(self):
        self.assertEqual(normalize_name("Wisła Kraków"), "wisla krakow")
        self.assertEqual(normalize_name("Brøndby"), "brondby")
        self.assertEqual(normalize_name("FC Nordsjælland"), "fc nordsjaelland")
        self.assertEqual(normalize_name("Kasımpaşa"), "kasimpasa")
        self.assertEqual(normalize_name("Đakovo Straße Œuvre"), "dakovo strasse oeuvre")

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


def save_png(root: Path, relative: str, mode: str = "RGBA", **save_args) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new(mode, (8, 8)).save(path, **save_args)
    return path


LOGO = "football/competitions/europe/laliga.png"
COLLAGE = "football/collages/laliga.png"


class HasAlphaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_rgba_and_la_have_alpha(self):
        self.assertTrue(has_alpha(save_png(self.root, "a.png", "RGBA")))
        self.assertTrue(has_alpha(save_png(self.root, "b.png", "LA")))

    def test_palette_with_transparency_has_alpha(self):
        self.assertTrue(has_alpha(save_png(self.root, "c.png", "P", transparency=0)))

    def test_fully_opaque_rgba_has_no_transparency(self):
        path = self.root / "opaque.png"
        Image.new("RGBA", (8, 8), (255, 255, 255, 255)).save(path)
        self.assertFalse(has_alpha(path))

    def test_palette_with_unused_transparency_key_has_no_transparency(self):
        path = self.root / "unused-key.png"
        Image.new("P", (8, 8), 1).save(path, transparency=0)
        self.assertFalse(has_alpha(path))

    def test_rgb_has_no_alpha(self):
        self.assertFalse(has_alpha(save_png(self.root, "d.png", "RGB")))

    def test_non_image_has_no_alpha(self):
        path = self.root / "e.png"
        path.write_text("not an image")
        self.assertFalse(has_alpha(path))


class ValidateCatalogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def validate(self, *entries):
        return validate_catalog(self.root, {"version": 1, "competitions": list(entries)})

    def test_valid_entry_with_logo_and_collage(self):
        save_png(self.root, LOGO)
        save_png(self.root, COLLAGE, "RGB")
        errors, warnings = self.validate(make_entry(logo=LOGO, collage=COLLAGE))
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_missing_logo_is_only_a_warning(self):
        errors, warnings = self.validate(make_entry())
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)
        self.assertIn("laliga", warnings[0])

    def test_catalog_without_competitions_list(self):
        errors, _ = validate_catalog(self.root, {"version": 1})
        self.assertEqual(len(errors), 1)
        errors, _ = validate_catalog(self.root, [])
        self.assertEqual(len(errors), 1)

    def test_missing_field(self):
        entry = make_entry()
        del entry["confederation"]
        errors, _ = self.validate(entry)
        self.assertEqual(len(errors), 1)
        self.assertIn("confederation", errors[0])

    def test_invalid_enum_values(self):
        errors, _ = self.validate(make_entry(continent="europa", type=["league"]))
        self.assertEqual(len(errors), 2)

    def test_invalid_id(self):
        errors, _ = self.validate(make_entry(id="La Liga"))
        self.assertTrue(any("Invalid id" in e for e in errors))

    def test_duplicate_id(self):
        errors, _ = self.validate(make_entry(), make_entry(name="La Liga 2", aliases=[]))
        self.assertTrue(any("Duplicate id: 'laliga'" in e for e in errors))

    def test_logo_in_wrong_continent_folder(self):
        wrong = "football/competitions/world/laliga.png"
        save_png(self.root, wrong)
        errors, _ = self.validate(make_entry(logo=wrong))
        self.assertTrue(any("must be" in e for e in errors))

    def test_logo_file_missing(self):
        errors, _ = self.validate(make_entry(logo=LOGO))
        self.assertTrue(any("not found" in e for e in errors))

    def test_logo_without_alpha(self):
        save_png(self.root, LOGO, "RGB")
        errors, _ = self.validate(make_entry(logo=LOGO))
        self.assertTrue(any("alpha" in e for e in errors))

    def test_la_logo_is_accepted(self):
        save_png(self.root, LOGO, "LA")
        errors, _ = self.validate(make_entry(logo=LOGO))
        self.assertEqual(errors, [])

    def test_collage_file_missing(self):
        errors, _ = self.validate(make_entry(collage=COLLAGE))
        self.assertTrue(any("not found" in e for e in errors))

    def test_unreferenced_image_is_an_error(self):
        save_png(self.root, COLLAGE, "RGB")
        errors, _ = self.validate(make_entry(collage=None))
        self.assertTrue(any("not referenced" in e and COLLAGE in e for e in errors))

    def test_image_outside_continent_folder_is_an_error(self):
        save_png(self.root, "football/competitions/laliga.png")
        errors, _ = self.validate(make_entry())
        self.assertTrue(any("outside a continent folder" in e for e in errors))

    def test_hidden_files_are_ignored(self):
        (self.root / "football/competitions").mkdir(parents=True)
        (self.root / "football/competitions/.gitkeep").write_text("")
        errors, _ = self.validate(make_entry())
        self.assertEqual(errors, [])

    def test_alias_collision_is_reported(self):
        errors, _ = self.validate(
            make_entry(aliases=["Supercopa"]),
            make_entry(id="uefa-super-cup", name="UEFA Super Cup", aliases=["Supercopa"],
                       type="super-cup", country=None),
        )
        self.assertTrue(any("collides" in e for e in errors))


class RealCatalogTest(unittest.TestCase):
    # Names used by more than one real competition; as aliases they would send
    # another country's league to the wrong logo.
    GENERIC_ALIASES = {
        "primera division",
        "liga profesional",
        "league cup",
        "nations league",
        "liga de naciones",
        "superliga",
        "super league",
        "premier liga",
        "pro league",
    }

    AMERICAN_LEAGUES = {
        "brasileirao-serie-a": "BR", "liga-profesional-argentina": "AR",
        "uruguayan-primera-division": "UY", "colombian-primera-a": "CO",
        "chilean-primera-division": "CL", "paraguayan-primera-division": "PY",
        "peruvian-liga-1": "PE", "ecuadorian-serie-a": "EC",
        "bolivian-primera-division": "BO", "venezuelan-primera-division": "VE",
        "liga-mx": "MX", "mls": "US", "canadian-premier-league": "CA",
        "costa-rican-primera-division": "CR", "guatemalan-liga-nacional": "GT",
        "panamanian-football-league": "PA",
    }

    def test_american_leagues_have_country_and_logo(self):
        by_id = {c["id"]: c for c in load_catalog()["competitions"]}
        for league_id, country in self.AMERICAN_LEAGUES.items():
            competition = by_id.get(league_id)
            self.assertIsNotNone(competition, league_id)
            self.assertEqual((competition["type"], competition["country"]), ("league", country), league_id)
            self.assertIsNotNone(competition["logo"], league_id)

    def test_no_generic_aliases(self):
        for competition in load_catalog()["competitions"]:
            for alias in competition["aliases"]:
                self.assertNotIn(
                    normalize_name(alias), self.GENERIC_ALIASES,
                    f"'{alias}' of '{competition['id']}' is ambiguous",
                )


if __name__ == "__main__":
    unittest.main()
