"""Tests for bb_sandbox.images."""

from bb_sandbox.images import list_images


def test_list_images_keeps_image_suffixes_in_any_case(tmp_path):
    for name in ("A.PNG", "b.jpg", "notes.txt", ".gitkeep"):
        (tmp_path / name).write_bytes(b"")
    assert [p.name for p in list_images(tmp_path)] == ["A.PNG", "b.jpg"]


def test_list_images_sorts_by_name_and_skips_folders(tmp_path):
    for name in ("c.webp", "a.gif", "b.bmp"):
        (tmp_path / name).write_bytes(b"")
    (tmp_path / "d.png").mkdir()
    assert [p.name for p in list_images(tmp_path)] == ["a.gif", "b.bmp", "c.webp"]


def test_list_images_of_a_missing_folder_is_empty(tmp_path):
    assert list_images(tmp_path / "missing") == ()
