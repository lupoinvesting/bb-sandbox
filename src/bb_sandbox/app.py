"""Pygame window lifecycle and main loop."""

from pathlib import Path

import pygame

from bb_sandbox.dice import BlockFace
from bb_sandbox.layout import Layout, build_layout
from bb_sandbox.races import RACES_FILE, load_races
from bb_sandbox.render import (
    DICE_SPRITES_DIR,
    PitchSprite,
    PlayerSprites,
    draw_builder,
    draw_dice,
    draw_menu,
    draw_name_box,
    draw_options,
    draw_races,
    draw_sandbox,
    load_block_sprites,
    load_pitch_sprite,
    load_player_sprites,
)
from bb_sandbox.session import (
    FileRequest,
    ImportRoster,
    Key,
    LoadSetup,
    RenameFile,
    SaveRoster,
    SaveSettings,
    SaveSetup,
    Screen,
    Session,
)

WINDOW_TITLE = "Blood Bowl Sandbox"
FPS = 60
FONT_SIZE = 20
# Reason: numbers on the dice are drawn bigger than the rest of the text.
DIE_FONT_SIZE = 40
ROSTERS_DIR = Path("rosters")
SETUPS_DIR = Path("setups")
PLAYER_SPRITES_DIR = Path("sprites")
PITCH_SPRITES_DIR = PLAYER_SPRITES_DIR / "pitch"
SETTINGS_FILE = Path("settings.json")
LEFT_BUTTON = 1
RIGHT_BUTTON = 3
# Reason: holding Backspace in the name box deletes repeatedly.
KEY_REPEAT_DELAY_MS = 400
KEY_REPEAT_INTERVAL_MS = 40
KEYS = {
    pygame.K_BACKSPACE: Key.BACKSPACE,
    pygame.K_RETURN: Key.ENTER,
    pygame.K_KP_ENTER: Key.ENTER,
    pygame.K_ESCAPE: Key.ESCAPE,
}


def _perform(session: Session, request: FileRequest | None) -> None:
    """
    Do the disk I/O a session request asks for.

    Args:
        session (Session): The session that made the request.
        request (FileRequest | None): The request; None does nothing.
    """
    # Reason: the session only returns file requests; the disk I/O is done
    # here so it's visible at the call site.
    match request:
        case ImportRoster(side=side, path=path):
            session.import_team(side, path)
        case LoadSetup(path=path):
            session.load_setup(path)
        case SaveSetup(name=name):
            session.save_setup(name)
            # Reason: the new file shows up in the setups list right away.
            session.rescan()
        case SaveRoster(name=name):
            session.save_roster(name)
            # Reason: the new roster shows up in the menu's roster lists
            # right away.
            session.rescan()
        case RenameFile(path=path, name=name):
            session.rename(path, name)
            session.rescan()


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
        _perform(session, session.press(event.pos))
    elif event.type == pygame.TEXTINPUT:
        session.type_text(event.text)
    elif event.type == pygame.KEYDOWN and event.key in KEYS:
        _perform(session, session.key(KEYS[event.key]))
            case SaveSettings():
                session.save_settings()
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == RIGHT_BUTTON:
        session.right_click(event.pos)
    elif event.type == pygame.MOUSEBUTTONUP and event.button == LEFT_BUTTON:
        session.release(event.pos)
    elif event.type == pygame.MOUSEMOTION:
        session.move(event.pos)
    elif event.type == pygame.WINDOWFOCUSGAINED:
        # Reason: picks up roster, setup and pitch image files added or
        # renamed in Explorer while the app was in the background.
        session.rescan()
    return True


def _draw(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    die_font: pygame.font.Font,
    sprites: dict[BlockFace, pygame.Surface],
    player_sprites: PlayerSprites,
    pitch_sprite: PitchSprite,
    session: Session,
) -> None:
    """
    Draw whichever screen the session is showing.

    Args:
        surface (pygame.Surface): The window surface.
        layout (Layout): Screen geometry.
        font (pygame.font.Font): Font for all text but the numbers on dice.
        die_font (pygame.font.Font): Bigger font for the numbers on dice.
        sprites (dict[BlockFace, pygame.Surface]): Block dice images, from
            load_block_sprites.
        player_sprites (PlayerSprites): Player images, from load_player_sprites.
        pitch_sprite (PitchSprite): The pitch image, from load_pitch_sprite.
        session (Session): The session to draw.
    """
    # Reason: a broken player or pitch image stays reported until it is fixed,
    # without hiding the session's own feedback.
    message = session.message or player_sprites.problem or pitch_sprite.problem
    if session.screen is Screen.SANDBOX and session.interaction is not None:
        view = session.interaction.view()
        board, pitch = session.board, pitch_sprite.image
        draw_sandbox(surface, layout, font, board, view, player_sprites, pitch, message)
        draw_dice(surface, layout, font, die_font, session.last_roll, sprites)
    elif session.screen is Screen.RACES:
        draw_races(surface, layout, font, session.races, message)
    elif session.screen is Screen.OPTIONS:
        draw_options(surface, layout, font, session.options_view(), message)
    elif session.screen is Screen.BUILDER and session.builder is not None:
        draw_builder(surface, layout, font, session.builder, message)
    else:
        draw_menu(surface, layout, font, session.menu_view(), message)
    # Reason: drawn last so the box sits over whichever screen opened it.
    if session.name_view is not None:
        draw_name_box(surface, layout, font, session.name_view)


def _load_pitch(session: Session, layout: Layout) -> PitchSprite:
    """
    Load the session's chosen pitch image, stretched to the pitch.

    Args:
        session (Session): Holds the chosen pitch.
        layout (Layout): Screen geometry; the pitch's size.

    Returns:
        PitchSprite: The image, or no image and why.
    """
    return load_pitch_sprite(
        session.pitch_path, (layout.pitch.width, layout.pitch.height)
    )


def _run_frames(
    screen: pygame.Surface, layout: Layout, session: Session, max_frames: int | None
) -> int:
    """
    Load the fonts and images, then draw frames until the window closes.

    Args:
        screen (pygame.Surface): The window surface; the display mode is set.
        layout (Layout): Screen geometry.
        session (Session): The session to drive and draw.
        max_frames (int | None): Stop after this many frames; None runs until
            the window is closed.

    Returns:
        int: Number of frames rendered.

    Raises:
        SpriteError: If a block dice image exists but can't be decoded.
    """
    font = pygame.font.Font(None, FONT_SIZE)
    die_font = pygame.font.Font(None, DIE_FONT_SIZE)
    # Reason: loaded once, after set_mode, because convert_alpha needs the
    # display mode. Like a broken races.csv, an image that exists but can't
    # be decoded stops the app with a SpriteError naming the file; only a
    # missing image falls back to the face's name.
    sprites = load_block_sprites(DICE_SPRITES_DIR, layout.die_boxes[0].width)
    # Reason: player and pitch images are user files, so a broken one never raises.
    player_sprites = load_player_sprites(PLAYER_SPRITES_DIR, layout.square_size)
    pitch_sprite, loaded_pitch = _load_pitch(session, layout), session.pitch
    clock = pygame.time.Clock()
    frames = 0
    running = True
    # Reason: an interactive loop is bounded by the user closing the window;
    # max_frames gives tests an explicit cap.
    while running and (max_frames is None or frames < max_frames):
        events = pygame.event.get()
        for event in events:
            running = handle_event(session, event) and running
        # Reason: one reload per frame, however many events arrived: everything
        # on a focus event, else the pitch alone when its choice changed.
        focused = any(event.type == pygame.WINDOWFOCUSGAINED for event in events)
        if focused:
            player_sprites = load_player_sprites(PLAYER_SPRITES_DIR, layout.square_size)
        if focused or session.pitch != loaded_pitch:
            pitch_sprite, loaded_pitch = _load_pitch(session, layout), session.pitch
        _draw(
            screen,
            layout,
            font,
            die_font,
            sprites,
            player_sprites,
            pitch_sprite,
            session,
        )
        pygame.display.flip()
        clock.tick(FPS)
        frames += 1
    return frames


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
        SpriteError: If a block dice image exists but can't be decoded.
    """
    if max_frames is not None and max_frames <= 0:
        raise ValueError(f"max_frames must be positive, got {max_frames}")

    layout = build_layout()
    # Reason: a broken races.csv is a packaging bug, not a user error, so its
    # RaceError (file, line and field) stops the app before the window opens.
    races = load_races(RACES_FILE)
    session = Session(
        layout,
        ROSTERS_DIR,
        SETUPS_DIR,
        races,
        pitches_dir=PITCH_SPRITES_DIR,
        settings_file=SETTINGS_FILE,
    )
    # Reason: settings.json is a user file, so a broken one becomes the
    # session message instead of stopping the app.
    session.load_settings()
    session.rescan()
    pygame.init()
    try:
        screen = pygame.display.set_mode(layout.window_size)
        pygame.display.set_caption(WINDOW_TITLE)
        font = pygame.font.Font(None, FONT_SIZE)
        die_font = pygame.font.Font(None, DIE_FONT_SIZE)
        # Reason: loaded once, after set_mode, because convert_alpha needs the
        # display mode. Like a broken races.csv, an image that exists but can't
        # be decoded stops the app with a SpriteError naming the file; only a
        # missing image falls back to the face's name.
        sprites = load_block_sprites(DICE_SPRITES_DIR, layout.die_boxes[0].width)
        # Reason: player images are user files, so a broken one never raises.
        player_sprites = load_player_sprites(PLAYER_SPRITES_DIR, layout.square_size)
        clock = pygame.time.Clock()
        frames = 0
        running = True
        # Reason: an interactive loop is bounded by the user closing the window;
        # max_frames gives tests an explicit cap.
        while running and (max_frames is None or frames < max_frames):
            events = pygame.event.get()
            for event in events:
                running = handle_event(session, event) and running
            # Reason: picks up new images once, however many focus events arrive.
            if any(event.type == pygame.WINDOWFOCUSGAINED for event in events):
                player_sprites = load_player_sprites(
                    PLAYER_SPRITES_DIR, layout.square_size
                )
            _draw(screen, layout, font, die_font, sprites, player_sprites, session)
            pygame.display.flip()
            clock.tick(FPS)
            frames += 1
        return frames
    finally:
        pygame.quit()
