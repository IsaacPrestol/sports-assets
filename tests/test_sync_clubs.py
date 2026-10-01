from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from sync_clubs import manual_cache_path, manual_note


class ManualUrlTest(unittest.TestCase):
    def test_cache_path_changes_with_the_url(self):
        old = manual_cache_path("limon", "https://upload.wikimedia.org/wikipedia/en/a/ab/Old.png")
        new = manual_cache_path("limon", "https://upload.wikimedia.org/wikipedia/en/c/cd/New.png")
        self.assertNotEqual(old, new)
        self.assertEqual(old, manual_cache_path("limon", "https://upload.wikimedia.org/wikipedia/en/a/ab/Old.png"))

    def test_note_names_the_real_host(self):
        self.assertEqual(manual_note("https://upload.wikimedia.org/wikipedia/commons/a/ab/X.svg"),
                         "Via Wikimedia Commons")
        self.assertEqual(manual_note("https://upload.wikimedia.org/wikipedia/en/a/ab/X.png"),
                         "Via en.wikipedia (non-free logo)")
        self.assertEqual(manual_note("https://example.org/x.png"), "Manual url in clubs-mapping.json")


if __name__ == "__main__":
    unittest.main()
