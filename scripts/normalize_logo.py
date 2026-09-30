"""Trim transparent margins from a logo and cap its longest side."""

from pathlib import Path
import argparse
import sys

from PIL import Image

MAX_SIDE = 1024


def normalize_logo(src: Path, dst: Path, max_side: int = MAX_SIDE) -> tuple[int, int]:
    with Image.open(src) as image:
        rgba = image.convert("RGBA")

    alpha = rgba.getchannel("A")
    if alpha.getextrema()[0] == 255:
        raise ValueError(f"{src} has no transparent pixels; use a logo with a transparent background")
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError(f"{src} is fully transparent")

    logo = rgba.crop(bbox)
    logo.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    logo.save(dst, "PNG", optimize=True)
    return logo.size


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("src", type=Path, help="Downloaded logo")
    parser.add_argument("dst", type=Path, help="Destination, e.g. football/competitions/europe/laliga.png")
    args = parser.parse_args()

    try:
        width, height = normalize_logo(args.src, args.dst)
    except (OSError, ValueError) as exc:
        print("ERROR:", exc)
        sys.exit(1)
    print(f"OK -> {args.dst} ({width}x{height})")


if __name__ == "__main__":
    main()
