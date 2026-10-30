from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from normalize_logo import normalize_logo


class NormalizeLogoTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.src = self.dir / "in.png"
        self.dst = self.dir / "out" / "logo.png"

    def tearDown(self):
        self.tmp.cleanup()

    def test_trims_transparent_margins(self):
        image = Image.new("RGBA", (100, 80), (0, 0, 0, 0))
        image.paste((255, 0, 0, 255), (10, 20, 60, 50))
        image.save(self.src)
        self.assertEqual(normalize_logo(self.src, self.dst), (50, 30))
        with Image.open(self.dst) as out:
            self.assertEqual(out.mode, "RGBA")
            self.assertEqual(out.size, (50, 30))

    def test_caps_longest_side(self):
        image = Image.new("RGBA", (2048, 1024), (255, 0, 0, 255))
        image.putpixel((0, 0), (0, 0, 0, 0))
        image.save(self.src)
        self.assertEqual(normalize_logo(self.src, self.dst), (1024, 512))

    def test_does_not_upscale(self):
        image = Image.new("RGBA", (40, 20), (0, 0, 0, 0))
        image.paste((0, 0, 255, 255), (5, 5, 35, 15))
        image.save(self.src)
        self.assertEqual(normalize_logo(self.src, self.dst), (30, 10))

    def test_rejects_image_without_transparency(self):
        Image.new("RGB", (50, 50), (255, 255, 255)).save(self.src)
        with self.assertRaises(ValueError):
            normalize_logo(self.src, self.dst)
        self.assertFalse(self.dst.exists())

    def test_rejects_fully_transparent_image(self):
        Image.new("RGBA", (50, 50), (0, 0, 0, 0)).save(self.src)
        with self.assertRaises(ValueError):
            normalize_logo(self.src, self.dst)
        self.assertFalse(self.dst.exists())


if __name__ == "__main__":
    unittest.main()
