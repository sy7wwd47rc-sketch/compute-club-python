import math
import random
import sys
from dataclasses import dataclass

import pygame


# Crue's Dog Rescue
# A child-friendly top-down game for Raspberry Pi / Computer Club.
#
# Story:
# A family is playing in a big field. The dog gets let off the lead and runs away.
# Two suspicious men take the dog. The family jumps in the car and searches the
# estate to rescue the dog.
#
# Controls:
#   Move mouse       = steer the car towards the mouse
#   Hold left mouse  = drive
#   R               = restart
#   ESC             = quit


SCREEN_W = 1000
SCREEN_H = 650
FPS = 60

CAR_SPEED = 210
CAR_TURN_SMOOTHING = 7.0
SEARCH_DISTANCE = 55

GRASS = (60, 165, 70)
FIELD_GRASS = (90, 190, 80)
ROAD = (70, 70, 75)
ROAD_LINE = (235, 235, 180)
HOUSE = (120, 160, 215)
HOUSE_ROOF = (40, 80, 145)
PAVEMENT = (150, 150, 145)
CAR = (35, 120, 235)
CAR_WINDOW = (180, 230, 255)
DOG = (165, 95, 40)
DOG_EAR = (85, 50, 25)
BOY = (60, 130, 240)
GIRL = (245, 80, 170)
MAN = (55, 55, 55)
TEXT = (245, 255, 245)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
FOUND = (80, 255, 130)


@dataclass
class CarState:
    x: float
    y: float
    angle: float


@dataclass
class DogState:
    x: float
    y: float
    found: bool = False


@dataclass
class StoryState:
    stage: str
    timer: float = 0.0
    message: str = ""


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def dist(a, b, c, d):
    return math.hypot(a - c, b - d)


def draw_text(screen, font, text, pos, colour=TEXT):
    surf = font.render(text, True, colour)
    screen.blit(surf, pos)


def draw_wrapped_text(screen, font, text, rect, colour=TEXT):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = current + (" " if current else "") + word
        if font.size(test)[0] <= rect.width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    y = rect.y
    for line in lines:
        surf = font.render(line, True, colour)
        screen.blit(surf, (rect.x, y))
        y += font.get_height() + 3


def draw_boy(screen, x, y):
    pygame.draw.circle(screen, (245, 205, 165), (int(x), int(y - 18)), 10)
    pygame.draw.rect(screen, BOY, (x - 8, y - 8, 16, 25), border_radius=4)
    pygame.draw.line(screen, BLACK, (x - 5, y + 16), (x - 10, y + 30), 3)
    pygame.draw.line(screen, BLACK, (x + 5, y + 16), (x + 10, y + 30), 3)


def draw_girl(screen, x, y):
    pygame.draw.circle(screen, (245, 205, 165), (int(x), int(y - 18)), 10)
    pygame.draw.polygon(screen, GIRL, [(x, y - 8), (x - 15, y + 20), (x + 15, y + 20)])
    pygame.draw.line(screen, BLACK, (x - 5, y + 18), (x - 10, y + 30), 3)
    pygame.draw.line(screen, BLACK, (x + 5, y + 18), (x + 10, y + 30), 3)


def draw_dog(screen, x, y, wag=False):
    # Body
    pygame.draw.ellipse(screen, DOG, (x - 16, y - 9, 32, 18))
    pygame.draw.circle(screen, DOG, (int(x + 17), int(y - 5)), 9)
    pygame.draw.circle(screen, DOG_EAR, (int(x + 12), int(y - 12)), 5)
    # Legs
    for lx in (-9, 6):
        pygame.draw.line(screen, DOG_EAR, (x + lx, y + 6), (x + lx, y + 17), 3)
    # Tail
    tail_end = (x - 25, y - 13 if wag else y - 6)
    pygame.draw.line(screen, DOG_EAR, (x - 15, y - 4), tail_end, 4)
    # Eye
    pygame.draw.circle(screen, BLACK, (int(x + 20), int(y - 8)), 2)


def draw_man(screen, x, y):
    pygame.draw.circle(screen, (220, 185, 145), (int(x), int(y - 18)), 9)
    pygame.draw.rect(screen, MAN, (x - 8, y - 8, 16, 25), border_radius=4)
    pygame.draw.line(screen, BLACK, (x - 5, y + 16), (x - 9, y + 29), 3)
    pygame.draw.line(screen, BLACK, (x + 5, y + 16), (x + 9, y + 29), 3)
    pygame.draw.rect(screen, BLACK, (x - 10, y - 30, 20, 5))


def draw_house(screen, x, y, w, h):
    pygame.draw.rect(screen, HOUSE, (x, y, w, h))
    pygame.draw.polygon(screen, HOUSE_ROOF, [(x - 8, y), (x + w / 2, y - 28), (x + w + 8, y)])
    pygame.draw.rect(screen, WHITE, (x + 12, y + 14, 18, 18))
    pygame.draw.rect(screen, WHITE, (x + w - 30, y + 14, 18, 18))
    pygame.draw.rect(screen, (100, 70, 45), (x + w / 2 - 8, y + h - 30, 16, 30))


def draw_estate(screen):
    screen.fill(GRASS)

    # Big field area
    pygame.draw.rect(screen, FIELD_GRASS, (20, 20, 350, 250), border_radius=20)
    pygame.draw.rect(screen, (40, 130, 55), (20, 20, 350, 250), 4, border_radius=20)

    # Roads - simple council-estate style loop and side roads
    roads = [
        pygame.Rect(390, 0, 75, 650),
        pygame.Rect(0, 300, 1000, 75),
        pygame.Rect(640, 90, 75, 500),
        pygame.Rect(465, 90, 250, 65),
        pygame.Rect(465, 520, 250, 65),
        pygame.Rect(760, 300, 75, 250),
        pygame.Rect(120, 375, 75, 190),
    ]

    for r in roads:
        pygame.draw.rect(screen, ROAD, r)
        pygame.draw.rect(screen, PAVEMENT, r, 4)

    # Road markings
    for y in range(15, 650, 55):
        pygame.draw.rect(screen, ROAD_LINE, (425, y, 5, 28))
        pygame.draw.rect(screen, ROAD_LINE, (675, y + 15, 5, 28))
    for x in range(15, 1000, 65):
        pygame.draw.rect(screen, ROAD_LINE, (x, 335, 34, 5))

    # Houses
    houses = [
        (505, 185, 80, 70), (610, 185, 80, 70), (735, 120, 80, 70),
        (850, 120, 80, 70), (505, 410, 80, 70), (610, 410, 80, 70),
        (820, 420, 80, 70), (230, 410, 80, 70), (35, 405, 70, 65),
        (220, 100, 70, 65),
    ]
    for h in houses:
        draw_house(screen, *h)

    # Trees / bushes
    for x, y in [(70, 80), (130, 130), (280, 210), (930, 570), (910, 270), (80, 590)]:
        pygame.draw.circle(screen, (30, 125, 50), (x, y), 22)
        pygame.draw.rect(screen, (85, 55, 25), (x - 4, y + 12, 8, 20))


def draw_car(screen, car):
    # Draw a rotated simple car
    surf = pygame.Surface((60, 36), pygame.SRCALPHA)
    pygame.draw.rect(surf, CAR, (5, 5, 50, 26), border_radius=8)
    pygame.draw.rect(surf, CAR_WINDOW, (31, 9, 15, 18), border_radius=3)
    pygame.draw.circle(surf, BLACK, (16, 6), 5)
    pygame.draw.circle(surf, BLACK, (44, 6), 5)
    pygame.draw.circle(surf, BLACK, (16, 31), 5)
    pygame.draw.circle(surf, BLACK, (44, 31), 5)
    pygame.draw.polygon(surf, WHITE, [(55, 18), (45, 12), (45, 24)])

    rotated = pygame.transform.rotate(surf, -math.degrees(car.angle))
    rect = rotated.get_rect(center=(car.x, car.y))
    screen.blit(rotated, rect)


def draw_story_scene(screen, font, big_font, story):
    draw_estate(screen)
    draw_boy(screen, 95, 180)
    draw_girl(screen, 150, 180)

    # Dog runs away during intro
    dog_x = 210 + min(120, story.timer * 55)
    dog_y = 177 + math.sin(story.timer * 5) * 8
    draw_dog(screen, dog_x, dog_y, wag=True)

    # Suspicious men near path
    draw_man(screen, 315, 180)
    draw_man(screen, 345, 185)

    panel = pygame.Rect(60, 455, 880, 135)
    pygame.draw.rect(screen, (0, 45, 60), panel, border_radius=12)
    pygame.draw.rect(screen, FOUND, panel, 3, border_radius=12)

    title = big_font.render("Crue's Dog Rescue", True, FOUND)
    screen.blit(title, title.get_rect(center=(SCREEN_W // 2, 485)))

    draw_wrapped_text(
        screen,
        font,
        "The family are playing in the big field. The dog runs off, and two suspicious men take him away. Jump in the car and search the estate to rescue the dog!",
        pygame.Rect(90, 515, 820, 60),
        TEXT,
    )

    draw_text(screen, font, "Click the mouse to start driving.", (350, 595), FOUND)


def find_random_dog_place():
    # Avoid putting the dog in the start field; use an estate area.
    places = [
        (890, 540), (880, 240), (755, 480), (560, 260), (560, 500),
        (710, 245), (255, 520), (930, 350), (790, 165)
    ]
    return random.choice(places)


def restart_game():
    car = CarState(120, 335, 0.0)
    dog_x, dog_y = find_random_dog_place()
    dog = DogState(dog_x, dog_y, False)
    men = [(dog_x - 45, dog_y + 20), (dog_x + 42, dog_y + 15)]
    story = StoryState("intro", 0.0, "")
    return car, dog, men, story


def main():
    pygame.init()
    pygame.display.set_caption("Crue's Dog Rescue")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 26)
    big_font = pygame.font.SysFont(None, 54)

    car, dog, men, story = restart_game()

    while True:
        dt = clock.tick(FPS) / 1000.0
        story.timer += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_r:
                    car, dog, men, story = restart_game()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if story.stage == "intro":
                    story.stage = "drive"
                    story.timer = 0.0
                elif story.stage == "won":
                    car, dog, men, story = restart_game()

        if story.stage == "drive":
            mouse_x, mouse_y = pygame.mouse.get_pos()
            buttons = pygame.mouse.get_pressed()

            target_angle = math.atan2(mouse_y - car.y, mouse_x - car.x)

            # Smooth turning towards mouse pointer
            angle_diff = (target_angle - car.angle + math.pi) % (math.tau) - math.pi
            car.angle += angle_diff * min(1, CAR_TURN_SMOOTHING * dt)

            if buttons[0]:
                car.x += math.cos(car.angle) * CAR_SPEED * dt
                car.y += math.sin(car.angle) * CAR_SPEED * dt

            car.x = clamp(car.x, 25, SCREEN_W - 25)
            car.y = clamp(car.y, 25, SCREEN_H - 25)

            if dist(car.x, car.y, dog.x, dog.y) < SEARCH_DISTANCE:
                dog.found = True
                story.stage = "won"
                story.timer = 0.0

        draw_estate(screen)

        if story.stage == "intro":
            draw_story_scene(screen, font, big_font, story)

        else:
            # Family in car search scene
            draw_car(screen, car)

            if not dog.found:
                # Only draw dog when player is fairly near; makes it a search game.
                if dist(car.x, car.y, dog.x, dog.y) < 170:
                    draw_dog(screen, dog.x, dog.y, wag=True)

                # Draw suspicious men near the dog, also only when close enough
                if dist(car.x, car.y, dog.x, dog.y) < 220:
                    for x, y in men:
                        draw_man(screen, x, y)

            # HUD
            pygame.draw.rect(screen, (0, 40, 55), (10, 10, 510, 82), border_radius=10)
            pygame.draw.rect(screen, FOUND, (10, 10, 510, 82), 2, border_radius=10)
            draw_text(screen, font, "Crue's Dog Rescue", (25, 22), FOUND)
            draw_text(screen, font, "Hold left mouse button to drive. Steer with the mouse.", (25, 50), TEXT)
            draw_text(screen, font, "Search roads, houses and the estate. Press R to restart.", (25, 72), TEXT)

            # Small search meter
            d = int(dist(car.x, car.y, dog.x, dog.y))
            hint = "Hot!" if d < 130 else "Getting closer..." if d < 260 else "Keep searching..."
            pygame.draw.rect(screen, (0, 40, 55), (780, 12, 205, 50), border_radius=10)
            pygame.draw.rect(screen, FOUND, (780, 12, 205, 50), 2, border_radius=10)
            draw_text(screen, font, hint, (798, 28), FOUND if d < 130 else TEXT)

            if story.stage == "won":
                overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
                overlay.fill((0, 45, 35, 175))
                screen.blit(overlay, (0, 0))

                draw_dog(screen, SCREEN_W // 2, SCREEN_H // 2 + 40, wag=True)
                title = big_font.render("You rescued the dog!", True, FOUND)
                sub = font.render("The family are happy. Click or press R to play again.", True, TEXT)

                screen.blit(title, title.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 45)))
                screen.blit(sub, sub.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 95)))

        pygame.display.flip()


if __name__ == "__main__":
    main()
