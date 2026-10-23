# Blood Bowl Sandbox

Interactive sandbox for testing Blood Bowl formations and setups. See [docs/prd.md](docs/prd.md).

## Setup & run

Requires [uv](https://docs.astral.sh/uv/). Python 3.13 is pinned (Pygame 2.6.1 has no 3.14+ wheels).

```bash
uv sync               # add --system-certs if PyPI TLS verification fails
uv run bb-sandbox     # launch the window
uv run pytest --cov   # tests (headless via SDL dummy driver)
```

## Layout

| Module | Responsibility |
|---|---|
| `bb_sandbox.layout` | Pure screen geometry: 26x15 pitch, Line of Scrimmage, Wide Zones, reserves, info panel. No Pygame. |
| `bb_sandbox.render` | Draws the static scene with Pygame from a `Layout`. |
| `bb_sandbox.app` | Window lifecycle and main loop (`run(max_frames=None)`). |
