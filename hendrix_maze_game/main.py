import math
import random
import sys
from dataclasses import dataclass

import pygame


# Hendrix Maze
# First-person maze game for Raspberry Pi / Computer Club
#
# Controls:
#   Mouse left/right  = turn
#   Hold left mouse   = walk forwards
#   Hold right mouse  = walk backwards
#   ESC              = quit
#   R                = new maze
#   M                = toggle mini-map
#   Arrow keys/WASD  = backup controls


SCREEN_W = 960
SCREEN_H = 600
FPS = 60

CELL_SIZE = 64
FOV = math.radians(70)
NUM_RAYS = 240
MAX_DEPTH = 900
MOVE_SPEED = 150       # pixels per second
TURN_SPEED = 2.7       # radians per second when using keyboard
MOUSE_TURN_SPEED = 0.004

MAZE_W = 15
MAZE_H = 15

# Blue and green theme
SKY = (25, 55, 115)
FLOOR = (18, 115, 65)
WALL_NEAR = (35, 220, 150)
WALL_FAR = (10, 75, 145)
TEXT = (235, 255, 235)
MAP_BG = (5, 30, 45)
MAP_WALL = (20, 95, 155)
MAP_PATH = (20, 165, 90)
MAP_VISITED = (120, 245, 160)
MAP_PLAYER = (255, 255, 255)
FINISH = (60, 255, 110)
BLACK = (0, 0, 0)


@dataclass
class Player:
    x: float
    y: float
    angle: float


def generate_maze(width: int, height: int):
    """Generate an odd-sized maze using recursive backtracking."""
    if width % 2 == 0:
        width += 1
    if height % 2 == 0:
        height += 1

    grid = [[1 for _ in range(width)] for _ in range(height)]

    def carve(cx, cy):
        grid[cy][cx] = 0
        dirs = [(2, 0), (-2, 0), (0, 2), (0, -2)]
        random.shuffle(dirs)

        for dx, dy in dirs:
            nx, ny = cx + dx, cy + dy
            if 1 <= nx < width - 1 and 1 <= ny < height - 1 and grid[ny][nx] == 1:
                grid[cy + dy // 2][cx + dx // 2] = 0
                carve(nx, ny)

    carve(1, 1)

    # Start and finish
    grid[1][1] = 0
    grid[height - 2][width - 2] = 2
    return grid


def is_wall(grid, x, y):
    gx = int(x // CELL_SIZE)
    gy = int(y // CELL_SIZE)
    if gy < 0 or gy >= len(grid) or gx < 0 or gx >= len(grid[0]):
        return True
    return grid[gy][gx] == 1


def cell_at(grid, x, y):
    gx = int(x // CELL_SIZE)
    gy = int(y // CELL_SIZE)
    if gy < 0 or gy >= len(grid) or gx < 0 or gx >= len(grid[0]):
        return 1
    return grid[gy][gx]


def shade_colour(near, far, distance):
    t = min(1.0, distance / MAX_DEPTH)
    return tuple(int(near[i] * (1 - t) + far[i] * t) for i in range(3))


def cast_rays(screen, grid, player):
    """Simple raycaster that draws vertical wall slices."""
    ray_angle = player.angle - FOV / 2
    strip_w = SCREEN_W / NUM_RAYS

    for ray in range(NUM_RAYS):
        sin_a = math.sin(ray_angle)
        cos_a = math.cos(ray_angle)

        depth = 1
        hit = False
        while depth < MAX_DEPTH:
            target_x = player.x + cos_a * depth
            target_y = player.y + sin_a * depth

            if is_wall(grid, target_x, target_y):
                hit = True
                break

            depth += 4

        if not hit:
            depth = MAX_DEPTH

        # Fish-eye correction
        corrected_depth = depth * math.cos(player.angle - ray_angle)
        corrected_depth = max(corrected_depth, 1)

        wall_height = min(SCREEN_H, int((CELL_SIZE * 520) / corrected_depth))
        x = int(ray * strip_w)
        y = SCREEN_H // 2 - wall_height // 2

        colour = shade_colour(WALL_NEAR, WALL_FAR, corrected_depth)

        pygame.draw.rect(
            screen,
            colour,
            (x, y, int(strip_w) + 1, wall_height)
        )

        # Simple edge/highlight every few strips to give the wall texture
        if ray % 8 == 0:
            pygame.draw.line(screen, (10, 45, 80), (x, y), (x, y + wall_height), 1)

        ray_angle += FOV / NUM_RAYS


def move_player(grid, player, amount):
    """Move with basic collision handling."""
    nx = player.x + math.cos(player.angle) * amount
    ny = player.y + math.sin(player.angle) * amount

    # Try x and y separately so player slides along walls
    if not is_wall(grid, nx, player.y):
        player.x = nx
    if not is_wall(grid, player.x, ny):
        player.y = ny


def draw_minimap(screen, grid, player, visited, show_full=False):
    """Top-right learned map. Shows walls only where visited unless show_full is True."""
    map_size = 170
    margin = 14
    x0 = SCREEN_W - map_size - margin
    y0 = margin

    rows = len(grid)
    cols = len(grid[0])
    scale = map_size / max(rows, cols)

    pygame.draw.rect(screen, MAP_BG, (x0 - 6, y0 - 6, map_size + 12, map_size + 12), border_radius=8)
    pygame.draw.rect(screen, (90, 220, 160), (x0 - 6, y0 - 6, map_size + 12, map_size + 12), 2, border_radius=8)

    for y in range(rows):
        for x in range(cols):
            known = show_full or (x, y) in visited
            if not known:
                continue

            val = grid[y][x]
            rect = (x0 + int(x * scale), y0 + int(y * scale), max(1, int(scale)), max(1, int(scale)))

            if val == 1:
                pygame.draw.rect(screen, MAP_WALL, rect)
            elif val == 2:
                pygame.draw.rect(screen, FINISH, rect)
            else:
                colour = MAP_VISITED if (x, y) in visited else MAP_PATH
                pygame.draw.rect(screen, colour, rect)

    px = x0 + int((player.x / CELL_SIZE) * scale)
    py = y0 + int((player.y / CELL_SIZE) * scale)
    pygame.draw.circle(screen, MAP_PLAYER, (px, py), 4)
    pygame.draw.line(
        screen,
        MAP_PLAYER,
        (px, py),
        (px + int(math.cos(player.angle) * 12), py + int(math.sin(player.angle) * 12)),
        2,
    )


def draw_hud(screen, font, won, show_full_map):
    title = font.render("Hendrix Maze", True, TEXT)
    screen.blit(title, (14, 12))

    help1 = font.render("Mouse: move and turn   R: new maze   M: map   ESC: quit", True, TEXT)
    screen.blit(help1, (14, SCREEN_H - 34))

    if show_full_map:
        hint = font.render("Full map view is ON", True, FINISH)
        screen.blit(hint, (14, 44))

    if won:
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 40, 30, 175))
        screen.blit(overlay, (0, 0))

        big = pygame.font.SysFont(None, 64)
        msg = big.render("You found the green finish!", True, FINISH)
        sub = font.render("Press R for a new maze or ESC to quit", True, TEXT)

        screen.blit(msg, msg.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 35)))
        screen.blit(sub, sub.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 30)))


def start_game():
    pygame.init()
    pygame.display.set_caption("Hendrix Maze")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 26)

    pygame.mouse.set_visible(True)

    def reset():
        grid = generate_maze(MAZE_W, MAZE_H)
        player = Player(1.5 * CELL_SIZE, 1.5 * CELL_SIZE, 0.0)
        visited = set()
        return grid, player, visited, False

    grid, player, visited, won = reset()
    show_full_map = False

    while True:
        dt = clock.tick(FPS) / 1000.0
        mouse_dx = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_r:
                    grid, player, visited, won = reset()
                if event.key == pygame.K_m:
                    show_full_map = not show_full_map

            if event.type == pygame.MOUSEMOTION:
                mouse_dx = event.rel[0]

        keys = pygame.key.get_pressed()
        buttons = pygame.mouse.get_pressed()

        if not won:
            # Mouse turning
            player.angle += mouse_dx * MOUSE_TURN_SPEED

            # Keyboard turning fallback
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                player.angle -= TURN_SPEED * dt
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                player.angle += TURN_SPEED * dt

            # Mouse movement
            if buttons[0]:
                move_player(grid, player, MOVE_SPEED * dt)
            if buttons[2]:
                move_player(grid, player, -MOVE_SPEED * dt)

            # Keyboard movement fallback
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                move_player(grid, player, MOVE_SPEED * dt)
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                move_player(grid, player, -MOVE_SPEED * dt)

            cx = int(player.x // CELL_SIZE)
            cy = int(player.y // CELL_SIZE)
            visited.add((cx, cy))

            # Reveal adjacent cells so the learned map feels useful
            for oy in (-1, 0, 1):
                for ox in (-1, 0, 1):
                    visited.add((cx + ox, cy + oy))

            if cell_at(grid, player.x, player.y) == 2:
                won = True

        # Draw background
        screen.fill(SKY)
        pygame.draw.rect(screen, FLOOR, (0, SCREEN_H // 2, SCREEN_W, SCREEN_H // 2))

        cast_rays(screen, grid, player)
        draw_minimap(screen, grid, player, visited, show_full_map)
        draw_hud(screen, font, won, show_full_map)

        pygame.display.flip()


if __name__ == "__main__":
    start_game()
