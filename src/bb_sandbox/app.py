"""Pygame window lifecycle and main loop."""

from pathlib import Path

import pygame

from bb_sandbox.layout import Layout, build_layout
from bb_sandbox.races import RACES_FILE, load_races
from bb_sandbox.render import draw_builder, draw_menu, draw_races, draw_sandbox
from bb_sandbox.session import (
    ImportRoster,
    LoadSetup,
    SaveRoster,
    SaveSetup,
    Screen,
    Session,
)

WINDOW_TITLE = "Blood Bowl Sandbox"
FPS = 60
FONT_SIZE = 20
ROSTERS_DIR = Path("rosters")
SETUPS_DIR = Path("setups")
LEFT_BUTTON = 1
RIGHT_BUTTON = 3


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
            case LoadSetup(path=path):
                session.load_setup(path)
            case SaveSetup():
                session.save_setup()
                # Reason: the new file shows up in the setups list right away.
                session.rescan()
            case SaveRoster():
                session.save_roster()
                # Reason: the new roster shows up in the menu's roster lists
                # right away.
                session.rescan()
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == RIGHT_BUTTON:
        session.right_click(event.pos)
    elif event.type == pygame.MOUSEBUTTONUP and event.button == LEFT_BUTTON:
        session.release(event.pos)
    elif event.type == pygame.MOUSEMOTION:
        session.move(event.pos)
    elif event.type == pygame.WINDOWFOCUSGAINED:
        # Reason: picks up roster and setup files added or renamed in Explorer
        # while the app was in the background.
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
    if session.screen is Screen.SANDBOX and session.interaction is not None:
        view = session.interaction.view()
        draw_sandbox(surface, layout, font, session.board, view, session.message)
    elif session.screen is Screen.RACES:
        draw_races(surface, layout, font, session.races, session.message)
    elif session.screen is Screen.BUILDER and session.builder is not None:
        draw_builder(surface, layout, font, session.builder, session.message)
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
        RaceError: If the race database shipped with the app is invalid.
    """
    if max_frames is not None and max_frames <= 0:
        raise ValueError(f"max_frames must be positive, got {max_frames}")

    layout = build_layout()
    # Reason: a broken races.csv is a packaging bug, not a user error, so its
    # RaceError (file, line and field) stops the app before the window opens.
    races = load_races(RACES_FILE)
    session = Session(layout, ROSTERS_DIR, SETUPS_DIR, races)
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
