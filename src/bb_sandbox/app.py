"""Pygame window lifecycle and main loop."""

import pygame

from bb_sandbox.layout import build_layout
from bb_sandbox.render import draw_scene

WINDOW_TITLE = "Blood Bowl Sandbox"
FPS = 60
FONT_SIZE = 20


def run(max_frames: int | None = None) -> int:
    """
    Open the sandbox window and run the main loop until the user closes it.

    Args:
        max_frames (int | None): Stop after this many frames. None runs until
            the window is closed; tests pass a small number to bound the loop.

    Returns:
        int: Number of frames rendered.

    Raises:
        ValueError: If max_frames is given and is not positive.
    """
    if max_frames is not None and max_frames <= 0:
        raise ValueError(f"max_frames must be positive, got {max_frames}")

    layout = build_layout()
    pygame.init()
    try:
        screen = pygame.display.set_mode(layout.window_size)
        pygame.display.set_caption(WINDOW_TITLE)
        font = pygame.font.Font(None, FONT_SIZE)
        clock = pygame.time.Clock()
        frames = 0
        running = True
        # Reason: an interactive loop is bounded by the user closing the window;
        # max_frames gives tests an explicit cap.
        while running and (max_frames is None or frames < max_frames):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
            draw_scene(screen, layout, font)
            pygame.display.flip()
            clock.tick(FPS)
            frames += 1
        return frames
    finally:
        pygame.quit()
