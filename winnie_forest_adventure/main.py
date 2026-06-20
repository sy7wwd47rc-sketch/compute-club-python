"""
Winnie's Forest Adventure - Version 6

Main gameplay changes:
- No more boring "collect 100 fruit" grind.
- Baby is much slower.
- Better-looking girl character, no beard effect.
- Flying now feels special:
  - longer wings power
  - glowing wing animation
  - sparkle trail
  - faster movement while flying
  - flying meter
- More interesting mini-quests:
  1. Find 3 golden feathers
  2. Collect the teddy
  3. Calm the cheeky baby
  4. Collect 10 apples
  5. Return to the treehouse

Run on Mac:
    cd ~/Downloads
    source winnie-game-env/bin/activate
    python3 winnies_forest_adventure_v6.py
"""

import math
import random
import sys
from array import array
from dataclasses import dataclass

import pygame


WIDTH = 1100
HEIGHT = 700
FPS = 60

PLAY_TOP = 320
PLAY_BOTTOM = HEIGHT - 45
PLAY_LEFT = 45
PLAY_RIGHT = WIDTH - 45

PLAYER_SPEED = 5
BABY_SPEED_OPTIONS = {
    "Tiny Toddle": 0.10,
    "Very Slow": 0.16,
    "Slow": 0.24,
    "Normal": 0.34,
    "Fast": 0.46,
    "Super Cheeky": 0.62,
}
BABY_SPEED_NAMES = list(BABY_SPEED_OPTIONS.keys())

MAX_ENERGY = 100
START_FOOD = 0
APPLE_TARGET = 10
FEATHERS_NEEDED = 3

FLY_TIME_MS = 14000
BABY_CALM_TIME_MS = 12000
ENERGY_DRAIN_MS = 10000

SKY_TOP = (120, 200, 255)
SKY_BOTTOM = (195, 235, 255)
GRASS_BACK = (130, 215, 130)
GRASS_MID = (85, 185, 95)
GRASS_FRONT = (50, 145, 70)
DARK_GRASS = (30, 105, 50)
TREE_TRUNK = (122, 76, 36)
TREE_TRUNK_DARK = (82, 50, 24)
TREE_LEAF = (45, 150, 70)
TREE_LEAF_DARK = (28, 105, 52)
TREE_LEAF_LIGHT = (80, 185, 95)
WHITE = (255, 255, 255)
OFF_WHITE = (252, 249, 232)
BLACK = (20, 20, 20)
PINK = (255, 150, 185)
PURPLE = (155, 95, 230)
PURPLE_DARK = (110, 60, 170)
YELLOW = (255, 225, 75)
GOLD = (255, 190, 30)
RED = (225, 55, 55)
RED_DARK = (165, 35, 35)
BROWN = (140, 80, 35)
BROWN_DARK = (100, 55, 20)
HAIR = (120, 65, 25)
DARK_BLUE = (30, 80, 160)
CREAM = (255, 224, 190)
BABY_BLUE = (125, 205, 255)
GREY = (210, 210, 210)
PATH = (218, 182, 122)
PATH_DARK = (170, 125, 75)
SHADOW = (40, 85, 42)
QUEST_GREEN = (45, 145, 75)
MAGIC_BLUE = (150, 225, 255)
MAGIC_PINK = (255, 170, 235)


@dataclass
class FloatingMessage:
    text: str
    x: int
    y: int
    created_ms: int
    duration_ms: int = 2200


@dataclass
class Sparkle:
    x: float
    y: float
    created_ms: int
    colour: tuple
    size: int


def clamp(value, low, high):
    return max(low, min(high, value))


def depth_scale(y):
    t = (y - PLAY_TOP) / max(1, (PLAY_BOTTOM - PLAY_TOP))
    return 0.58 + clamp(t, 0, 1) * 0.62


def random_play_position():
    return (
        random.randint(PLAY_LEFT + 40, PLAY_RIGHT - 40),
        random.randint(PLAY_TOP + 30, PLAY_BOTTOM - 40),
    )


def circle_rect(x, y, r):
    return pygame.Rect(int(x - r), int(y - r), int(r * 2), int(r * 2))


class GameState:
    def __init__(self):
        self.mode = "start"
        self.stage = 1
        self.day_complete = False
        self.sparkles = []
        self.baby_speed_name = "Very Slow"
        self.stage_names = {
            1: "Find 3 golden feathers to unlock magic wings.",
            2: "Find the teddy before the cheeky baby steals too much.",
            3: "Press T to calm the cheeky baby.",
            4: f"Collect {APPLE_TARGET} apples for the picnic.",
            5: "Return to the treehouse to finish the day.",
            6: "Day complete!",
        }

    @property
    def baby_speed(self):
        return BABY_SPEED_OPTIONS[self.baby_speed_name]

    def quest_text(self):
        return self.stage_names.get(self.stage, "Explore the forest.")


class Player:
    def __init__(self):
        self.x = WIDTH // 2
        self.y = 570
        self.energy = MAX_ENERGY
        self.food = START_FOOD
        self.feathers = 0
        self.teddy_ready = False
        self.flying_until = 0
        self.facing_right = True

    @property
    def scale(self):
        return depth_scale(self.y)

    @property
    def rect(self):
        s = self.scale
        return pygame.Rect(
            int(self.x - 18 * s),
            int(self.y - 68 * s),
            int(36 * s),
            int(82 * s),
        )

    def is_flying(self, now):
        return now < self.flying_until

    def fly_remaining_ratio(self, now):
        if not self.is_flying(now):
            return 0
        return clamp((self.flying_until - now) / FLY_TIME_MS, 0, 1)

    def can_fly(self):
        return self.feathers >= FEATHERS_NEEDED and self.energy > 0

    def start_flying(self, now, messages):
        if self.can_fly():
            self.flying_until = now + FLY_TIME_MS
            messages.append(FloatingMessage("WHOOSH! Magic wings!", int(self.x - 95), int(self.y - 105), now, 2600))
        else:
            missing = FEATHERS_NEEDED - self.feathers
            if missing > 0:
                messages.append(FloatingMessage(f"Need {missing} more feather(s)!", int(self.x - 95), int(self.y - 85), now))
            else:
                messages.append(FloatingMessage("Too tired to fly!", int(self.x - 70), int(self.y - 85), now))

    def move(self, keys, now, sparkles):
        dx = 0
        dy = 0

        if keys[pygame.K_LEFT]:
            dx -= PLAYER_SPEED
            self.facing_right = False
        if keys[pygame.K_RIGHT]:
            dx += PLAYER_SPEED
            self.facing_right = True
        if keys[pygame.K_UP]:
            dy -= PLAYER_SPEED
        if keys[pygame.K_DOWN]:
            dy += PLAYER_SPEED

        if self.is_flying(now):
            dx *= 1.85
            dy *= 1.85
            self.energy = max(0, self.energy - 0.025)

            if random.random() < 0.55:
                sparkles.append(
                    Sparkle(
                        self.x + random.randint(-28, 28),
                        self.y - random.randint(10, 60),
                        now,
                        random.choice([GOLD, MAGIC_BLUE, MAGIC_PINK, WHITE]),
                        random.randint(3, 7),
                    )
                )

        self.x += dx
        self.y += dy

        self.x = clamp(self.x, PLAY_LEFT, PLAY_RIGHT)
        self.y = clamp(self.y, PLAY_TOP + 70, PLAY_BOTTOM)

    def draw(self, screen, now):
        s = self.scale
        flying = self.is_flying(now)

        shadow_w = int(44 * s)
        shadow_h = int(15 * s)
        pygame.draw.ellipse(screen, SHADOW, (int(self.x - shadow_w / 2), int(self.y + 7 * s), shadow_w, shadow_h))

        if flying:
            pulse = 1.0 + math.sin(now / 120) * 0.12
            wing_offset = int(math.sin(now / 70) * 15 * s)
            wing_w = int(72 * s * pulse)
            wing_h = int(54 * s * pulse)

            # Outer glow
            pygame.draw.ellipse(screen, (175, 235, 255), (int(self.x - 82 * s), int(self.y - 58 * s + wing_offset), wing_w, wing_h))
            pygame.draw.ellipse(screen, (175, 235, 255), (int(self.x + 12 * s), int(self.y - 58 * s - wing_offset), wing_w, wing_h))

            # Inner wing
            pygame.draw.ellipse(screen, WHITE, (int(self.x - 68 * s), int(self.y - 46 * s + wing_offset), int(42 * s), int(30 * s)))
            pygame.draw.ellipse(screen, WHITE, (int(self.x + 30 * s), int(self.y - 46 * s - wing_offset), int(42 * s), int(30 * s)))

            # Wing lines
            pygame.draw.line(screen, MAGIC_BLUE, (int(self.x - 26 * s), int(self.y - 28 * s)), (int(self.x - 78 * s), int(self.y - 35 * s + wing_offset)), max(1, int(2 * s)))
            pygame.draw.line(screen, MAGIC_BLUE, (int(self.x + 26 * s), int(self.y - 28 * s)), (int(self.x + 78 * s), int(self.y - 35 * s - wing_offset)), max(1, int(2 * s)))

        # Legs behind dress
        pygame.draw.line(screen, BLACK, (int(self.x - 8 * s), int(self.y + 18 * s)), (int(self.x - 8 * s), int(self.y + 39 * s)), max(2, int(3 * s)))
        pygame.draw.line(screen, BLACK, (int(self.x + 8 * s), int(self.y + 18 * s)), (int(self.x + 8 * s), int(self.y + 39 * s)), max(2, int(3 * s)))
        pygame.draw.ellipse(screen, DARK_BLUE, (int(self.x - 19 * s), int(self.y + 36 * s), int(19 * s), int(8 * s)))
        pygame.draw.ellipse(screen, DARK_BLUE, (int(self.x + 2 * s), int(self.y + 36 * s), int(19 * s), int(8 * s)))

        # Dress
        pygame.draw.polygon(screen, PURPLE, [
            (int(self.x), int(self.y - 32 * s)),
            (int(self.x - 26 * s), int(self.y + 22 * s)),
            (int(self.x + 26 * s), int(self.y + 22 * s)),
        ])
        pygame.draw.polygon(screen, PURPLE_DARK, [
            (int(self.x + 3 * s), int(self.y - 27 * s)),
            (int(self.x + 26 * s), int(self.y + 22 * s)),
            (int(self.x + 5 * s), int(self.y + 22 * s)),
        ])
        pygame.draw.circle(screen, PINK, (int(self.x), int(self.y - 22 * s)), int(5 * s))

        # Arms
        pygame.draw.line(screen, CREAM, (int(self.x - 12 * s), int(self.y - 22 * s)), (int(self.x - 27 * s), int(self.y - 2 * s)), max(2, int(4 * s)))
        pygame.draw.line(screen, CREAM, (int(self.x + 12 * s), int(self.y - 22 * s)), (int(self.x + 27 * s), int(self.y - 2 * s)), max(2, int(4 * s)))

        # Hair behind head - this replaces the old arc that looked beard-like.
        pygame.draw.circle(screen, HAIR, (int(self.x - 14 * s), int(self.y - 55 * s)), int(15 * s))
        pygame.draw.circle(screen, HAIR, (int(self.x + 14 * s), int(self.y - 55 * s)), int(15 * s))
        pygame.draw.circle(screen, HAIR, (int(self.x), int(self.y - 62 * s)), int(20 * s))

        # Face
        pygame.draw.circle(screen, CREAM, (int(self.x), int(self.y - 55 * s)), int(17 * s))

        # Fringe / top hair only
        pygame.draw.circle(screen, HAIR, (int(self.x - 10 * s), int(self.y - 68 * s)), int(10 * s))
        pygame.draw.circle(screen, HAIR, (int(self.x + 2 * s), int(self.y - 70 * s)), int(11 * s))
        pygame.draw.circle(screen, HAIR, (int(self.x + 12 * s), int(self.y - 66 * s)), int(8 * s))

        # Face details
        pygame.draw.circle(screen, BLACK, (int(self.x - 6 * s), int(self.y - 56 * s)), max(1, int(2 * s)))
        pygame.draw.circle(screen, BLACK, (int(self.x + 6 * s), int(self.y - 56 * s)), max(1, int(2 * s)))
        pygame.draw.circle(screen, PINK, (int(self.x - 10 * s), int(self.y - 50 * s)), max(1, int(3 * s)))
        pygame.draw.circle(screen, PINK, (int(self.x + 10 * s), int(self.y - 50 * s)), max(1, int(3 * s)))
        pygame.draw.arc(screen, BLACK, (int(self.x - 7 * s), int(self.y - 53 * s), int(14 * s), int(10 * s)), 0, math.pi, max(1, int(2 * s)))


class Apple:
    def __init__(self):
        self.x, self.y = random_play_position()

    @property
    def scale(self):
        return depth_scale(self.y)

    @property
    def rect(self):
        r = 14 * self.scale
        return circle_rect(self.x, self.y, r)

    def respawn(self):
        self.x, self.y = random_play_position()

    def draw(self, screen):
        s = self.scale
        r = int(14 * s)
        pygame.draw.ellipse(screen, SHADOW, (int(self.x - 12 * s), int(self.y + 8 * s), int(24 * s), int(8 * s)))
        pygame.draw.circle(screen, RED_DARK, (int(self.x + 2 * s), int(self.y + 2 * s)), r)
        pygame.draw.circle(screen, RED, (int(self.x), int(self.y)), r)
        pygame.draw.circle(screen, (255, 120, 120), (int(self.x - 5 * s), int(self.y - 4 * s)), max(2, int(4 * s)))
        pygame.draw.line(screen, BROWN, (int(self.x), int(self.y - 12 * s)), (int(self.x + 4 * s), int(self.y - 23 * s)), max(2, int(3 * s)))
        pygame.draw.ellipse(screen, TREE_LEAF, (int(self.x + 4 * s), int(self.y - 24 * s), int(14 * s), int(8 * s)))


class Feather:
    def __init__(self):
        self.x, self.y = random_play_position()
        self.collected = False

    @property
    def scale(self):
        return depth_scale(self.y)

    @property
    def rect(self):
        s = self.scale
        return pygame.Rect(int(self.x - 18 * s), int(self.y - 18 * s), int(36 * s), int(36 * s))

    def draw(self, screen):
        if self.collected:
            return
        s = self.scale
        pygame.draw.ellipse(screen, SHADOW, (int(self.x - 12 * s), int(self.y + 15 * s), int(24 * s), int(7 * s)))
        pygame.draw.ellipse(screen, GOLD, (int(self.x - 6 * s), int(self.y - 20 * s), int(18 * s), int(38 * s)))
        pygame.draw.line(screen, BROWN, (int(self.x + 2 * s), int(self.y - 17 * s)), (int(self.x - 8 * s), int(self.y + 20 * s)), max(1, int(2 * s)))
        pygame.draw.line(screen, WHITE, (int(self.x + 2 * s), int(self.y - 5 * s)), (int(self.x + 14 * s), int(self.y - 12 * s)), 1)
        pygame.draw.line(screen, WHITE, (int(self.x), int(self.y + 5 * s)), (int(self.x + 12 * s), int(self.y)), 1)


class Teddy:
    def __init__(self):
        self.x, self.y = random_play_position()
        self.visible = True

    @property
    def scale(self):
        return depth_scale(self.y)

    @property
    def rect(self):
        s = self.scale
        return pygame.Rect(int(self.x - 20 * s), int(self.y - 20 * s), int(40 * s), int(40 * s))

    def draw(self, screen):
        if not self.visible:
            return
        s = self.scale
        pygame.draw.ellipse(screen, SHADOW, (int(self.x - 17 * s), int(self.y + 14 * s), int(34 * s), int(9 * s)))
        pygame.draw.circle(screen, BROWN_DARK, (int(self.x + 2 * s), int(self.y + 2 * s)), int(15 * s))
        pygame.draw.circle(screen, BROWN, (int(self.x), int(self.y)), int(15 * s))
        pygame.draw.circle(screen, BROWN, (int(self.x - 13 * s), int(self.y - 10 * s)), int(8 * s))
        pygame.draw.circle(screen, BROWN, (int(self.x + 13 * s), int(self.y - 10 * s)), int(8 * s))
        pygame.draw.circle(screen, CREAM, (int(self.x), int(self.y + 4 * s)), int(8 * s))
        pygame.draw.circle(screen, BLACK, (int(self.x - 5 * s), int(self.y - 3 * s)), max(1, int(2 * s)))
        pygame.draw.circle(screen, BLACK, (int(self.x + 5 * s), int(self.y - 3 * s)), max(1, int(2 * s)))


class Baby:
    def __init__(self):
        self.x, self.y = random_play_position()
        self.calm_until = 0
        self.last_steal_ms = 0

    @property
    def scale(self):
        return depth_scale(self.y)

    @property
    def rect(self):
        s = self.scale
        return pygame.Rect(int(self.x - 25 * s), int(self.y - 42 * s), int(50 * s), int(70 * s))

    def is_calm(self, now):
        return now < self.calm_until

    def calm_down(self, now, messages):
        self.calm_until = now + BABY_CALM_TIME_MS
        messages.append(FloatingMessage("Teddy time! Baby is calm.", int(self.x - 85), int(self.y - 75), now, 2600))

    def update(self, player, now, game_state):
        if self.is_calm(now) or game_state.day_complete:
            return

        # Baby only really chases once the teddy stage has started.
        # Before that, it mostly toddles around.
        if game_state.stage < 2:
            self.x += math.sin(now / 600) * 0.35
            self.y += math.cos(now / 750) * 0.22
        else:
            dx = player.x - self.x
            dy = player.y - self.y
            distance = math.hypot(dx, dy)
            if distance > 0:
                wobble_x = math.sin(now / 380) * 0.18
                wobble_y = math.cos(now / 460) * 0.14
                self.x += (dx / distance) * game_state.baby_speed + wobble_x
                self.y += (dy / distance) * game_state.baby_speed + wobble_y

        self.x = clamp(self.x, PLAY_LEFT, PLAY_RIGHT)
        self.y = clamp(self.y, PLAY_TOP + 45, PLAY_BOTTOM)

    def steal_food_if_touching(self, player, now, messages, game_state):
        if self.is_calm(now) or game_state.day_complete or game_state.stage < 4:
            return

        if self.rect.colliderect(player.rect) and now - self.last_steal_ms > 4200:
            if player.food > 0:
                player.food -= 1
                messages.append(FloatingMessage("Cheeky baby stole 1 apple!", int(self.x - 105), int(self.y - 82), now, 2200))
            else:
                messages.append(FloatingMessage("No apples left!", int(self.x - 50), int(self.y - 82), now))

            self.last_steal_ms = now
            self.x, self.y = random_play_position()

    def draw(self, screen, now):
        s = self.scale
        calm = self.is_calm(now)

        pygame.draw.ellipse(screen, SHADOW, (int(self.x - 23 * s), int(self.y + 21 * s), int(46 * s), int(13 * s)))
        pygame.draw.circle(screen, BABY_BLUE if not calm else GREY, (int(self.x), int(self.y)), int(24 * s))
        pygame.draw.circle(screen, CREAM, (int(self.x), int(self.y - 24 * s)), int(18 * s))

        pygame.draw.circle(screen, BLACK, (int(self.x - 6 * s), int(self.y - 27 * s)), max(1, int(2 * s)))
        pygame.draw.circle(screen, BLACK, (int(self.x + 6 * s), int(self.y - 27 * s)), max(1, int(2 * s)))
        pygame.draw.arc(screen, BLACK, (int(self.x - 8 * s), int(self.y - 27 * s), int(16 * s), int(13 * s)), 0, math.pi, max(1, int(2 * s)))

        pygame.draw.rect(screen, WHITE, (int(self.x - 17 * s), int(self.y + 3 * s), int(34 * s), int(14 * s)), border_radius=max(2, int(5 * s)))
        pygame.draw.circle(screen, CREAM, (int(self.x - 17 * s), int(self.y + 25 * s)), int(6 * s))
        pygame.draw.circle(screen, CREAM, (int(self.x + 17 * s), int(self.y + 25 * s)), int(6 * s))

        if calm:
            pygame.draw.circle(screen, PINK, (int(self.x + 22 * s), int(self.y - 12 * s)), int(7 * s))
            pygame.draw.line(screen, PINK, (int(self.x + 16 * s), int(self.y - 12 * s)), (int(self.x + 5 * s), int(self.y - 10 * s)), max(2, int(3 * s)))


def draw_vertical_gradient(screen, top_colour, bottom_colour):
    for y in range(0, HEIGHT):
        ratio = y / HEIGHT
        r = int(top_colour[0] * (1 - ratio) + bottom_colour[0] * ratio)
        g = int(top_colour[1] * (1 - ratio) + bottom_colour[1] * ratio)
        b = int(top_colour[2] * (1 - ratio) + bottom_colour[2] * ratio)
        pygame.draw.line(screen, (r, g, b), (0, y), (WIDTH, y))


def draw_tree(screen, x, y, scale=1.0):
    trunk_w = int(28 * scale)
    trunk_h = int(120 * scale)
    leaf_r = int(50 * scale)

    pygame.draw.ellipse(screen, SHADOW, (int(x - 44 * scale), int(y + 55 * scale), int(88 * scale), int(19 * scale)))
    pygame.draw.rect(screen, TREE_TRUNK_DARK, (int(x - trunk_w / 2 + 5 * scale), int(y - trunk_h / 2 + 5 * scale), trunk_w, trunk_h))
    pygame.draw.rect(screen, TREE_TRUNK, (int(x - trunk_w / 2), int(y - trunk_h / 2), trunk_w, trunk_h))

    pygame.draw.line(screen, TREE_TRUNK_DARK, (int(x - 5 * scale), int(y - 42 * scale)), (int(x - 9 * scale), int(y + 30 * scale)), max(1, int(2 * scale)))
    pygame.draw.line(screen, TREE_TRUNK_DARK, (int(x + 7 * scale), int(y - 30 * scale)), (int(x + 3 * scale), int(y + 42 * scale)), max(1, int(2 * scale)))

    pygame.draw.circle(screen, TREE_LEAF_DARK, (int(x - 30 * scale), int(y - 75 * scale)), int(36 * scale))
    pygame.draw.circle(screen, TREE_LEAF_DARK, (int(x + 30 * scale), int(y - 75 * scale)), int(36 * scale))
    pygame.draw.circle(screen, TREE_LEAF, (int(x), int(y - 94 * scale)), leaf_r)
    pygame.draw.circle(screen, TREE_LEAF_LIGHT, (int(x - 12 * scale), int(y - 112 * scale)), int(28 * scale))


def draw_bush(screen, x, y, scale=1.0):
    pygame.draw.ellipse(screen, SHADOW, (int(x - 35 * scale), int(y + 15 * scale), int(70 * scale), int(13 * scale)))
    pygame.draw.circle(screen, TREE_LEAF_DARK, (int(x - 25 * scale), int(y)), int(22 * scale))
    pygame.draw.circle(screen, TREE_LEAF, (int(x), int(y - 8 * scale)), int(28 * scale))
    pygame.draw.circle(screen, TREE_LEAF_DARK, (int(x + 28 * scale), int(y)), int(21 * scale))
    pygame.draw.circle(screen, TREE_LEAF_LIGHT, (int(x - 8 * scale), int(y - 17 * scale)), int(12 * scale))


def draw_background_forest(screen):
    draw_vertical_gradient(screen, SKY_TOP, SKY_BOTTOM)

    pygame.draw.circle(screen, YELLOW, (980, 82), 42)
    pygame.draw.circle(screen, (255, 235, 120), (980, 82), 62, 3)

    pygame.draw.ellipse(screen, (150, 220, 150), (-180, 225, 680, 210))
    pygame.draw.ellipse(screen, (120, 205, 135), (350, 205, 820, 230))
    pygame.draw.ellipse(screen, (100, 190, 125), (120, 260, 760, 210))

    pygame.draw.rect(screen, GRASS_BACK, (0, 270, WIDTH, 115))
    pygame.draw.rect(screen, GRASS_MID, (0, 385, WIDTH, 125))
    pygame.draw.rect(screen, GRASS_FRONT, (0, 510, WIDTH, HEIGHT - 510))

    path = [
        (520, 300), (580, 300), (640, 390), (575, 465), (680, 560),
        (820, HEIGHT), (250, HEIGHT), (405, 560), (505, 465), (450, 390),
    ]
    pygame.draw.polygon(screen, PATH, path)
    pygame.draw.lines(screen, PATH_DARK, False, [(520, 300), (450, 390), (505, 465), (405, 560), (250, HEIGHT)], 5)
    pygame.draw.lines(screen, PATH_DARK, False, [(580, 300), (640, 390), (575, 465), (680, 560), (820, HEIGHT)], 5)

    for x, y, w in [(550, 345, 42), (540, 415, 60), (590, 500, 82), (530, 600, 120)]:
        pygame.draw.ellipse(screen, (195, 155, 95), (x - w // 2, y, w, int(w * 0.32)))

    for x, y, s in [
        (60, 330, 0.55), (170, 300, 0.48), (300, 335, 0.60), (430, 315, 0.48),
        (690, 330, 0.60), (820, 310, 0.52), (1010, 350, 0.66),
        (115, 445, 0.78), (245, 475, 0.85), (910, 455, 0.82), (1015, 500, 0.95),
        (760, 520, 0.96),
    ]:
        draw_tree(screen, x, y, s)

    for x, y in [(130, 545), (220, 610), (845, 545), (890, 590), (610, 635), (380, 480), (705, 645)]:
        pygame.draw.circle(screen, PINK, (x - 5, y), 5)
        pygame.draw.circle(screen, PINK, (x + 5, y), 5)
        pygame.draw.circle(screen, PINK, (x, y - 5), 5)
        pygame.draw.circle(screen, YELLOW, (x, y), 4)
        pygame.draw.line(screen, TREE_LEAF_DARK, (x, y + 5), (x, y + 18), 2)

    for x, y in [(350, 650), (370, 635), (725, 655), (790, 635), (145, 640), (975, 620)]:
        pygame.draw.line(screen, DARK_GRASS, (x, y), (x - 9, y - 18), 3)
        pygame.draw.line(screen, DARK_GRASS, (x, y), (x + 7, y - 15), 3)
        pygame.draw.line(screen, DARK_GRASS, (x, y), (x, y - 22), 3)


def draw_treehouse(screen):
    x, y = 118, 605
    pygame.draw.ellipse(screen, SHADOW, (x - 75, y - 23, 150, 28))
    pygame.draw.rect(screen, TREE_TRUNK_DARK, (x - 14, y - 130, 32, 145))
    pygame.draw.rect(screen, TREE_TRUNK, (x - 20, y - 135, 32, 145))
    pygame.draw.rect(screen, BROWN_DARK, (x - 58, y - 170, 122, 78), border_radius=8)
    pygame.draw.rect(screen, BROWN, (x - 64, y - 176, 122, 78), border_radius=8)
    pygame.draw.polygon(screen, RED_DARK, [(x - 74, y - 176), (x, y - 232), (x + 74, y - 176)])
    pygame.draw.polygon(screen, RED, [(x - 80, y - 183), (x, y - 240), (x + 80, y - 183)])
    pygame.draw.rect(screen, DARK_BLUE, (x - 18, y - 136, 35, 42))
    pygame.draw.rect(screen, YELLOW, (x + 27, y - 153, 26, 26))
    pygame.draw.line(screen, BROWN_DARK, (x - 54, y - 84), (x + 54, y - 84), 7)


def draw_foreground(screen):
    draw_tree(screen, 15, 690, 1.25)
    draw_tree(screen, 1085, 685, 1.23)
    draw_bush(screen, 150, 685, 1.1)
    draw_bush(screen, 965, 685, 1.1)


def draw_sparkles(screen, sparkles, now):
    alive = []
    for sparkle in sparkles:
        age = now - sparkle.created_ms
        if age < 900:
            alive.append(sparkle)
            fade = 1 - age / 900
            size = max(1, int(sparkle.size * fade))
            pygame.draw.circle(screen, sparkle.colour, (int(sparkle.x), int(sparkle.y)), size)
            pygame.draw.line(screen, sparkle.colour, (int(sparkle.x - size * 2), int(sparkle.y)), (int(sparkle.x + size * 2), int(sparkle.y)), 1)
            pygame.draw.line(screen, sparkle.colour, (int(sparkle.x), int(sparkle.y - size * 2)), (int(sparkle.x), int(sparkle.y + size * 2)), 1)
    sparkles[:] = alive


def draw_hud(screen, font, small_font, player, baby, now, game_state):
    pygame.draw.rect(screen, (245, 244, 220), (0, 0, WIDTH, 170))
    pygame.draw.line(screen, BLACK, (0, 170), (WIDTH, 170), 2)

    left_box = pygame.Rect(15, 15, 390, 105)
    pygame.draw.rect(screen, OFF_WHITE, left_box, border_radius=12)
    pygame.draw.rect(screen, BLACK, left_box, 2, border_radius=12)

    screen.blit(font.render(f"Apples: {player.food}/{APPLE_TARGET}", True, BLACK), (30, 25))
    screen.blit(font.render(f"Energy: {int(player.energy)}", True, BLACK), (30, 56))
    screen.blit(font.render(f"Feathers: {player.feathers}/{FEATHERS_NEEDED}", True, BLACK), (30, 87))

    teddy_text = "Ready" if player.teddy_ready else "Find teddy"
    wings_text = "Unlocked" if player.feathers >= FEATHERS_NEEDED else "Locked"
    baby_text = "Calm" if baby.is_calm(now) else "Cheeky"

    screen.blit(small_font.render(f"Teddy: {teddy_text}", True, BLACK), (225, 31))
    screen.blit(small_font.render(f"Wings: {wings_text}", True, BLACK), (225, 61))
    screen.blit(small_font.render(f"Baby: {baby_text}", True, BLACK), (225, 91))

    right_box = pygame.Rect(675, 15, 410, 105)
    pygame.draw.rect(screen, OFF_WHITE, right_box, border_radius=12)
    pygame.draw.rect(screen, BLACK, right_box, 2, border_radius=12)

    screen.blit(small_font.render("Controls", True, BLACK), (692, 28))
    screen.blit(small_font.render("Arrow keys: move", True, BLACK), (692, 53))
    screen.blit(small_font.render("SPACE: magic wings", True, BLACK), (692, 77))
    screen.blit(small_font.render("T: use teddy    R: setup screen", True, BLACK), (692, 101))

    quest_box = pygame.Rect(15, 127, WIDTH - 30, 35)
    pygame.draw.rect(screen, QUEST_GREEN, quest_box, border_radius=9)
    pygame.draw.rect(screen, BLACK, quest_box, 1, border_radius=9)
    screen.blit(small_font.render("Task: " + game_state.quest_text(), True, WHITE), (30, 135))

    # Flying power meter
    if player.is_flying(now):
        meter_bg = pygame.Rect(430, 37, 210, 28)
        pygame.draw.rect(screen, WHITE, meter_bg, border_radius=8)
        pygame.draw.rect(screen, BLACK, meter_bg, 2, border_radius=8)
        fill_w = int(200 * player.fly_remaining_ratio(now))
        pygame.draw.rect(screen, MAGIC_BLUE, (435, 42, fill_w, 18), border_radius=6)
        screen.blit(small_font.render("Flying power", True, BLACK), (478, 73))



def draw_start_screen(screen, big_font, font, small_font, game_state):
    draw_background_forest(screen)

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((255, 255, 255, 120))
    screen.blit(overlay, (0, 0))

    box = pygame.Rect(230, 135, 640, 410)
    pygame.draw.rect(screen, OFF_WHITE, box, border_radius=20)
    pygame.draw.rect(screen, BLACK, box, 3, border_radius=20)

    title = big_font.render("Winnie's Forest Adventure", True, BLACK)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 165))

    subtitle = font.render("Choose the cheeky baby speed and enjoy the pop music!", True, BLACK)
    screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, 230))

    speed = font.render(f"Baby speed: {game_state.baby_speed_name}", True, BLACK)
    screen.blit(speed, (WIDTH // 2 - speed.get_width() // 2, 300))

    hints = [
        "Left / Right arrows: change baby speed",
        "Press ENTER to start the game",
        "Press M to mute or unmute the pop music",
        "Recommendation for Winnie: Tiny Toddle or Very Slow",
        "Apples count whenever you collect them",
    ]

    y = 380
    for hint in hints:
        text = small_font.render(hint, True, BLACK)
        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, y))
        y += 30

    # Baby preview
    x, y = WIDTH // 2, 520
    pygame.draw.ellipse(screen, SHADOW, (x - 28, y + 20, 56, 14))
    pygame.draw.circle(screen, BABY_BLUE, (x, y), 28)
    pygame.draw.circle(screen, CREAM, (x, y - 28), 20)
    pygame.draw.circle(screen, BLACK, (x - 7, y - 32), 3)
    pygame.draw.circle(screen, BLACK, (x + 7, y - 32), 3)
    pygame.draw.arc(screen, BLACK, (x - 10, y - 31, 20, 16), 0, math.pi, 2)

def draw_big_center_message(screen, big_font, font, game_state):
    if not game_state.day_complete:
        return

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((255, 255, 255, 85))
    screen.blit(overlay, (0, 0))

    box = pygame.Rect(225, 235, 650, 205)
    pygame.draw.rect(screen, OFF_WHITE, box, border_radius=18)
    pygame.draw.rect(screen, BLACK, box, 3, border_radius=18)

    title = big_font.render("Picnic Saved!", True, BLACK)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 260))

    line1 = font.render("You got the feathers, calmed the baby,", True, BLACK)
    line2 = font.render("collected apples, and made it home.", True, BLACK)
    line3 = font.render("Press R to play again.", True, BLACK)
    screen.blit(line1, (WIDTH // 2 - line1.get_width() // 2, 325))
    screen.blit(line2, (WIDTH // 2 - line2.get_width() // 2, 357))
    screen.blit(line3, (WIDTH // 2 - line3.get_width() // 2, 397))


def draw_messages(screen, font, messages, now):
    alive = []
    for msg in messages:
        age = now - msg.created_ms
        if age < msg.duration_ms:
            alive.append(msg)
            x = clamp(msg.x, 20, WIDTH - 360)
            y = clamp(msg.y, 178, HEIGHT - 70)
            bubble_width = min(360, 22 + len(msg.text) * 9)
            bubble = pygame.Rect(x - 8, y - 5, bubble_width, 32)
            pygame.draw.rect(screen, OFF_WHITE, bubble, border_radius=8)
            pygame.draw.rect(screen, BLACK, bubble, 1, border_radius=8)
            screen.blit(font.render(msg.text, True, BLACK), (x, y))
    messages[:] = alive


def update_stage(game_state, player, baby, treehouse_zone, now, messages):
    old_stage = game_state.stage

    if player.feathers < FEATHERS_NEEDED:
        game_state.stage = 1
    elif not player.teddy_ready and not baby.is_calm(now):
        game_state.stage = 2
    elif not baby.is_calm(now):
        game_state.stage = 3
    elif player.food < APPLE_TARGET:
        game_state.stage = 4
    elif not player.rect.colliderect(treehouse_zone):
        game_state.stage = 5
    else:
        game_state.stage = 6
        game_state.day_complete = True

    if game_state.stage != old_stage and not game_state.day_complete:
        messages.append(FloatingMessage("New task!", 480, 190, now, 1800))


def reset_game(game_state=None):
    if game_state is None:
        game_state = GameState()
    game_state.mode = "play"
    game_state.stage = 1
    game_state.day_complete = False
    game_state.sparkles = []
    player = Player()
    apple = Apple()
    feathers = [Feather(), Feather(), Feather()]
    teddy = Teddy()
    baby = Baby()
    messages = [FloatingMessage("Welcome! Start by finding 3 golden feathers.", 285, 190, pygame.time.get_ticks(), 3500)]
    last_energy_drain = pygame.time.get_ticks()
    return game_state, player, apple, feathers, teddy, baby, messages, last_energy_drain



def make_tone(frequency, duration, volume=0.22, sample_rate=22050):
    """Create a small 16-bit mono sound tone using only Python."""
    sample_count = int(sample_rate * duration)
    samples = array("h")
    fade_samples = max(1, int(sample_rate * 0.015))

    for i in range(sample_count):
        t = i / sample_rate
        # Pop-ish tone: bright lead note plus a quieter octave underneath.
        wave = math.sin(2 * math.pi * frequency * t)
        wave += 0.35 * math.sin(2 * math.pi * frequency * 2 * t)

        # Quick fade in/out so notes do not click.
        fade = 1.0
        if i < fade_samples:
            fade = i / fade_samples
        elif i > sample_count - fade_samples:
            fade = max(0, (sample_count - i) / fade_samples)

        samples.append(int(32767 * volume * fade * wave))

    return pygame.mixer.Sound(buffer=samples.tobytes())


class PopMusic:
    def __init__(self):
        self.enabled = True
        self.available = False
        self.channel = None
        self.note_index = 0
        self.next_note_ms = 0
        self.notes = []
        self.note_ms = 185
        self.sounds = {}

    def setup(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self.channel = pygame.mixer.Channel(0)
            self.available = True

            # A cheerful C major / pop-style loop.
            melody = [
                "C5", "E5", "G5", "E5", "A5", "G5", "E5", "D5",
                "C5", "E5", "G5", "C6", "B5", "G5", "E5", "D5",
                "A4", "C5", "E5", "A5", "G5", "E5", "D5", "C5",
                "F5", "A5", "G5", "E5", "D5", "E5", "C5", "REST",
            ]
            freqs = {
                "A4": 440.00, "C5": 523.25, "D5": 587.33, "E5": 659.25,
                "F5": 698.46, "G5": 783.99, "A5": 880.00, "B5": 987.77,
                "C6": 1046.50,
            }
            self.notes = melody
            for name, freq in freqs.items():
                self.sounds[name] = make_tone(freq, self.note_ms / 1000.0, volume=0.20)
        except pygame.error:
            self.available = False

    def toggle(self):
        self.enabled = not self.enabled
        if not self.enabled and self.channel:
            self.channel.stop()

    def update(self, now):
        if not self.available or not self.enabled:
            return
        if now < self.next_note_ms:
            return

        note = self.notes[self.note_index]
        self.note_index = (self.note_index + 1) % len(self.notes)
        self.next_note_ms = now + self.note_ms

        if note != "REST" and self.channel:
            self.channel.play(self.sounds[note])


def main():
    pygame.init()
    music = PopMusic()
    music.setup()
    pygame.display.set_caption("Winnie's Forest Adventure - Version 6")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    font = pygame.font.SysFont("arial", 24, bold=True)
    small_font = pygame.font.SysFont("arial", 19)
    big_font = pygame.font.SysFont("arial", 52, bold=True)

    game_state = GameState()
    player = None
    apple = None
    feathers = []
    teddy = None
    baby = None
    messages = []
    last_energy_drain = pygame.time.get_ticks()

    running = True
    while running:
        now = pygame.time.get_ticks()
        music.update(now)
        treehouse_zone = pygame.Rect(45, 390, 155, 250)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if game_state.mode == "start":
                    if event.key == pygame.K_m:
                        music.toggle()

                    if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                        idx = BABY_SPEED_NAMES.index(game_state.baby_speed_name)
                        if event.key == pygame.K_LEFT:
                            idx = (idx - 1) % len(BABY_SPEED_NAMES)
                        else:
                            idx = (idx + 1) % len(BABY_SPEED_NAMES)
                        game_state.baby_speed_name = BABY_SPEED_NAMES[idx]

                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        game_state, player, apple, feathers, teddy, baby, messages, last_energy_drain = reset_game(game_state)

                elif game_state.mode == "play":
                    if event.key == pygame.K_m:
                        music.toggle()

                    if event.key == pygame.K_SPACE and not game_state.day_complete:
                        player.start_flying(now, messages)

                    if event.key == pygame.K_t and not game_state.day_complete:
                        if player.teddy_ready:
                            player.teddy_ready = False
                            baby.calm_down(now, messages)
                        else:
                            messages.append(FloatingMessage("Find the teddy first!", int(player.x - 90), int(player.y - 85), now))

                    if event.key == pygame.K_r:
                        game_state.mode = "start"

        if game_state.mode == "start":
            draw_start_screen(screen, big_font, font, small_font, game_state)
            pygame.display.flip()
            clock.tick(FPS)
            continue

        keys = pygame.key.get_pressed()

        if not game_state.day_complete:
            player.move(keys, now, game_state.sparkles)
            baby.update(player, now, game_state)

            # Apples now count whenever they are collected, even if the current task is feathers or teddy.
            if player.rect.colliderect(apple.rect):
                player.food += 1
                messages.append(FloatingMessage("+1 apple", int(apple.x - 30), int(apple.y - 45), now))
                apple.respawn()

            for feather in feathers:
                if not feather.collected and player.rect.colliderect(feather.rect):
                    if player.feathers < FEATHERS_NEEDED:
                        player.feathers += 1
                        feather.collected = True
                        messages.append(FloatingMessage("+1 golden feather", int(feather.x - 80), int(feather.y - 45), now))
                        if player.feathers == FEATHERS_NEEDED:
                            messages.append(FloatingMessage("Magic wings unlocked! Press SPACE!", int(player.x - 150), int(player.y - 100), now, 3500))

            if teddy.visible and player.rect.colliderect(teddy.rect) and game_state.stage >= 2:
                teddy.visible = False
                player.teddy_ready = True
                messages.append(FloatingMessage("Teddy collected! Press T!", int(teddy.x - 95), int(teddy.y - 45), now, 2600))
            elif teddy.visible and player.rect.colliderect(teddy.rect) and game_state.stage < 2:
                messages.append(FloatingMessage("Feathers first!", int(teddy.x - 55), int(teddy.y - 45), now, 900))

            baby.steal_food_if_touching(player, now, messages, game_state)

            if now - last_energy_drain > ENERGY_DRAIN_MS:
                last_energy_drain = now
                player.energy = max(0, player.energy - 1)

            if player.rect.colliderect(treehouse_zone):
                if player.energy < MAX_ENERGY:
                    player.energy = min(MAX_ENERGY, player.energy + 0.65)

            if player.energy <= 0:
                player.x = 118
                player.y = 630
                player.energy = MAX_ENERGY
                player.food = max(0, player.food - 1)
                messages.append(FloatingMessage("Rest time at the treehouse!", 220, 530, now, 2500))

            update_stage(game_state, player, baby, treehouse_zone, now, messages)

        draw_background_forest(screen)
        draw_treehouse(screen)

        drawable_objects = [
            (apple.y, apple.draw),
            *[(f.y, f.draw) for f in feathers],
            (teddy.y, teddy.draw),
            (baby.y, lambda scr: baby.draw(scr, now)),
            (player.y, lambda scr: player.draw(scr, now)),
        ]

        for _, draw_func in sorted(drawable_objects, key=lambda item: item[0]):
            draw_func(screen)

        draw_sparkles(screen, game_state.sparkles, now)
        draw_foreground(screen)
        draw_hud(screen, font, small_font, player, baby, now, game_state)
        draw_messages(screen, small_font, messages, now)
        draw_big_center_message(screen, big_font, font, game_state)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
