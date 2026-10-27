"""Tests for scripts/crop_tiles.py."""

import importlib.util
from pathlib import Path

import pygame
import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "crop_tiles.py"
# Reason: scripts/ is not a package, so load the module straight from its file.
_spec = importlib.util.spec_from_file_location("crop_tiles", SCRIPT)
crop_tiles = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(crop_tiles)

QUARTER_COLOURS = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]


def _make_image(path: Path, width: int, height: int) -> Path:
    """
    Save a PNG whose four vertical quarters are filled with QUARTER_COLOURS.

    Args:
        path (Path): Where to save the image.
        width (int): Image width.
        height (int): Image height.

    Returns:
        Path: `path`.
    """
    surface = pygame.Surface((width, height))
    quarter = max(width // 4, 1)
    for index, colour in enumerate(QUARTER_COLOURS):
        surface.fill(colour, (index * quarter, 0, quarter, height))
    pygame.image.save(surface, path)
    return path


def _colour(path: Path) -> tuple[int, int, int]:
    """
    Return the RGB colour of the top-left pixel of an image file.

    Args:
        path (Path): The image.

    Returns:
        tuple[int, int, int]: The pixel's colour.
    """
    return tuple(pygame.image.load(path).get_at((0, 0)))[:3]


def test_crops_first_and_third_squares(tmp_path):
    source = _make_image(tmp_path / "pitch.png", 400, 200)

    first, third = crop_tiles.crop_tiles(source)

    assert (first.name, third.name) == ("pitch_1.png", "pitch_3.png")
    assert first.parent == tmp_path
    assert pygame.image.load(first).get_size() == (100, 100)
    assert pygame.image.load(third).get_size() == (100, 100)
    assert _colour(first) == QUARTER_COLOURS[0]
    assert _colour(third) == QUARTER_COLOURS[2]


def test_out_folder_is_created(tmp_path):
    source = _make_image(tmp_path / "pitch.png", 400, 200)
    out = tmp_path / "new" / "crops"

    paths = crop_tiles.crop_tiles(source, out)

    assert all(path.parent == out and path.exists() for path in paths)


def test_width_not_divisible_by_four_is_floored(tmp_path):
    source = _make_image(tmp_path / "odd.png", 403, 200)

    _, third = crop_tiles.crop_tiles(source)

    assert pygame.image.load(third).get_size() == (100, 100)
    # The third square starts at x 200, the start of the third colour band.
    assert _colour(third) == QUARTER_COLOURS[2]


def test_height_equal_to_square_size_works(tmp_path):
    source = _make_image(tmp_path / "strip.png", 400, 100)

    first, _ = crop_tiles.crop_tiles(source)

    assert pygame.image.load(first).get_size() == (100, 100)


@pytest.mark.parametrize("size", [(400, 50), (3, 10)])
def test_too_small_image_raises(tmp_path, size):
    source = _make_image(tmp_path / "small.png", *size)

    with pytest.raises(ValueError):
        crop_tiles.crop_tiles(source)


def test_main_prints_paths(tmp_path, capsys):
    source = _make_image(tmp_path / "pitch.png", 400, 200)

    assert crop_tiles.main([str(source), "--out", str(tmp_path / "out")]) == 0
    assert "pitch_3.png" in capsys.readouterr().out


def test_main_missing_file_returns_1(tmp_path, capsys):
    assert crop_tiles.main([str(tmp_path / "missing.png")]) == 1
    assert "crop_tiles:" in capsys.readouterr().err


def test_split_folder_writes_home_and_away(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    for name in ("human-blitzer.png", "orc-lineman.png"):
        _make_image(raw / name, 400, 200)
    sprites = tmp_path / "sprites"

    written, errors = crop_tiles.split_folder(raw, sprites)

    assert errors == []
    assert len(written) == 4
    for name in ("human-blitzer.png", "orc-lineman.png"):
        home, away = sprites / "home" / name, sprites / "away" / name
        assert pygame.image.load(home).get_size() == (100, 100)
        assert _colour(home) == QUARTER_COLOURS[0]
        assert _colour(away) == QUARTER_COLOURS[2]


def test_split_folder_ignores_others_and_overwrites(tmp_path):
    raw = tmp_path / "raw"
    (raw / "sub").mkdir(parents=True)
    (raw / "notes.txt").write_text("not an image")
    _make_image(raw / "sub" / "nested.png", 400, 200)
    _make_image(raw / "OGRE.PNG", 400, 200)
    sprites = tmp_path / "sprites"
    (sprites / "home").mkdir(parents=True)
    pygame.image.save(pygame.Surface((5, 5)), sprites / "home" / "OGRE.PNG")

    written, errors = crop_tiles.split_folder(raw, sprites)

    assert errors == []
    assert sorted(path.name for path in written) == ["OGRE.PNG", "OGRE.PNG"]
    assert pygame.image.load(sprites / "home" / "OGRE.PNG").get_size() == (100, 100)


def test_split_folder_reports_bad_image_and_continues(tmp_path, capsys):
    raw = tmp_path / "raw"
    raw.mkdir()
    _make_image(raw / "good.png", 400, 200)
    _make_image(raw / "small.png", 400, 50)
    (raw / "broken.png").write_text("not a png")
    sprites = tmp_path / "sprites"

    assert crop_tiles.main([str(raw), "--sprites", str(sprites)]) == 1

    assert (sprites / "away" / "good.png").exists()
    assert not (sprites / "home" / "small.png").exists()
    err = capsys.readouterr().err
    assert "small.png" in err and "broken.png" in err
