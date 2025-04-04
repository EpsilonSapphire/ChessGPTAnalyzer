import pygame
import chess
import chess.engine
import chess.pgn
import tkinter as tk
from tkinter import filedialog
import g4f
import re

pygame.init()


WIDTH, HEIGHT = 600, 600
SQUARE_SIZE = WIDTH // 8
WHITE = (240, 217, 181)
BROWN = (181, 136, 99)
GREEN = (0, 255, 0)
BAR_COLOR = (200, 200, 200)
BAR_WHITE = (255, 255, 255)
BAR_BLACK = (0, 0, 0)
BUTTON_COLOR = (100, 100, 100)
TEXT_COLOR = (255, 255, 255)
FONT = pygame.font.Font(None, 36)
PIECE_IMAGES = {}
analysis_cache = {}

SETTINGS_WIDTH = 200
SETTINGS_BG = (180, 180, 180)

models = {
    "GPT-4": g4f.models.gpt_4,
    "GPT-3.5 Turbo": g4f.models.gpt_3_5_turbo
}
selected_model = list(models.keys())[0]
selected_language = "English"
play_against_stockfish = False

game_name = "Неизвестная партия"
white_player = "Белые"
black_player = "Чёрные"


screen = pygame.display.set_mode((WIDTH + 1500, HEIGHT + 100))
pygame.display.set_caption("Chess Analyzer")



def load_piece_images():
    pieces = ["p", "r", "n", "b", "q", "k", "P", "R", "N", "B", "Q", "K"]
    for piece in pieces:
        filename = f"images/{piece}.png" if piece.islower() else f"images/m{piece}.png"
        PIECE_IMAGES[piece] = pygame.image.load(filename)
        PIECE_IMAGES[piece] = pygame.transform.scale(PIECE_IMAGES[piece], (SQUARE_SIZE, SQUARE_SIZE))


load_piece_images()

# Инициализация доски
board = chess.Board()
move_history = []
current_move_index = -1
score = 0


def draw_board():
    for row in range(8):
        for col in range(8):
            color = WHITE if (row + col) % 2 == 0 else BROWN
            pygame.draw.rect(screen, color, (col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE))


def draw_pieces():
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            x, y = chess.square_file(square), 7 - chess.square_rank(square)
            screen.blit(PIECE_IMAGES[piece.symbol()], (x * SQUARE_SIZE, y * SQUARE_SIZE))


def draw_buttons():
    load_button = pygame.Rect(50, HEIGHT + 10, 150, 30)
    prev_button = pygame.Rect(250, HEIGHT + 10, 50, 30)
    next_button = pygame.Rect(350, HEIGHT + 10, 50, 30)
    set_button = pygame.Rect(450, HEIGHT + 10, 150, 30)

    pygame.draw.rect(screen, BUTTON_COLOR, load_button)
    pygame.draw.rect(screen, BUTTON_COLOR, prev_button)
    pygame.draw.rect(screen, BUTTON_COLOR, next_button)
    pygame.draw.rect(screen, BUTTON_COLOR, set_button)

    if selected_language == "English":
        screen.blit(FONT.render("Load PGN", True, TEXT_COLOR), (60, HEIGHT + 15))
        screen.blit(FONT.render("SETTINGS", True, TEXT_COLOR), (450, HEIGHT + 15))
    else:
        screen.blit(FONT.render("Загрузить PGN", True, TEXT_COLOR), (60, HEIGHT + 15))
        screen.blit(FONT.render("НАСТРОЙКИ", True, TEXT_COLOR), (450, HEIGHT + 15))



    screen.blit(FONT.render("<", True, TEXT_COLOR), (265, HEIGHT + 15))
    screen.blit(FONT.render(">", True, TEXT_COLOR), (365, HEIGHT + 15))


    return load_button, prev_button, next_button, set_button


def draw_arrows():
    if current_move_index >= 0:
        move = move_history[current_move_index]
        start_square = move.from_square
        end_square = move.to_square
        start_x, start_y = chess.square_file(start_square), 7 - chess.square_rank(start_square)
        end_x, end_y = chess.square_file(end_square), 7 - chess.square_rank(end_square)

        pygame.draw.line(screen, GREEN, ((start_x + 0.5) * SQUARE_SIZE, (start_y + 0.5) * SQUARE_SIZE),
                         ((end_x + 0.5) * SQUARE_SIZE, (end_y + 0.5) * SQUARE_SIZE), 5)


def draw_eval_bar():
    bar_x = WIDTH
    bar_y = 0
    bar_width = 50
    bar_height = HEIGHT
    eval_height = int((score + 1000) / 2000 * HEIGHT)

    pygame.draw.rect(screen, BAR_COLOR, (bar_x, bar_y, bar_width, bar_height))
    pygame.draw.rect(screen, BAR_WHITE, (bar_x, bar_y, bar_width, bar_height - eval_height))
    pygame.draw.rect(screen, BAR_BLACK, (bar_x, bar_y + bar_height - eval_height, bar_width, eval_height))




INFO_BG_COLOR = (220, 220, 220)
INFO_WIDTH = 400
screen = pygame.display.set_mode((WIDTH + INFO_WIDTH + 50, HEIGHT + 50))
pygame.display.set_caption("Chess Analyzer")


def load_pgn():
    global board, move_history, current_move_index, game_name, white_player, black_player
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title="Select PGN File", filetypes=[("PGN Files", "*.pgn")])
    if file_path:
        try:
            with open(file_path, "r") as pgn_file:
                game = chess.pgn.read_game(pgn_file)
                board = game.board()
                move_history = list(game.mainline_moves())
                current_move_index = -1

                # Извлекаем информацию о партии
                game_name = game.headers.get("Event", "Неизвестная партия")
                white_player = game.headers.get("White", "Белые")
                black_player = game.headers.get("Black", "Чёрные")

        except Exception as e:
            print(f"Error loading PGN: {e}")


def get_previous_position():
    temp_board = chess.Board()
    previous_fen = temp_board.fen()
    for i, move in enumerate(move_history[:current_move_index]):
        temp_board.push(move)
        if i == current_move_index - 2:
            previous_fen = temp_board.fen()

    return previous_fen

def get_current_position():
    temp_board = chess.Board()
    for move in move_history[:current_move_index + 1]:
        temp_board.push(move)
    return temp_board.fen()

INFO_SCROLL_POS = 0


def draw_info_panel(curtext):
    global INFO_SCROLL_POS
    panel_x = WIDTH + 50
    pygame.draw.rect(screen, INFO_BG_COLOR, (panel_x, 0, INFO_WIDTH, HEIGHT))


    words = curtext.split()
    lines = []
    current_line = ""
    line_height = FONT.get_height() + 5

    for word in words:
        test_line = current_line + word + " "
        if FONT.size(test_line)[0] < INFO_WIDTH - 20:
            current_line = test_line
        else:
            lines.append(current_line.strip())
            current_line = word + " "

    lines.append(current_line.strip())

    max_lines_visible = HEIGHT // line_height
    total_lines = len(lines)
    max_scroll = max(0, total_lines - max_lines_visible)
    INFO_SCROLL_POS = max(0, min(INFO_SCROLL_POS, max_scroll))

    y_offset = 10
    for i in range(INFO_SCROLL_POS, min(INFO_SCROLL_POS + max_lines_visible, total_lines)):
        line = lines[i]


        font = FONT
        color = (0, 0, 0)


        if line.startswith("### "):
            font = pygame.font.Font(None, 40)
            color = (0, 0, 255)
            line = line[4:]

        # Жирный текст (**text**)
        elif "**" in line:
            match = re.search(r"\*\*(.*?)\*\*", line)
            if match:
                line = line.replace(f"**{match.group(1)}**", match.group(1))
                font = pygame.font.Font(None, 36)

        # Курсив (*text*)
        elif "*" in line:
            match = re.search(r"\*(.*?)\*", line)
            if match:
                line = line.replace(f"*{match.group(1)}*", match.group(1))
                font = pygame.font.Font(None, 30)

        text_surface = font.render(line, True, color)
        screen.blit(text_surface, (panel_x + 10, y_offset))
        y_offset += line_height


def handle_scroll(event):
    global INFO_SCROLL_POS
    if event.type == pygame.MOUSEBUTTONDOWN:
        if event.button == 4:
            INFO_SCROLL_POS -= 1
        elif event.button == 5:
            INFO_SCROLL_POS += 1
def get_analysis():
    global curtext
    fen = get_current_position()


    if fen in analysis_cache:
        curtext = analysis_cache[fen]
        return

    if selected_language == "English":
        curtext = "Loading..."
    else:
        curtext = "Загрузка..."

    draw_info_panel(curtext)
    pygame.display.flip()
    print(board.fen())
    print(str((get_current_position())))

    model = models[selected_model]

    if selected_language == "Русский":
        messages = [{"role": "user",
                     "content": f"Ты шахматный тренер и должен рассказать тактику и дать советы по позиции. "
                                f"Название партии: {game_name}. "
                                f"Игроки: {white_player} (белые) против {black_player} (чёрные). "
                                f"Название дебюта. "
                                f"Прошлая позиция: {get_previous_position()} "
                                f"Текущая позиция: {get_current_position()}"}]
    else:
        messages = [{"role": "user",
                     "content": f"You are a chess coach and should explain tactics and give advice on the position. "
                                f"Game name: {game_name}. "
                                f"Players: {white_player} (white) vs. {black_player} (black). "
                                f"Opening name. "
                                f"Previous position: {get_previous_position()} "
                                f"Current position: {get_current_position()}"}]

    analysis = g4f.ChatCompletion.create(
        model=model,
        messages=messages
    )

    curtext = analysis
    analysis_cache[fen] = analysis




def draw_settings_panel():
    panel_x = WIDTH + 50
    pygame.draw.rect(screen, INFO_BG_COLOR, (panel_x, 0, INFO_WIDTH, HEIGHT))

    title = FONT.render("Settings", True, (0, 0, 0))
    screen.blit(title, (panel_x + 10, 10))


    model_label = FONT.render("Model:", True, (0, 0, 0))
    screen.blit(model_label, (panel_x + 10, 50))
    model_rect = pygame.Rect(panel_x + 10, 80, SETTINGS_WIDTH - 20, 30)
    pygame.draw.rect(screen, BUTTON_COLOR, model_rect)
    model_text = FONT.render(selected_model, True, TEXT_COLOR)
    screen.blit(model_text, (panel_x + 15, 85))


    lang_label = FONT.render("Language:", True, (0, 0, 0))
    screen.blit(lang_label, (panel_x + 10, 130))
    eng_button = pygame.Rect(panel_x + 10, 160, 80, 30)
    rus_button = pygame.Rect(panel_x + 110, 160, 80, 30)
    pygame.draw.rect(screen, (0, 255, 0) if selected_language == "English" else BUTTON_COLOR, eng_button)
    pygame.draw.rect(screen, (0, 255, 0) if selected_language == "Русский" else BUTTON_COLOR, rus_button)
    screen.blit(FONT.render("EN", True, TEXT_COLOR), (panel_x + 35, 165))
    screen.blit(FONT.render("RU", True, TEXT_COLOR), (panel_x + 135, 165))


    checkbox_rect = pygame.Rect(panel_x + 10, 220, 20, 20)
    pygame.draw.rect(screen, BUTTON_COLOR, checkbox_rect, border_radius=3)
    if play_against_stockfish:
        pygame.draw.line(screen, (0, 255, 0), (panel_x + 12, 230), (panel_x + 25, 215), 3)
        pygame.draw.line(screen, (0, 255, 0), (panel_x + 25, 215), (panel_x + 35, 235), 3)
    mode_label = FONT.render("COMING SOON", True, (0, 0, 0))
    screen.blit(mode_label, (panel_x + 40, 220))

    return model_rect, eng_button, rus_button, checkbox_rect




def handle_settings_click(x, y, model_rect, eng_button, rus_button, checkbox_rect):
    global selected_model, selected_language, play_against_stockfish

    if model_rect.collidepoint(x, y):
        model_keys = list(models.keys())
        selected_index = model_keys.index(selected_model)
        selected_model = model_keys[(selected_index + 1) % len(model_keys)]
    elif eng_button.collidepoint(x, y):
        selected_language = "English"
    elif rus_button.collidepoint(x, y):
        selected_language = "Русский"
    elif checkbox_rect.collidepoint(x, y):
        play_against_stockfish = not play_against_stockfish



def main():
    global current_move_index, curtext
    running = True
    selected_square = None
    move_made = False

    curtext = "Analitics"
    settings_enabled = False
    while running:
        screen.fill((0, 0, 0))
        draw_board()
        draw_pieces()
        draw_arrows()
        draw_eval_bar()
        model_rect = eng_button = rus_button = checkbox_rect = None
        if settings_enabled == True:

            model_rect, eng_button, rus_button, checkbox_rect = draw_settings_panel()
        else:
            draw_info_panel(curtext)

        load_button, prev_button, next_button, set_button = draw_buttons()
        for event in pygame.event.get():
            handle_scroll(event)

            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                x, y = event.pos

                if settings_enabled:
                    if model_rect and model_rect.collidepoint(x, y):
                        handle_settings_click(x, y, model_rect, eng_button, rus_button, checkbox_rect)
                    elif eng_button and eng_button.collidepoint(x, y):
                        handle_settings_click(x, y, model_rect, eng_button, rus_button, checkbox_rect)
                    elif rus_button and rus_button.collidepoint(x, y):
                        handle_settings_click(x, y, model_rect, eng_button, rus_button, checkbox_rect)
                    elif checkbox_rect and checkbox_rect.collidepoint(x, y):
                        handle_settings_click(x, y, model_rect, eng_button, rus_button, checkbox_rect)

                if load_button.collidepoint(x, y):
                    load_pgn()
                if set_button.collidepoint(x, y):
                    settings_enabled = not settings_enabled
                elif prev_button.collidepoint(x, y) and current_move_index > 0:
                    current_move_index -= 1
                    board.undo()

                    curtext = "Loading"
                    pygame.display.flip()
                    get_analysis()
                elif next_button.collidepoint(x, y) and current_move_index < len(move_history) - 1:
                    current_move_index += 1
                    board.push(move_history[current_move_index])
                    get_analysis()
                else:
                    col, row = x // SQUARE_SIZE, y // SQUARE_SIZE
                    square = chess.square(col, 7 - row)

                    if selected_square is None:
                        selected_square = square
                    else:
                        move = chess.Move(selected_square, square)
                        if move in board.legal_moves:
                            board.push(move)
                            move_history.append(move)
                            current_move_index += 1
                            move_made = True
                        selected_square = None

        if move_made:

            move_made = False

        pygame.display.flip()


    pygame.quit()


if __name__ == "__main__":
    main()








