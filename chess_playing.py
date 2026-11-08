import pygame
import chess
import sys
import math

pygame.init()

# ------------------------------------------------------------
# WINDOW AND BOARD SETTINGS
# ------------------------------------------------------------
WIDTH, HEIGHT = 1000, 760
BOARD_SIZE = 640
SQ = BOARD_SIZE // 8
BOARD_X, BOARD_Y = 30, 60
PANEL_X = 710

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("2D Chess Board Game - Lighting and Shading")
clock = pygame.time.Clock()

TITLE = pygame.font.SysFont("arial", 30, bold=True)
FONT = pygame.font.SysFont("arial", 20)
SMALL = pygame.font.SysFont("arial", 15)

LIGHT = (232, 237, 243)
DARK = (91, 112, 139)
SELECT = (28, 190, 190)
LAST = (246, 190, 75)
MOVE_DOT = (22, 163, 130)
BG = (30, 38, 48)
PANEL = (43, 53, 66)

# Lighting settings: light comes from the upper-left.
LIGHT_POSITION = (BOARD_X + 100, BOARD_Y + 80)
AMBIENT_STRENGTH = 0.38
DIFFUSE_STRENGTH = 0.62

board = chess.Board()
selected_square = None
legal_targets = []
move_history = []
scroll_offset = 0
message = "White to move"
running = True


# ------------------------------------------------------------
# GENERAL DRAWING HELPERS
# ------------------------------------------------------------
def draw_text(surface, text, font, color, x, y):
    image = font.render(text, True, color)
    surface.blit(image, (x, y))


def mix_color(base, light, amount):
    """Blend two RGB colors. amount=0 gives base; amount=1 gives light."""
    amount = max(0.0, min(1.0, amount))
    return tuple(
        int(base[i] * (1 - amount) + light[i] * amount)
        for i in range(3)
    )


def draw_soft_shadow(surface, center, scale):
    """
    Draw a soft elliptical shadow using several transparent ellipses.
    This is a 2D approximation of a cast shadow.
    """
    cx, cy = center
    shadow_w = max(2, int(76 * scale))
    shadow_h = max(2, int(25 * scale))

    shadow_surface = pygame.Surface(
        (shadow_w + 12, shadow_h + 12), pygame.SRCALPHA
    )

    # Larger, more transparent ellipses form the soft outer edge.
    for i in range(8, 0, -1):
        factor = i / 8
        w = int(shadow_w * factor)
        h = int(shadow_h * factor)
        alpha = int(5 + (8 - i) * 3)

        rect = pygame.Rect(
            (shadow_w + 12 - w) // 2,
            (shadow_h + 12 - h) // 2,
            w,
            h
        )
        pygame.draw.ellipse(shadow_surface, (0, 0, 0, alpha), rect)

    surface.blit(
        shadow_surface,
        (int(cx - shadow_w / 2 - 6), int(cy + 23 * scale - shadow_h / 2 - 6))
    )


def draw_piece(surface, piece, center, square_size):
    """
    Draw chess pieces with 2D vector primitives.
    Lighting/shading techniques used:
    - soft transparent shadow below each piece
    - lighter and darker face colors
    - small specular-style highlights
    - directional shading to suggest a light source at upper-left
    """
    cx, cy = center
    s = square_size / 100.0
    white = piece.color == chess.WHITE

    if white:
        fill = (250, 248, 239)
        edge = (70, 78, 91)
        shade = (205, 211, 218)
        accent = (190, 145, 65)
        light_face = (255, 255, 250)
        dark_face = (174, 181, 191)
    else:
        fill = (39, 47, 61)
        edge = (12, 17, 26)
        shade = (83, 96, 114)
        accent = (221, 184, 104)
        light_face = (105, 118, 137)
        dark_face = (22, 29, 41)

    def pt(x, y):
        return (int(cx + x * s), int(cy + y * s))

    def polygon(points, color, outline=edge, width=2):
        pts = [pt(x, y) for x, y in points]
        pygame.draw.polygon(surface, color, pts)
        if outline:
            pygame.draw.polygon(
                surface, outline, pts, max(1, int(width * s))
            )

    def ellipse(x, y, w, h, color, outline=edge, width=2):
        rect = pygame.Rect(
            int(cx + (x - w / 2) * s),
            int(cy + (y - h / 2) * s),
            max(1, int(w * s)),
            max(1, int(h * s))
        )
        pygame.draw.ellipse(surface, color, rect)
        if outline:
            pygame.draw.ellipse(
                surface, outline, rect, max(1, int(width * s))
            )

    def line(points, color, width=3):
        pygame.draw.lines(
            surface, color, False,
            [pt(x, y) for x, y in points],
            max(1, int(width * s))
        )

    def highlight(x, y, w, h, alpha=100):
        """Small translucent white ellipse to imitate specular reflection."""
        hw = max(2, int(w * s))
        hh = max(2, int(h * s))
        highlight_surface = pygame.Surface((hw + 4, hh + 4), pygame.SRCALPHA)
        pygame.draw.ellipse(
            highlight_surface, (255, 255, 255, alpha),
            (2, 2, hw, hh)
        )
        surface.blit(
            highlight_surface,
            (int(cx + (x - w / 2) * s) - 2,
             int(cy + (y - h / 2) * s) - 2)
        )

    # Shadow is drawn before the piece so it stays underneath.
    draw_soft_shadow(surface, center, s)

    kind = piece.piece_type

    # Shared pedestal: top surface is lighter; lower rim is darker.
    ellipse(0, 31, 58, 12, dark_face, edge, 2)
    pygame.draw.rect(
        surface, shade,
        (int(cx - 25 * s), int(cy + 18 * s),
         max(1, int(50 * s)), max(1, int(10 * s))),
        border_radius=max(2, int(4 * s))
    )
    pygame.draw.rect(
        surface, edge,
        (int(cx - 25 * s), int(cy + 18 * s),
         max(1, int(50 * s)), max(1, int(10 * s))),
        max(1, int(2 * s)), border_radius=max(2, int(4 * s))
    )
    ellipse(0, 18, 50, 10, light_face, edge, 2)
    highlight(-10, 16, 22, 3, 65)

    if kind == chess.PAWN:
        polygon([(-13, 17), (-10, -2), (10, -2), (13, 17)], fill)
        # Left face catches more light; right face is darker.
        polygon([(-13, 17), (-10, -2), (0, -2), (0, 17)], light_face, None)
        polygon([(0, -2), (10, -2), (13, 17), (0, 17)], dark_face, None)
        ellipse(0, -15, 27, 27, fill, edge, 2)
        ellipse(-5, -20, 6, 6, light_face, None)
        highlight(-7, -23, 9, 5, 95)

    elif kind == chess.ROOK:
        body = pygame.Rect(
            int(cx - 19 * s), int(cy - 27 * s),
            max(1, int(38 * s)), max(1, int(47 * s))
        )
        pygame.draw.rect(surface, fill, body)
        pygame.draw.rect(surface, edge, body, max(1, int(2 * s)))
        pygame.draw.rect(
            surface, light_face,
            (int(cx - 15 * s), int(cy - 23 * s),
             max(1, int(8 * s)), max(1, int(37 * s)))
        )
        pygame.draw.rect(
            surface, dark_face,
            (int(cx + 9 * s), int(cy - 23 * s),
             max(1, int(7 * s)), max(1, int(37 * s)))
        )
        for x in (-16, -5, 6):
            r = pygame.Rect(
                int(cx + x * s), int(cy - 38 * s),
                max(1, int(10 * s)), max(1, int(14 * s))
            )
            pygame.draw.rect(surface, fill, r)
            pygame.draw.rect(surface, edge, r, max(1, int(2 * s)))
        line([(-19, -25), (19, -25)], accent, 2)
        highlight(-10, -20, 8, 25, 55)

    elif kind == chess.KNIGHT:
        polygon(
            [(-20, 18), (-18, 2), (-10, -8), (-18, -20),
             (-8, -37), (8, -32), (21, -15), (14, -4),
             (19, 18)], fill
        )
        polygon(
            [(-20, 18), (-18, 2), (-10, -8), (-8, -37),
             (0, -30), (0, 18)], light_face, None
        )
        polygon([(-8, -31), (-3, -43), (8, -33), (2, -23)], shade)
        ellipse(6, -25, 5, 5, accent, edge, 1)
        line([(-8, -8), (9, -5), (15, 2)], shade, 3)
        highlight(-8, -30, 8, 5, 75)

    elif kind == chess.BISHOP:
        polygon(
            [(-15, 17), (-11, -5), (-7, -16), (-13, -27),
             (0, -43), (13, -27), (7, -16), (11, -5),
             (15, 17)], fill
        )
        polygon(
            [(-15, 17), (-11, -5), (-7, -16), (0, -43),
             (0, 17)], light_face, None
        )
        ellipse(0, -39, 11, 11, accent, edge, 1)
        line([(-5, -29), (5, -20)], edge, 3)
        ellipse(0, -7, 31, 8, shade, edge, 1)
        highlight(-6, -28, 8, 5, 85)

    elif kind == chess.QUEEN:
        polygon(
            [(-20, 17), (-15, -8), (-22, -29), (-8, -18),
             (0, -39), (8, -18), (22, -29), (15, -8),
             (20, 17)], fill
        )
        polygon(
            [(-20, 17), (-15, -8), (-22, -29), (-8, -18),
             (0, -39), (0, 17)], light_face, None
        )
        for x, y in [(-22, -29), (-8, -18), (0, -40), (8, -18), (22, -29)]:
            ellipse(x, y, 9, 9, accent, edge, 1)
        line([(-15, -8), (15, -8)], accent, 2)
        highlight(-8, -24, 10, 5, 80)

    elif kind == chess.KING:
        polygon(
            [(-18, 17), (-13, -9), (-9, -24), (9, -24),
             (13, -9), (18, 17)], fill
        )
        polygon(
            [(-18, 17), (-13, -9), (-9, -24), (0, -24),
             (0, 17)], light_face, None
        )
        pygame.draw.rect(
            surface, fill,
            (int(cx - 3 * s), int(cy - 47 * s),
             max(1, int(6 * s)), max(1, int(29 * s)))
        )
        pygame.draw.rect(
            surface, edge,
            (int(cx - 3 * s), int(cy - 47 * s),
             max(1, int(6 * s)), max(1, int(29 * s))),
            max(1, int(1.5 * s))
        )
        pygame.draw.rect(
            surface, light_face,
            (int(cx - 13 * s), int(cy - 39 * s),
             max(1, int(26 * s)), max(1, int(6 * s)))
        )
        pygame.draw.rect(
            surface, edge,
            (int(cx - 13 * s), int(cy - 39 * s),
             max(1, int(26 * s)), max(1, int(6 * s))),
            max(1, int(1.5 * s))
        )
        line([(-10, -7), (10, -7)], accent, 2)
        highlight(-7, -19, 7, 5, 85)


# ------------------------------------------------------------
# BOARD AND GAME STATUS
# ------------------------------------------------------------
def square_rect(square):
    file_no = chess.square_file(square)
    rank_no = chess.square_rank(square)
    x = BOARD_X + file_no * SQ
    y = BOARD_Y + (7 - rank_no) * SQ
    return pygame.Rect(x, y, SQ, SQ)


def draw_square_overlay(square, color, alpha=90):
    overlay = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
    overlay.fill((*color, alpha))
    screen.blit(overlay, square_rect(square).topleft)


def current_status():
    if board.is_checkmate():
        winner = "Black" if board.turn == chess.WHITE else "White"
        return f"CHECKMATE - {winner} wins!"
    if board.is_stalemate():
        return "DRAW - Stalemate"
    if board.is_insufficient_material():
        return "DRAW - Insufficient material"
    if board.is_seventyfive_moves():
        return "DRAW - 75-move rule"
    if board.is_fivefold_repetition():
        return "DRAW - Fivefold repetition"
    if board.is_check():
        return ("White" if board.turn else "Black") + " is in CHECK"
    return ("White" if board.turn else "Black") + " to move"


def draw_board_lighting():
    """
    Add a subtle board-wide light wash from the upper-left.
    The transparent overlay gives the board a gentle lighting gradient.
    """
    lighting = pygame.Surface((BOARD_SIZE, BOARD_SIZE), pygame.SRCALPHA)

    # Broad transparent light near the upper-left corner.
    for radius in range(BOARD_SIZE, 0, -12):
        alpha = max(0, int(13 * (1 - radius / BOARD_SIZE)))
        if alpha > 0:
            pygame.draw.circle(
                lighting, (255, 248, 220, alpha),
                (0, 0), radius
            )

    screen.blit(lighting, (BOARD_X, BOARD_Y))


def draw_board():
    # Chessboard squares.
    for rank in range(8):
        for file_no in range(8):
            x = BOARD_X + file_no * SQ
            y = BOARD_Y + rank * SQ
            color = LIGHT if (rank + file_no) % 2 == 0 else DARK
            pygame.draw.rect(screen, color, (x, y, SQ, SQ))

    # Subtle directional lighting on the board.
    draw_board_lighting()

    # Last move highlight.
    if board.move_stack:
        last = board.peek()
        for sq in (last.from_square, last.to_square):
            draw_square_overlay(sq, LAST, 85)

    # Selected square.
    if selected_square is not None:
        draw_square_overlay(selected_square, SELECT, 75)
        pygame.draw.rect(
            screen, (0, 235, 210), square_rect(selected_square), 5
        )

    # Legal move indicators.
    for target in legal_targets:
        rect = square_rect(target)
        if board.piece_at(target):
            pygame.draw.circle(
                screen, (15, 135, 105), rect.center, int(SQ * 0.39), 5
            )
        else:
            pygame.draw.circle(
                screen, (15, 135, 105), rect.center, int(SQ * 0.105)
            )
            pygame.draw.circle(
                screen, (235, 255, 248), rect.center,
                int(SQ * 0.105), 2
            )

    # Draw chess pieces with shadows and shading.
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            rect = square_rect(square)
            draw_piece(screen, piece, rect.center, SQ)

    # Board frame and coordinates.
    pygame.draw.rect(
        screen, (35, 45, 58),
        (BOARD_X, BOARD_Y, BOARD_SIZE, BOARD_SIZE), 3
    )

    for file_no in range(8):
        letter = chr(ord("a") + file_no)
        x = BOARD_X + file_no * SQ + SQ - 18
        y = BOARD_Y + BOARD_SIZE - 20
        draw_text(screen, letter, SMALL, (45, 55, 68), x, y)

    for rank in range(8):
        number = str(8 - rank)
        x = BOARD_X + 4
        y = BOARD_Y + rank * SQ + 3
        draw_text(screen, number, SMALL, (45, 55, 68), x, y)


# ------------------------------------------------------------
# SIDE PANEL
# ------------------------------------------------------------
def draw_panel():
    pygame.draw.rect(
        screen, PANEL, (PANEL_X, 45, 260, 680), border_radius=14
    )

    draw_text(screen, "2D CHESS", TITLE, (255, 255, 255), PANEL_X + 22, 68)
    draw_text(
        screen, "Python + Pygame", SMALL,
        (190, 205, 220), PANEL_X + 24, 108
    )

    status = current_status()
    draw_text(
        screen, status, FONT, (255, 220, 125), PANEL_X + 20, 150
    )

    turn_text = "White" if board.turn else "Black"
    draw_text(
        screen, "Turn: " + turn_text, FONT,
        (240, 240, 240), PANEL_X + 20, 188
    )
    draw_text(
        screen, "MOVE HISTORY", FONT,
        (255, 255, 255), PANEL_X + 20, 235
    )

    # Reconstruct algebraic move history.
    moves = []
    temp = chess.Board()

    for idx, move in enumerate(board.move_stack):
        san = temp.san(move)
        if idx % 2 == 0:
            moves.append(f"{idx // 2 + 1}. {san}")
        else:
            moves[-1] += f"   {san}"
        temp.push(move)

    visible = moves[scroll_offset:scroll_offset + 15]
    for i, item in enumerate(visible):
        draw_text(
            screen, item, SMALL, (225, 230, 235),
            PANEL_X + 22, 275 + i * 23
        )

    # Buttons.
    buttons = [
        (pygame.Rect(PANEL_X + 18, 630, 105, 38), "UNDO"),
        (pygame.Rect(PANEL_X + 137, 630, 105, 38), "RESTART"),
    ]

    for rect, label in buttons:
        pygame.draw.rect(
            screen, (77, 111, 145), rect, border_radius=8
        )
        label_img = FONT.render(label, True, (255, 255, 255))
        screen.blit(label_img, label_img.get_rect(center=rect.center))

    draw_text(
        screen, "Teal dots = legal moves", SMALL,
        (150, 230, 210), PANEL_X + 18, 686
    )
    draw_text(
        screen, "Amber = last move", SMALL,
        (245, 210, 145), PANEL_X + 18, 705
    )


# ------------------------------------------------------------
# MOUSE INPUT AND CHESS MOVES
# ------------------------------------------------------------
def board_square_from_mouse(pos):
    x, y = pos

    if not (
        BOARD_X <= x < BOARD_X + BOARD_SIZE
        and BOARD_Y <= y < BOARD_Y + BOARD_SIZE
    ):
        return None

    file_no = (x - BOARD_X) // SQ
    rank_no = 7 - ((y - BOARD_Y) // SQ)
    return chess.square(file_no, rank_no)


def choose_promotion(move):
    choices = [
        (chess.QUEEN, "Queen"),
        (chess.ROOK, "Rook"),
        (chess.BISHOP, "Bishop"),
        (chess.KNIGHT, "Knight"),
    ]

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))

    box = pygame.Rect(260, 300, 480, 150)
    pygame.draw.rect(screen, (43, 53, 66), box, border_radius=14)
    draw_text(
        screen, "Choose promotion", TITLE,
        (255, 255, 255), 385, 315
    )

    rects = []
    for i, (piece_type, name) in enumerate(choices):
        rect = pygame.Rect(285 + i * 110, 375, 95, 48)
        pygame.draw.rect(
            screen, (77, 111, 145), rect, border_radius=8
        )
        label = FONT.render(name, True, (255, 255, 255))
        screen.blit(label, label.get_rect(center=rect.center))
        rects.append((rect, piece_type))

    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return chess.Move(
                    move.from_square, move.to_square,
                    promotion=chess.QUEEN
                )

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for rect, piece_type in rects:
                    if rect.collidepoint(event.pos):
                        return chess.Move(
                            move.from_square, move.to_square,
                            promotion=piece_type
                        )

        clock.tick(30)


def handle_square_click(square):
    global selected_square, legal_targets, message

    if square is None or board.is_game_over():
        return

    piece = board.piece_at(square)

    if selected_square is None:
        if piece and piece.color == board.turn:
            selected_square = square
            legal_targets = [
                move.to_square
                for move in board.legal_moves
                if move.from_square == square
            ]
        return

    candidates = [
        move for move in board.legal_moves
        if move.from_square == selected_square
        and move.to_square == square
    ]

    if candidates:
        move = candidates[0]

        if any(candidate.promotion for candidate in candidates):
            move = choose_promotion(move)
            if move is None:
                return

        move_history.append(board.fen())
        board.push(move)
        message = current_status()
        selected_square = None
        legal_targets = []

    elif piece and piece.color == board.turn:
        selected_square = square
        legal_targets = [
            move.to_square
            for move in board.legal_moves
            if move.from_square == square
        ]

    else:
        selected_square = None
        legal_targets = []


# ------------------------------------------------------------
# MAIN GAME LOOP
# ------------------------------------------------------------
while running:
    clock.tick(60)
    screen.fill(BG)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos

            undo_rect = pygame.Rect(PANEL_X + 18, 630, 105, 38)
            restart_rect = pygame.Rect(PANEL_X + 137, 630, 105, 38)

            if undo_rect.collidepoint(pos):
                if board.move_stack:
                    board.pop()
                selected_square = None
                legal_targets = []

            elif restart_rect.collidepoint(pos):
                board.reset()
                selected_square = None
                legal_targets = []
                scroll_offset = 0

            else:
                handle_square_click(board_square_from_mouse(pos))

        elif event.type == pygame.MOUSEWHEEL:
            max_scroll = max(0, len(board.move_stack) // 2 - 14)
            scroll_offset = max(
                0, min(max_scroll, scroll_offset - event.y)
            )

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

            elif event.key == pygame.K_u and board.move_stack:
                board.pop()
                selected_square = None
                legal_targets = []

            elif event.key == pygame.K_r:
                board.reset()
                selected_square = None
                legal_targets = []
                scroll_offset = 0

    draw_board()
    draw_panel()
    pygame.display.flip()

pygame.quit()
sys.exit()
