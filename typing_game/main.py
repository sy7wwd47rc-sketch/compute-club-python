import csv
import json
import os
import random
import time
import uuid
from datetime import datetime

import pygame


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WORDS_FILE = os.path.join(BASE_DIR, "words.json")
PLAYERS_FILE = os.path.join(BASE_DIR, "players.json")
RESULTS_DIR = os.path.join(BASE_DIR, "results")
SESSIONS_CSV = os.path.join(RESULTS_DIR, "sessions.csv")
KEYS_CSV = os.path.join(RESULTS_DIR, "key_presses.csv")

WIDTH = 1000
HEIGHT = 700
FPS = 60

SESSION_WORD_COUNT = 10

THEMES = {
    "cream": {
        "name": "Cream",
        "background": (245, 236, 210),
        "text": (35, 35, 35),
        "highlight": (40, 90, 160),
        "good": (20, 130, 60),
        "bad": (170, 40, 40),
        "panel": (255, 250, 235)
    },
    "white": {
        "name": "White",
        "background": (255, 255, 255),
        "text": (25, 25, 25),
        "highlight": (20, 90, 180),
        "good": (20, 130, 60),
        "bad": (170, 40, 40),
        "panel": (240, 240, 240)
    },
    "blue": {
        "name": "Soft Blue",
        "background": (220, 235, 250),
        "text": (20, 35, 60),
        "highlight": (0, 80, 170),
        "good": (20, 120, 70),
        "bad": (170, 50, 50),
        "panel": (235, 245, 255)
    },
    "yellow": {
        "name": "Pale Yellow",
        "background": (255, 248, 190),
        "text": (35, 35, 35),
        "highlight": (20, 80, 160),
        "good": (20, 130, 60),
        "bad": (170, 40, 40),
        "panel": (255, 252, 220)
    },
    "dark": {
        "name": "Dark",
        "background": (20, 25, 40),
        "text": (245, 245, 245),
        "highlight": (120, 190, 255),
        "good": (120, 230, 150),
        "bad": (255, 120, 120),
        "panel": (35, 42, 65)
    },
    "pink": {
        "name": "Pink",
        "background": (255, 225, 238),
        "text": (45, 25, 35),
        "highlight": (160, 45, 110),
        "good": (20, 130, 60),
        "bad": (170, 40, 40),
        "panel": (255, 240, 247)
    }
}


def ensure_files():
    os.makedirs(RESULTS_DIR, exist_ok=True)

    if not os.path.exists(SESSIONS_CSV):
        with open(SESSIONS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "session_id",
                "datetime",
                "player",
                "age",
                "level_start",
                "level_end",
                "theme",
                "words_attempted",
                "letters_attempted",
                "correct_letters",
                "wrong_letters",
                "accuracy_percent",
                "avg_reaction_time_seconds",
                "total_time_seconds"
            ])

    if not os.path.exists(KEYS_CSV):
        with open(KEYS_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "session_id",
                "datetime",
                "player",
                "age",
                "level",
                "theme",
                "word",
                "letter_position",
                "target_letter",
                "pressed_key",
                "correct",
                "reaction_time_seconds"
            ])


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_players(players):
    with open(PLAYERS_FILE, "w", encoding="utf-8") as f:
        json.dump(players, f, indent=2)


def pick_words(words_data, level, count):
    levels = words_data["levels"]
    level_key = str(level)

    available = list(levels.get(level_key, []))

    if level > 1:
        easier_key = str(level - 1)
        available.extend(levels.get(easier_key, [])[:6])

    if not available:
        available = levels["1"]

    random.shuffle(available)
    return available[:count]


def draw_text(screen, text, font, color, center):
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=center)
    screen.blit(surf, rect)
    return rect


def draw_button(screen, rect, label, font, theme, selected=False):
    pygame.draw.rect(screen, theme["panel"], rect, border_radius=16)
    border_color = theme["highlight"] if selected else theme["text"]
    pygame.draw.rect(screen, border_color, rect, width=3, border_radius=16)
    draw_text(screen, label, font, theme["text"], rect.center)


def wait_for_click_or_key():
    # Small helper to prevent accidental double-click flow.
    pygame.time.wait(150)


def select_from_buttons(screen, title, options, theme, default_index=0):
    clock = pygame.time.Clock()
    title_font = pygame.font.SysFont(None, 70)
    button_font = pygame.font.SysFont(None, 44)
    small_font = pygame.font.SysFont(None, 30)

    selected = default_index
    button_rects = []

    while True:
        screen.fill(theme["background"])
        draw_text(screen, title, title_font, theme["text"], (WIDTH // 2, 90))
        draw_text(
            screen,
            "Use mouse, number keys, up/down, then Enter",
            small_font,
            theme["text"],
            (WIDTH // 2, 145)
        )

        button_rects.clear()
        start_y = 210
        for i, option in enumerate(options):
            rect = pygame.Rect(250, start_y + i * 70, 500, 55)
            button_rects.append(rect)
            label = f"{i + 1}. {option}"
            draw_button(screen, rect, label, button_font, theme, selected=(i == selected))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, rect in enumerate(button_rects):
                    if rect.collidepoint(event.pos):
                        wait_for_click_or_key()
                        return options[i]

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = max(0, selected - 1)
                elif event.key == pygame.K_DOWN:
                    selected = min(len(options) - 1, selected + 1)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    wait_for_click_or_key()
                    return options[selected]
                elif pygame.K_1 <= event.key <= pygame.K_9:
                    index = event.key - pygame.K_1
                    if index < len(options):
                        wait_for_click_or_key()
                        return options[index]

        clock.tick(FPS)


def show_message(screen, message, theme, seconds=1.2):
    font = pygame.font.SysFont(None, 64)
    small = pygame.font.SysFont(None, 34)
    screen.fill(theme["background"])
    draw_text(screen, message, font, theme["text"], (WIDTH // 2, HEIGHT // 2 - 20))
    draw_text(screen, "Press any key to continue", small, theme["text"], (WIDTH // 2, HEIGHT // 2 + 60))
    pygame.display.flip()

    start = time.time()
    while time.time() - start < seconds:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise SystemExit
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                return
        pygame.time.wait(20)


def play_session(screen, player_name, player_profile, theme_key, words_data):
    theme = THEMES[theme_key]
    clock = pygame.time.Clock()

    level_start = int(player_profile.get("current_level", 1))
    age = int(player_profile.get("age", 7))
    session_id = str(uuid.uuid4())
    session_datetime = datetime.now().isoformat(timespec="seconds")

    words = pick_words(words_data, level_start, SESSION_WORD_COUNT)

    big_font = pygame.font.SysFont(None, 150)
    word_font = pygame.font.SysFont(None, 105)
    normal_font = pygame.font.SysFont(None, 44)
    small_font = pygame.font.SysFont(None, 30)

    key_rows = []
    correct_letters = 0
    wrong_letters = 0
    reaction_times = []
    total_start = time.time()

    for word_index, word in enumerate(words, start=1):
        current_pos = 0
        feedback = "Type each letter as it pops up"
        feedback_color = theme["text"]

        while current_pos < len(word):
            target = word[current_pos]
            letter_start = time.time()
            waiting_for_correct = True

            while waiting_for_correct:
                screen.fill(theme["background"])

                draw_text(
                    screen,
                    f"{player_name}  |  Level {level_start}  |  Word {word_index}/{len(words)}",
                    small_font,
                    theme["text"],
                    (WIDTH // 2, 35)
                )

                pygame.draw.rect(screen, theme["panel"], pygame.Rect(70, 75, 860, 150), border_radius=22)
                pygame.draw.rect(screen, theme["highlight"], pygame.Rect(70, 75, 860, 150), width=3, border_radius=22)

                # Draw whole word with completed/current highlighting.
                x_start = WIDTH // 2 - (len(word) * 42)
                for i, ch in enumerate(word):
                    if i < current_pos:
                        color = theme["good"]
                    elif i == current_pos:
                        color = theme["highlight"]
                    else:
                        color = theme["text"]
                    draw_text(screen, ch, word_font, color, (x_start + i * 84, 150))

                draw_text(screen, target.upper(), big_font, theme["highlight"], (WIDTH // 2, 365))
                draw_text(screen, "Find and press this letter", normal_font, theme["text"], (WIDTH // 2, 480))
                draw_text(screen, feedback, normal_font, feedback_color, (WIDTH // 2, 555))
                draw_text(screen, "Esc quits the game", small_font, theme["text"], (WIDTH // 2, 650))

                pygame.display.flip()

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        raise SystemExit

                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            raise SystemExit

                        pressed = event.unicode.lower()
                        if not pressed:
                            continue

                        reaction = time.time() - letter_start
                        correct = pressed == target.lower()

                        key_rows.append([
                            session_id,
                            session_datetime,
                            player_name,
                            age,
                            level_start,
                            theme_key,
                            word,
                            current_pos + 1,
                            target,
                            pressed,
                            "yes" if correct else "no",
                            round(reaction, 3)
                        ])

                        if correct:
                            correct_letters += 1
                            reaction_times.append(reaction)
                            feedback = "Good!"
                            feedback_color = theme["good"]
                            current_pos += 1
                            waiting_for_correct = False
                            pygame.time.wait(120)
                        else:
                            wrong_letters += 1
                            reaction_times.append(reaction)
                            feedback = f"Nearly — look for {target.upper()}"
                            feedback_color = theme["bad"]
                            letter_start = time.time()

                clock.tick(FPS)

        show_message(screen, f"Great! You typed {word}", theme, seconds=0.7)

    total_time = time.time() - total_start
    letters_attempted = correct_letters + wrong_letters
    accuracy = (correct_letters / letters_attempted * 100) if letters_attempted else 0
    avg_reaction = (sum(reaction_times) / len(reaction_times)) if reaction_times else 0

    # Simple adaptive level rules.
    level_end = level_start
    if accuracy >= 90 and avg_reaction <= 1.7 and level_start < 4:
        level_end += 1
    elif accuracy < 75 and level_start > 1:
        level_end -= 1

    return {
        "session_id": session_id,
        "datetime": session_datetime,
        "player": player_name,
        "age": age,
        "level_start": level_start,
        "level_end": level_end,
        "theme": theme_key,
        "words_attempted": len(words),
        "letters_attempted": letters_attempted,
        "correct_letters": correct_letters,
        "wrong_letters": wrong_letters,
        "accuracy_percent": round(accuracy, 1),
        "avg_reaction_time_seconds": round(avg_reaction, 3),
        "total_time_seconds": round(total_time, 1),
        "key_rows": key_rows
    }


def save_session(summary):
    with open(KEYS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in summary["key_rows"]:
            writer.writerow(row)

    with open(SESSIONS_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            summary["session_id"],
            summary["datetime"],
            summary["player"],
            summary["age"],
            summary["level_start"],
            summary["level_end"],
            summary["theme"],
            summary["words_attempted"],
            summary["letters_attempted"],
            summary["correct_letters"],
            summary["wrong_letters"],
            summary["accuracy_percent"],
            summary["avg_reaction_time_seconds"],
            summary["total_time_seconds"]
        ])


def show_summary(screen, summary, theme):
    title_font = pygame.font.SysFont(None, 72)
    normal_font = pygame.font.SysFont(None, 42)
    small_font = pygame.font.SysFont(None, 32)

    screen.fill(theme["background"])
    draw_text(screen, "Session complete!", title_font, theme["highlight"], (WIDTH // 2, 90))

    lines = [
        f"Player: {summary['player']}",
        f"Words: {summary['words_attempted']}",
        f"Accuracy: {summary['accuracy_percent']}%",
        f"Average key time: {summary['avg_reaction_time_seconds']} seconds",
        f"Level: {summary['level_start']} → {summary['level_end']}"
    ]

    y = 190
    for line in lines:
        draw_text(screen, line, normal_font, theme["text"], (WIDTH // 2, y))
        y += 65

    if summary["level_end"] > summary["level_start"]:
        msg = "Brilliant — next time gets a little harder!"
    elif summary["level_end"] < summary["level_start"]:
        msg = "Good effort — next time will be a little easier."
    else:
        msg = "Good work — keep practising!"

    draw_text(screen, msg, normal_font, theme["good"], (WIDTH // 2, y + 20))
    draw_text(screen, "Press any key to exit", small_font, theme["text"], (WIDTH // 2, HEIGHT - 80))
    pygame.display.flip()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                return
        pygame.time.wait(20)


def main():
    ensure_files()

    words_data = load_json(WORDS_FILE)
    players = load_json(PLAYERS_FILE)

    pygame.init()
    pygame.display.set_caption("Compute Club Typing Game")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))

    default_theme = THEMES["cream"]

    player_names = list(players.keys())
    player_name = select_from_buttons(screen, "Who is playing?", player_names, default_theme)

    profile = players[player_name]
    preferred_theme = profile.get("preferred_theme", "cream")
    theme_names = list(THEMES.keys())
    default_theme_index = theme_names.index(preferred_theme) if preferred_theme in theme_names else 0

    theme_key = select_from_buttons(
        screen,
        "Choose colours",
        theme_names,
        THEMES[preferred_theme] if preferred_theme in THEMES else default_theme,
        default_index=default_theme_index
    )

    theme = THEMES[theme_key]
    show_message(screen, f"Ready {player_name}?", theme, seconds=1.0)

    summary = play_session(screen, player_name, profile, theme_key, words_data)
    save_session(summary)

    # Store the new adaptive level and chosen theme.
    players[player_name]["current_level"] = summary["level_end"]
    players[player_name]["preferred_theme"] = theme_key
    save_players(players)

    show_summary(screen, summary, theme)

    pygame.quit()


if __name__ == "__main__":
    main()
