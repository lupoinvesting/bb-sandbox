"""Pygame window lifecycle and main loop."""

from pathlib import Path

import pygame

from bb_sandbox.layout import Layout, build_layout
from bb_sandbox.render import draw_menu, draw_sandbox
from bb_sandbox.session import ImportRoster, Screen, Session

WINDOW_TITLE = "Blood Bowl Sandbox"
FPS = 60
FONT_SIZE = 20
ROSTERS_DIR = Path("rosters")
LEFT_BUTTON = 1


def handle_event(session: Session, event: pygame.event.Event) -> bool:
    """
    Map one Pygame event to session calls.

    Args:
        session (Session): The session to drive.
        event (pygame.event.Event): The event to handle.

    Returns:
        bool: False if the window should close, True otherwise.
    """
    if event.type == pygame.QUIT:
        return False
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == LEFT_BUTTON:
        # Reason: press() only returns file requests; the disk I/O is done
        # here so it's visible at the call site.
        match session.press(event.pos):
            case ImportRoster(side=side, path=path):
                session.import_team(side, path)
    elif event.type == pygame.WINDOWFOCUSGAINED:
        # Reason: picks up roster files added in Explorer while the app was
        # in the background.
        session.rescan()
    return True


def _draw(
    surface: pygame.Surface, layout: Layout, font: pygame.font.Font, session: Session
) -> None:
    """
    Draw whichever screen the session is showing.

    Args:
        surface (pygame.Surface): The window surface.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for all text.
        session (Session): The session to draw.
    """
    if session.screen is Screen.SANDBOX and session.board is not None:
        draw_sandbox(surface, layout, font, session.board)
    else:
        draw_menu(surface, layout, font, session.menu_view(), session.message)


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
    session = Session(layout, ROSTERS_DIR)
    session.rescan()
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
                running = handle_event(session, event) and running
            _draw(screen, layout, font, session)
            pygame.display.flip()
            clock.tick(FPS)
            frames += 1
        return frames
    finally:
        pygame.quit()
