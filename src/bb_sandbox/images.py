"""Image files in a folder, found by suffix.

No Pygame dependency, so session can list pitch images without importing it.
"""

from pathlib import Path

# Compared in lower case, so `A.PNG` counts.
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")


def list_images(folder: Path) -> tuple[Path, ...]:
    """
    List the image files in a folder.

    Args:
        folder (Path): Folder to scan.

    Returns:
        tuple[Path, ...]: Files with one of IMAGE_SUFFIXES, in any case, sorted
            by name; empty if the folder is missing.
    """
    if not folder.is_dir():
        return ()
    return tuple(
        sorted(
            p
            for p in folder.iterdir()
            if p.suffix.lower() in IMAGE_SUFFIXES and p.is_file()
        )
    )
