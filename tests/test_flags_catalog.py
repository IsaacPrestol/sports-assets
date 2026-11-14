"""Guard the flag catalog: ids, regions, lookups and opaque images."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class FlagCatalogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.catalog = {"version": 1, "flags": [
            {"id": "es", "code": "ES", "name": "Spain", "aliases": ["España", "ESP"],
             "type": "country", "parent": None, "flag": "flags/es.png"},
            {"id": "es-pv", "code": "ES-PV", "name": "Basque Country", "aliases": ["Euskadi", "País Vasco"],
             "type": "subdivision", "parent": "es", "flag": "flags/es-pv.png"},
        ]}
        for entry in self.catalog["flags"]:
            self.png(entry["flag"])

    def png(self, relative, size=(30, 20), color=(200, 0, 0, 255)):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGBA", size, color).save(path)
        return path

    def validate(self):
        from flags_catalog import validate_flags
        return validate_flags(self.root, self.catalog)

    def errors(self):
        return self.validate()[0]

    def test_valid_catalog_with_opaque_flags_passes(self):
        self.assertEqual(self.validate(), ([], []))

    def test_names_aliases_and_codes_resolve(self):
        from football_catalog import build_lookup, normalize_name
        lookup, errors = build_lookup(self.catalog["flags"])
        self.assertEqual(errors, [])
        self.assertEqual(lookup[normalize_name("España")], "es")
        self.assertEqual(lookup[normalize_name("ESP")], "es")
        self.assertEqual(lookup[normalize_name("Euskadi")], "es-pv")
        self.assertEqual(lookup[normalize_name("ES-PV")], "es-pv")

    def test_alias_collision_is_rejected(self):
        self.catalog["flags"][1]["aliases"].append("España")
        self.assertTrue(any("collides" in e for e in self.errors()))

    def test_id_must_be_lowercase_code(self):
        self.catalog["flags"][0]["id"] = "spain"
        self.catalog["flags"][0]["flag"] = "flags/spain.png"
        self.assertTrue(any("lowercase" in e for e in self.errors()))

    def test_subdivision_needs_known_parent_with_matching_code(self):
        self.catalog["flags"][1]["parent"] = "fr"
        self.assertTrue(any("unknown parent" in e for e in self.errors()))
        self.catalog["flags"].append({"id": "fr", "code": "FR", "name": "France", "aliases": [],
                                      "type": "country", "parent": None, "flag": None})
        self.assertTrue(any("start with its parent" in e for e in self.errors()))

    def test_country_must_not_have_parent(self):
        self.catalog["flags"][0]["parent"] = "es-pv"
        self.assertTrue(any("must not have a parent" in e for e in self.errors()))

    def test_image_path_must_match_id(self):
        self.catalog["flags"][0]["flag"] = "flags/spain.png"
        self.assertTrue(any("must be 'flags/es.png'" in e for e in self.errors()))

    def test_missing_oversized_and_unreferenced_images(self):
        (self.root / "flags/es.png").unlink()
        self.png("flags/es-pv.png", size=(1100, 700))
        self.png("flags/xx.png")
        errors = self.errors()
        self.assertTrue(any("not found: flags/es.png" in e for e in errors))
        self.assertTrue(any("exceeds 1024" in e for e in errors))
        self.assertTrue(any("not referenced: flags/xx.png" in e for e in errors))

    def test_missing_image_is_a_warning(self):
        (self.root / "flags/es.png").unlink()
        self.catalog["flags"][0]["flag"] = None
        self.assertEqual(self.validate(), ([], ["Flag 'es' has no image yet"]))

    def test_country_codes_without_flag(self):
        from flags_catalog import missing_country_flags
        self.assertEqual(missing_country_flags(self.catalog["flags"], {"ES", "ES-PV", "GB-ENG", None}), ["GB-ENG"])


class NormalizeFlagTest(unittest.TestCase):
    def test_keeps_opaque_flags_and_caps_size_without_upscaling(self):
        from flags_catalog import normalize_flag
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / "src.png", Path(tmp) / "out" / "flag.png"
            Image.new("RGB", (1280, 853), (0, 0, 255)).save(src)
            self.assertEqual(normalize_flag(src, dst), (1024, 682))
            Image.new("RGB", (300, 200), (0, 0, 255)).save(src)
            self.assertEqual(normalize_flag(src, dst), (300, 200))

    def test_trims_transparent_margins(self):
        from flags_catalog import normalize_flag
        with tempfile.TemporaryDirectory() as tmp:
            src, dst = Path(tmp) / "src.png", Path(tmp) / "flag.png"
            image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
            image.paste((255, 0, 0, 255), (10, 20, 70, 60))
            image.save(src)
            self.assertEqual(normalize_flag(src, dst), (60, 40))


class SeedHelpersTest(unittest.TestCase):
    def test_ambiguous_aliases_are_dropped_but_names_win(self):
        from sync_flags import drop_colliding_aliases
        flags = [
            {"id": "mf", "name": "Saint Martin", "aliases": ["San Martín", "MAF"]},
            {"id": "sx", "name": "Sint Maarten", "aliases": ["San Martín", "Saint-Martin", "SXM"]},
        ]
        dropped = drop_colliding_aliases(flags)
        self.assertEqual(flags[0]["aliases"], ["MAF"])
        self.assertEqual(flags[1]["aliases"], ["SXM"])
        self.assertCountEqual(dropped, ["mf: San Martín", "sx: San Martín", "sx: Saint-Martin"])


class RealFlagCatalogTest(unittest.TestCase):
    def test_real_catalog_covers_iso_countries_and_regions(self):
        flags = {f["id"]: f for f in json.loads((ROOT / "data/flags.json").read_text(encoding="utf-8"))["flags"]}
        countries = [f for f in flags.values() if f["type"] == "country"]
        self.assertGreaterEqual(len(countries), 250)  # 249 ISO 3166-1 codes plus Kosovo
        for region in ("gb-eng", "gb-sct", "gb-wls", "gb-nir", "es-pv", "es-ct", "es-ga"):
            self.assertEqual(flags[region]["type"], "subdivision")
        lookup = json.loads((ROOT / "data/flags-lookup.json").read_text(encoding="utf-8"))
        self.assertEqual(lookup["euskadi"], "es-pv")
        self.assertEqual(lookup["catalunya"], "es-ct")
        self.assertEqual(lookup["ger"], "de")
        self.assertEqual(lookup["sco"], "gb-sct")


if __name__ == "__main__":
    unittest.main()
