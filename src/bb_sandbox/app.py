"""Pygame window lifecycle and main loop."""

from pathlib import Path

import pygame

from bb_sandbox.dice import BlockFace
from bb_sandbox.interaction import EditKey
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
    draw_team_setups,
    load_block_sprites,
    load_pitch_sprite,
    load_player_sprites,
)
from bb_sandbox.session import (
    DeleteFile,
    DeployTeamSetup,
    FileRequest,
    ImportRoster,
    LoadSetup,
    OpenTeamSetups,
    RenameFile,
    SaveRoster,
    SaveSettings,
    SaveSetup,
    SaveTeamSetup,
    Screen,
    Session,
)

WINDOW_TITLE = "Blood Bowl Sandbox"
FPS = 60
FONT_SIZE = 20
# Reason: numbers on the dice are drawn bigger than the rest of the text.
DIE_FONT_SIZE = 40
# Reason: player comments are drawn smaller, so 4 characters fit on a square.
COMMENT_FONT_SIZE = 14
ROSTERS_DIR = Path("rosters")
SETUPS_DIR = Path("setups")
PLAYER_SPRITES_DIR = Path("sprites")
PITCH_SPRITES_DIR = PLAYER_SPRITES_DIR / "pitch"
SETTINGS_FILE = Path("settings.json")
LANGUAGES_DIR = Path("languages")
LEFT_BUTTON = 1
RIGHT_BUTTON = 3
# Reason: holding Backspace in the name box or a comment deletes repeatedly.
KEY_REPEAT_DELAY_MS = 400
KEY_REPEAT_INTERVAL_MS = 40
# Reason: session and interaction never see Pygame, so the editing keys are
# mapped here; any other key is ignored.
KEYS = {
    pygame.K_BACKSPACE: EditKey.BACKSPACE,
    pygame.K_RETURN: EditKey.ENTER,
    pygame.K_KP_ENTER: EditKey.ENTER,
    pygame.K_ESCAPE: EditKey.ESCAPE,
    pygame.K_DELETE: EditKey.DELETE,
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
        case SaveSettings():
            session.save_settings()
        case OpenTeamSetups():
            session.open_team_setups()
        case DeployTeamSetup(side=side, path=path):
            session.deploy_team_setup(side, path)
        case SaveTeamSetup(side=side, name=name):
            session.save_team_setup(side, name)
            session.rescan()
        case DeleteFile(path=path):
            session.delete(path)
            # Reason: the deleted file leaves its list right away.
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
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == RIGHT_BUTTON:
        # Reason: Ctrl is read here so session and interaction stay free of Pygame.
        ctrl = bool(pygame.key.get_mods() & pygame.KMOD_CTRL)
        session.right_click(event.pos, ctrl=ctrl)
    elif event.type == pygame.MOUSEBUTTONUP and event.button == LEFT_BUTTON:
        session.release(event.pos)
    elif event.type == pygame.MOUSEBUTTONUP and event.button == RIGHT_BUTTON:
        session.right_release(event.pos)
    elif event.type == pygame.MOUSEMOTION:
        session.move(event.pos)
    elif event.type == pygame.WINDOWFOCUSGAINED:
        # Reason: picks up roster, setup, pitch image and language files
        # added or renamed in Explorer while the app was in the background.
        # Languages are read here only, not on every rescan after a save.
        session.load_languages()
        session.rescan()
    return True


def _draw(
    surface: pygame.Surface,
    layout: Layout,
    font: pygame.font.Font,
    die_font: pygame.font.Font,
    comment_font: pygame.font.Font,
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
        font (pygame.font.Font): Font for all text but dice numbers and comments.
        die_font (pygame.font.Font): Bigger font for the numbers on dice.
        comment_font (pygame.font.Font): Smaller font for player comments.
        sprites (dict[BlockFace, pygame.Surface]): Block dice images, from
            load_block_sprites.
        player_sprites (PlayerSprites): Player images, from load_player_sprites.
        pitch_sprite (PitchSprite): The pitch image, from load_pitch_sprite.
        session (Session): The session to draw.
    """
    # Reason: a broken player or pitch image or language file stays reported
    # until it is fixed, without hiding the session's own feedback.
    message = (
        session.message
        or player_sprites.problem
        or pitch_sprite.problem
        or session.language_problem
    )
    texts = session.texts
    if session.screen is Screen.SANDBOX and session.interaction is not None:
        view = session.interaction.view()
        board, pitch = session.board, pitch_sprite.image
        draw_sandbox(
            surface,
            layout,
            font,
            texts,
            comment_font,
            board,
            view,
            player_sprites,
            pitch,
            message,
        )
        draw_dice(surface, layout, font, texts, die_font, session.last_roll, sprites)
    elif session.screen is Screen.TEAM_SETUPS:
        view = session.team_setups_view()
        draw_team_setups(surface, layout, font, texts, view, message)
    elif session.screen is Screen.RACES:
        draw_races(surface, layout, font, texts, session.races, message)
    elif session.screen is Screen.OPTIONS:
        draw_options(surface, layout, font, texts, session.options_view(), message)
    elif session.screen is Screen.BUILDER and session.builder is not None:
        draw_builder(surface, layout, font, texts, session.builder, message)
    else:
        draw_menu(surface, layout, font, texts, session.menu_view(), message)
    # Reason: drawn last so the box sits over whichever screen opened it.
    if session.name_view is not None:
        draw_name_box(surface, layout, font, texts, session.name_view)


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
    comment_font = pygame.font.Font(None, COMMENT_FONT_SIZE)
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
            comment_font,
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
        languages_dir=LANGUAGES_DIR,
    )
    # Reason: language files are user files too, so a broken one is skipped
    # and reported. They are read first so the saved language can be found,
    # and only here: rescan() doesn't read them again.
    session.load_languages()
    # Reason: settings.json is a user file, so a broken one becomes the
    # session message instead of stopping the app.
    session.load_settings()
    session.rescan()
    pygame.init()
    try:
        screen = pygame.display.set_mode(layout.window_size)
        pygame.display.set_caption(WINDOW_TITLE)
        # Reason: typed text arrives as TEXTINPUT events, which pygame 2 sends
        # by default; only the editing keys need KEYDOWN repeats.
        pygame.key.set_repeat(KEY_REPEAT_DELAY_MS, KEY_REPEAT_INTERVAL_MS)
        return _run_frames(screen, layout, session, max_frames)
    finally:
        pygame.quit()
