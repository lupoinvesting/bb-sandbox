# Crop tiles script

`scripts/crop_tiles.py` is a standalone utility, not part of the game. It splits an image's width into 4 squares of side `X = width // 4` and saves two `X × X` crops from the top row:

- `<stem>_1<ext>`: the 1st square (top-left corner, x `0..X`).
- `<stem>_3<ext>`: the 3rd square from the left (x `2X..3X`).

## Usage
```bash
uv run python scripts/crop_tiles.py path/to/image.png             # crops next to the image
uv run python scripts/crop_tiles.py path/to/image.png --out crops # crops in ./crops (created if missing)
```
The script prints the two written paths. Existing files with the same names are overwritten.

## Behaviour
- A width not divisible by 4 is floored: the leftover pixels on the right are ignored.
- Uses Pygame (already a dependency) to load, crop and save; no display is opened.

## Folder mode
Pass a folder of raw images instead of one image to build player sprites ([sprites.md](sprites.md)):
```bash
uv run python scripts/crop_tiles.py raw/                       # into sprites/home and sprites/away
uv run python scripts/crop_tiles.py raw/ --sprites other/dir   # into other/dir/home and other/dir/away
```
- For each image, the 1st square is written to `sprites/home/<name>` and the 3rd to `sprites/away/<name>`, keeping the original file name (e.g. `human-blitzer.png`). Run it from the project root, where the app looks for `sprites/`.
- The raw images are left untouched; existing sprites with the same name are overwritten.
- Only `.png .jpg .jpeg .bmp` files (any case) are read, the formats Pygame can save. Other files and subfolders are ignored.
- `--out` applies only to single-image mode.

## Errors
The script prints `crop_tiles: <message>` to stderr and exits with 1 when:
- the image is narrower than 4 pixels, or shorter than one square (`height < X`);
- the file does not exist or is not a readable image.

In folder mode a bad image is reported and skipped; the other images are still written, and the exit code is 1 at the end.

Tests: `tests/scripts/test_crop_tiles.py`.
