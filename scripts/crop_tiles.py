"""Crop two square tiles from the top row of an image.

The image's width is split into 4 squares of side X = width // 4. The script saves
the 1st (top-left corner) and the 3rd square from the left, both from the top row.

Given a folder of raw images instead, it writes each image's 1st square to
sprites/home/<name> and its 3rd square to sprites/away/<name>.

Usage:
    uv run python scripts/crop_tiles.py path/to/image.png [--out folder]
    uv run python scripts/crop_tiles.py path/to/raw-folder [--sprites folder]
"""

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # must follow the env var above

TILES_ACROSS = 4
# (output suffix, square index from the left, 0-based)
TILES_TO_SAVE = ((1, 0), (3, 2))
SPRITES_DIR = Path("sprites")
# Reason: these are the formats pygame.image.save can write; .gif/.webp would be
# written as TGA under the wrong extension, so folder mode skips them.
RAW_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp"}


def _crop_squares(source: Path) -> tuple[pygame.Surface, pygame.Surface]:
    """
    Load an image and return its 1st and 3rd top-row squares.

    Args:
        source (Path): The image to crop.

    Returns:
        tuple[pygame.Surface, pygame.Surface]: The 1st and 3rd square.

    Raises:
        ValueError: If the image is narrower than 4 pixels or shorter than one square.
        FileNotFoundError: If `source` does not exist.
        pygame.error: If `source` is not a readable image.
    """
    image = pygame.image.load(source)
    # Reason: a width not divisible by 4 is floored, so the leftover pixels on the
    # right are ignored rather than stretching or padding the squares.
    size = image.get_width() // TILES_ACROSS
    if size == 0:
        raise ValueError(f"{source.name}: width {image.get_width()} is under 4 pixels")
    if image.get_height() < size:
        raise ValueError(
            f"{source.name}: height {image.get_height()} is under the square size {size}"
        )
    first, third = (
        image.subsurface((column * size, 0, size, size)) for _, column in TILES_TO_SAVE
    )
    return first, third


def crop_tiles(source: Path, out_dir: Path | None = None) -> tuple[Path, Path]:
    """
    Save the 1st and 3rd top-row squares of an image as `<stem>_1` and `<stem>_3`.

    Args:
        source (Path): The image to crop.
        out_dir (Path | None): Folder for the two crops; defaults to the image's folder.

    Returns:
        tuple[Path, Path]: The paths of the 1st and 3rd square crops.

    Raises:
        ValueError: If the image is narrower than 4 pixels or shorter than one square.
        FileNotFoundError: If `source` does not exist.
        pygame.error: If `source` is not a readable image.
    """
    squares = _crop_squares(source)
    out_dir = source.parent if out_dir is None else out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for (suffix, _), square in zip(TILES_TO_SAVE, squares):
        target = out_dir / f"{source.stem}_{suffix}{source.suffix}"
        pygame.image.save(square, target)
        written.append(target)
    return written[0], written[1]


def split_folder(
    raw_dir: Path, sprites_dir: Path = SPRITES_DIR
) -> tuple[list[Path], list[str]]:
    """
    Crop every raw image in a folder into home and away sprites with the same name.

    The 1st square goes to `sprites_dir/home/<name>`, the 3rd to
    `sprites_dir/away/<name>`, overwriting existing files. Subfolders and files
    whose extension is not in RAW_EXTENSIONS are ignored.

    Args:
        raw_dir (Path): Folder of raw images.
        sprites_dir (Path): Folder holding `home/` and `away/`; created if missing.

    Returns:
        tuple[list[Path], list[str]]: The written sprite paths, and one message per
            image that could not be cropped.
    """
    targets = (sprites_dir / "home", sprites_dir / "away")
    for folder in targets:
        folder.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    errors: list[str] = []
    for path in sorted(raw_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in RAW_EXTENSIONS:
            continue
        try:
            squares = _crop_squares(path)
        except ValueError as error:
            errors.append(str(error))
            continue
        except pygame.error as error:
            errors.append(f"{path.name}: {error}")
            continue
        for folder, square in zip(targets, squares):
            pygame.image.save(square, folder / path.name)
            written.append(folder / path.name)
    return written, errors


def main(argv: list[str] | None = None) -> int:
    """
    Parse the command line, crop the image or folder and print the written paths.

    Args:
        argv (list[str] | None): Arguments without the program name; defaults to sys.argv.

    Returns:
        int: 0 on success, 1 if any image could not be cropped.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path, help="image, or folder of raw images")
    parser.add_argument(
        "--out", type=Path, help="image mode: output folder (default: image's)"
    )
    parser.add_argument(
        "--sprites",
        type=Path,
        default=SPRITES_DIR,
        help=f"folder mode: sprites folder (default: {SPRITES_DIR})",
    )
    args = parser.parse_args(argv)
    if args.source.is_dir():
        paths, errors = split_folder(args.source, args.sprites)
    else:
        try:
            paths, errors = list(crop_tiles(args.source, args.out)), []
        except (ValueError, FileNotFoundError, pygame.error) as error:
            paths, errors = [], [str(error)]
    for path in paths:
        print(path)
    for message in errors:
        print(f"crop_tiles: {message}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
