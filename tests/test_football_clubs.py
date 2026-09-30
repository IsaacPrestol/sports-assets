from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from football_clubs import auto_aliases, propose_slug, slug_name, slugify, strip_affixes


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


if __name__ == "__main__":
    unittest.main()
