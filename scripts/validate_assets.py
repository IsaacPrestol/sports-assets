from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIRS = [
    ROOT / "football" / "competitions",
    ROOT / "ufc" / "fighters",
    ROOT / "ufc" / "logos",
]
ALLOWED = {".png", ".webp", ".jpg", ".jpeg", ".svg"}
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.(?:png|webp|jpg|jpeg|svg)$")
MAX_BYTES = 5 * 1024 * 1024


def png_dimensions(path: Path):
    try:
        with path.open("rb") as f:
            header = f.read(24)
        if header[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        return struct.unpack(">II", header[16:24])
    except OSError:
        return None


def main():
    errors = []
    warnings = []
    seen = {}

    for folder in ASSET_DIRS:
        if not folder.exists():
            continue

        for path in folder.iterdir():
            if not path.is_file() or path.name.startswith("."):
                continue

            if path.suffix.lower() not in ALLOWED:
                errors.append(f"Unsupported extension: {path.relative_to(ROOT)}")
                continue

            if not NAME_RE.match(path.name):
                errors.append(f"Invalid filename: {path.relative_to(ROOT)}")

            slug = path.stem
            if slug in seen:
                warnings.append(
                    f"Repeated slug '{slug}': {seen[slug].relative_to(ROOT)} and {path.relative_to(ROOT)}"
                )
            else:
                seen[slug] = path

            if path.stat().st_size > MAX_BYTES:
                warnings.append(f"Large asset (>5 MB): {path.relative_to(ROOT)}")

            if path.suffix.lower() == ".png":
                dims = png_dimensions(path)
                if dims:
                    w, h = dims
                    if w > 3000 or h > 3000:
                        warnings.append(
                            f"Very large dimensions ({w}x{h}): {path.relative_to(ROOT)}"
                        )

    for warning in warnings:
        print("WARNING:", warning)
    for error in errors:
        print("ERROR:", error)

    if errors:
        print(f"\nValidation failed with {len(errors)} error(s).")
        sys.exit(1)

    print(f"\nValidation passed. {len(warnings)} warning(s).")


if __name__ == "__main__":
    main()
