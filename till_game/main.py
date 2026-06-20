"""
Kids Barcode Checkout Game
Author: ChatGPT for Tony

A colourful Python game that lets children play shop.

Features:
- Looks like a simple shop till
- Uses the MacBook camera to scan barcodes if optional libraries are installed
- Manual barcode entry fallback
- If a barcode is new, the child/adult can enter item name and price
- Saves known products locally
- Adds items to a basket and keeps a running total
- Checkout beep when an item is scanned/added
- Clear basket and remove last item
- Colourful child-friendly screen

Install basic game:
    python3 -m pip install pygame

Optional camera barcode scanning:
    python3 -m pip install opencv-python pyzbar

Mac note for barcode scanning:
    pyzbar may also need zbar installed:
    brew install zbar

Run:
    python3 kids_barcode_checkout_game.py

If barcode scanning is awkward on a Mac, the game still works with manual barcode entry.
"""

from __future__ import annotations

import json
import math
import os
import struct
import sys
import time
import wave
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pygame

# Optional camera/barcode libraries.
# The game still works without them using manual entry.
try:
    import cv2  # type: ignore
except Exception:
    cv2 = None

try:
    from pyzbar.pyzbar import decode as barcode_decode  # type: ignore
except Exception:
    barcode_decode = None


# -----------------------------
# Basic setup
# -----------------------------

WIDTH, HEIGHT = 1200, 760
FPS = 60

BASE_DIR = Path(__file__).resolve().parent
PRODUCT_DB_FILE = BASE_DIR / "kids_checkout_products.json"
SOUND_DIR = BASE_DIR / "kids_checkout_sounds"

# Online lookup:
# - Open Food Facts can usually provide a product name for food barcodes.
# - Supermarket prices are location/account dependent, so the game keeps price entry local/manual.
OPEN_FOOD_FACTS_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json?fields=product_name,brands,quantity"

pygame.init()
pygame.font.init()

try:
    pygame.mixer.init()
except pygame.error:
    pass


# -----------------------------
# Colours
# -----------------------------

WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
DARK = (40, 45, 55)
GREY = (210, 215, 225)
MID_GREY = (130, 140, 150)

BLUE = (75, 150, 255)
LIGHT_BLUE = (205, 230, 255)
GREEN = (65, 200, 120)
LIGHT_GREEN = (205, 250, 220)
RED = (235, 85, 85)
LIGHT_RED = (255, 215, 215)
YELLOW = (255, 220, 80)
LIGHT_YELLOW = (255, 245, 190)
PURPLE = (160, 115, 255)
LIGHT_PURPLE = (230, 220, 255)
ORANGE = (255, 165, 70)
LIGHT_ORANGE = (255, 230, 200)
PINK = (255, 120, 185)
LIGHT_PINK = (255, 220, 240)
CYAN = (75, 210, 220)
LIGHT_CYAN = (210, 250, 252)


# -----------------------------
# Fonts
# -----------------------------

FONT_TITLE = pygame.font.SysFont("arialrounded", 44, bold=True)
FONT_BIG = pygame.font.SysFont("arialrounded", 34, bold=True)
FONT_MED = pygame.font.SysFont("arialrounded", 24, bold=True)
FONT_SMALL = pygame.font.SysFont("arialrounded", 19)
FONT_TINY = pygame.font.SysFont("arialrounded", 16)
FONT_RECEIPT = pygame.font.SysFont("menlo", 18)


# -----------------------------
# Helpers
# -----------------------------

def rounded_rect(
    surface: pygame.Surface,
    rect: pygame.Rect,
    color: Tuple[int, int, int],
    radius: int = 16,
    border: int = 0,
    border_color: Tuple[int, int, int] = BLACK,
) -> None:
    pygame.draw.rect(surface, color, rect, border_radius=radius)
    if border:
        pygame.draw.rect(surface, border_color, rect, width=border, border_radius=radius)


def draw_text(
    surface: pygame.Surface,
    text: str,
    pos: Tuple[int, int],
    font: pygame.font.Font,
    color: Tuple[int, int, int] = BLACK,
    max_width: Optional[int] = None,
) -> None:
    x, y = pos
    if max_width is None:
        img = font.render(text, True, color)
        surface.blit(img, (x, y))
        return

    words = text.split(" ")
    line = ""
    line_height = font.get_height() + 4

    for word in words:
        test = f"{line} {word}".strip()
        if font.size(test)[0] <= max_width:
            line = test
        else:
            if line:
                img = font.render(line, True, color)
                surface.blit(img, (x, y))
            y += line_height
            line = word

    if line:
        img = font.render(line, True, color)
        surface.blit(img, (x, y))


def fit_text(text: str, font: pygame.font.Font, max_width: int) -> str:
    """Shorten text with ... so it fits in a fixed width."""
    if font.size(text)[0] <= max_width:
        return text

    ellipsis = "..."
    while text and font.size(text + ellipsis)[0] > max_width:
        text = text[:-1]
    return text + ellipsis if text else ellipsis


def draw_text_clipped(
    surface: pygame.Surface,
    text: str,
    pos: Tuple[int, int],
    font: pygame.font.Font,
    color: Tuple[int, int, int],
    clip_rect: pygame.Rect,
) -> None:
    """Draw text but clip it to a rectangle."""
    old_clip = surface.get_clip()
    surface.set_clip(clip_rect)
    img = font.render(text, True, color)
    surface.blit(img, pos)
    surface.set_clip(old_clip)


def format_money(value: float) -> str:
    return f"£{value:.2f}"


def create_beep_wav(path: Path, frequency: int, duration: float, volume: float) -> None:
    sample_rate = 44100
    samples = int(sample_rate * duration)
    path.parent.mkdir(exist_ok=True)

    with wave.open(str(path), "w") as wav:
        wav.setparams((1, 2, sample_rate, samples, "NONE", "not compressed"))
        for i in range(samples):
            t = i / sample_rate
            value = int(32767 * volume * math.sin(2 * math.pi * frequency * t))
            wav.writeframes(struct.pack("<h", value))


def ensure_sounds() -> Dict[str, Optional[pygame.mixer.Sound]]:
    sounds: Dict[str, Optional[pygame.mixer.Sound]] = {
        "scan": None,
        "wrong": None,
        "clear": None,
    }

    try:
        SOUND_DIR.mkdir(exist_ok=True)

        scan = SOUND_DIR / "checkout_scan.wav"
        wrong = SOUND_DIR / "wrong.wav"
        clear = SOUND_DIR / "clear.wav"

        if not scan.exists():
            create_beep_wav(scan, 1040, 0.08, 0.35)
        if not wrong.exists():
            create_beep_wav(wrong, 180, 0.18, 0.35)
        if not clear.exists():
            create_beep_wav(clear, 520, 0.10, 0.35)

        sounds["scan"] = pygame.mixer.Sound(str(scan))
        sounds["wrong"] = pygame.mixer.Sound(str(wrong))
        sounds["clear"] = pygame.mixer.Sound(str(clear))
    except Exception:
        pass

    return sounds


SOUNDS = ensure_sounds()


def play_sound(name: str) -> None:
    snd = SOUNDS.get(name)
    if snd:
        try:
            snd.play()
        except Exception:
            pass


# -----------------------------
# Data
# -----------------------------

@dataclass
class Product:
    barcode: str
    name: str
    price: float


@dataclass
class OnlineLookup:
    name: Optional[str] = None
    estimated_price: Optional[float] = None
    price_note: str = ""
    category_text: str = ""


@dataclass
class BasketItem:
    barcode: str
    name: str
    price: float


def load_products() -> Dict[str, Product]:
    if not PRODUCT_DB_FILE.exists():
        return {}

    try:
        raw = json.loads(PRODUCT_DB_FILE.read_text(encoding="utf-8"))
        products = {}
        for barcode, product in raw.items():
            products[barcode] = Product(
                barcode=str(product["barcode"]),
                name=str(product["name"]),
                price=float(product["price"]),
            )
        return products
    except Exception:
        return {}


def save_products(products: Dict[str, Product]) -> None:
    raw = {barcode: asdict(product) for barcode, product in products.items()}
    PRODUCT_DB_FILE.write_text(json.dumps(raw, indent=2), encoding="utf-8")


def estimate_price_from_product_text(name: str, category_text: str = "") -> Tuple[float, str]:
    """Return a child-game friendly approximate UK supermarket price.

    This is deliberately an estimate, not a live shop price.
    The parent/adult can overwrite the value before saving.
    """
    text = f"{name} {category_text}".lower()

    rules = [
        (("milk",), 1.60, "approx milk price"),
        (("bread", "loaf"), 1.40, "approx bread price"),
        (("egg", "eggs"), 2.40, "approx eggs price"),
        (("butter",), 2.20, "approx butter price"),
        (("cheese",), 2.50, "approx cheese price"),
        (("yogurt", "yoghurt"), 1.50, "approx yoghurt price"),
        (("cereal", "corn flakes", "weetabix"), 2.50, "approx cereal price"),
        (("pasta", "spaghetti"), 1.20, "approx pasta price"),
        (("rice",), 1.50, "approx rice price"),
        (("beans", "baked beans"), 0.90, "approx tin price"),
        (("soup",), 1.20, "approx soup price"),
        (("tomato", "chopped tomatoes"), 0.80, "approx tin price"),
        (("crisps",), 1.75, "approx crisps price"),
        (("chocolate", "bar"), 1.25, "approx chocolate price"),
        (("biscuit", "cookies"), 1.50, "approx biscuits price"),
        (("juice",), 1.60, "approx juice price"),
        (("cola", "coke", "pepsi", "fanta", "sprite", "lemonade"), 1.85, "approx drink price"),
        (("water",), 0.90, "approx water price"),
        (("tea",), 2.50, "approx tea price"),
        (("coffee",), 3.50, "approx coffee price"),
        (("shampoo",), 2.50, "approx shampoo price"),
        (("toothpaste",), 1.50, "approx toothpaste price"),
        (("soap", "shower gel"), 1.50, "approx wash item price"),
        (("washing", "detergent", "laundry"), 4.50, "approx laundry price"),
        (("toilet roll", "toilet tissue"), 4.00, "approx household price"),
        (("kitchen roll",), 2.50, "approx household price"),
        (("banana", "apple", "orange", "fruit"), 1.50, "approx fruit price"),
        (("potato", "carrot", "onion", "vegetable"), 1.20, "approx vegetable price"),
    ]

    for keywords, price, note in rules:
        if any(keyword in text for keyword in keywords):
            return price, note

    return 1.99, "rough default estimate"


def lookup_product_online(barcode: str) -> OnlineLookup:
    """Try to find product name online, then estimate a sensible price.

    Open Food Facts is used for the name/category.
    The price is an approximate child-game estimate and can be overwritten.
    """
    safe_barcode = urllib.parse.quote(barcode.strip())
    url = OPEN_FOOD_FACTS_URL.format(barcode=safe_barcode)

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "KidsBarcodeCheckoutGame/1.0 educational local game",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))

        if data.get("status") != 1:
            price, note = estimate_price_from_product_text("")
            return OnlineLookup(None, price, note, "")

        product = data.get("product", {})
        name = str(product.get("product_name") or "").strip()
        brand = str(product.get("brands") or "").split(",")[0].strip()
        quantity = str(product.get("quantity") or "").strip()
        category_text = " ".join([
            str(product.get("categories") or ""),
            " ".join(product.get("categories_tags") or []),
        ])

        parts = []
        if brand:
            parts.append(brand)
        if name:
            parts.append(name)
        if quantity:
            parts.append(quantity)

        full_name = " ".join(parts).strip()[:60] or None
        price, note = estimate_price_from_product_text(full_name or "", category_text)

        return OnlineLookup(full_name, price, note, category_text[:80])

    except Exception:
        price, note = estimate_price_from_product_text("")
        return OnlineLookup(None, price, note, "")


# -----------------------------
# UI widgets
# -----------------------------

class Button:
    def __init__(self, rect: pygame.Rect, text: str, color: Tuple[int, int, int]):
        self.rect = rect
        self.text = text
        self.color = color

    def draw(self, screen: pygame.Surface) -> None:
        rounded_rect(screen, self.rect, self.color, 14, 2, DARK)
        img = FONT_SMALL.render(self.text, True, WHITE)
        screen.blit(img, img.get_rect(center=self.rect.center))

    def clicked(self, event: pygame.event.Event) -> bool:
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)


# -----------------------------
# Game
# -----------------------------

class CheckoutGame:
    def __init__(self) -> None:
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Kids Barcode Checkout Game")
        self.clock = pygame.time.Clock()

        self.products: Dict[str, Product] = load_products()
        self.basket: List[BasketItem] = []
        self.basket_scroll = 0
        self.basket_visible_rows = 12

        self.mode = "till"  # till, manual_barcode, new_name, new_price, camera
        self.input_text = ""
        self.pending_barcode = ""
        self.pending_name = ""
        self.pending_estimated_price: Optional[float] = None
        self.suggested_name = ""
        self.lookup_status = ""
        self.confirm_clear_basket = False

        self.message = "Welcome to the shop! Scan or type a barcode to start."
        self.message_color = DARK

        self.scan_button = Button(pygame.Rect(40, 665, 180, 55), "Camera scan", GREEN)
        self.type_button = Button(pygame.Rect(240, 665, 180, 55), "Type barcode", BLUE)
        self.remove_button = Button(pygame.Rect(440, 665, 180, 55), "Remove last", ORANGE)
        self.clear_button = Button(pygame.Rect(640, 665, 180, 55), "Clear basket", RED)
        self.done_button = Button(pygame.Rect(840, 665, 180, 55), "Checkout", PURPLE)

        self.camera = None
        self.last_scanned = ""
        self.last_scan_time = 0.0
        self.camera_surface: Optional[pygame.Surface] = None
        self.camera_error = ""
        self.torch_enabled = False
        self.torch_supported = False
        self.scan_attempts = 0
        self.torch_button = Button(pygame.Rect(510, 585, 180, 45), "Torch / flash", ORANGE)

    def run(self) -> None:
        while True:
            self.clock.tick(FPS)
            self.handle_events()
            self.update()
            self.draw()
            pygame.display.flip()

    # -----------------------------
    # Event handling
    # -----------------------------

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.close_camera()
                pygame.quit()
                sys.exit(0)

            if self.mode == "till":
                self.handle_till_event(event)
            elif self.mode in {"manual_barcode", "new_name", "new_price"}:
                self.handle_text_input_event(event)
            elif self.mode == "camera":
                self.handle_camera_event(event)

    def handle_till_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEWHEEL:
            mouse_pos = pygame.mouse.get_pos()
            basket_area = pygame.Rect(60, 160, 630, 420)
            if basket_area.collidepoint(mouse_pos):
                self.scroll_basket(-event.y)
            return

        if self.scan_button.clicked(event):
            self.confirm_clear_basket = False
            self.start_camera_scan()
        elif self.type_button.clicked(event):
            self.confirm_clear_basket = False
            self.mode = "manual_barcode"
            self.input_text = ""
            self.message = "Type the barcode number, then press Enter."
            self.message_color = BLUE
        elif self.remove_button.clicked(event):
            self.confirm_clear_basket = False
            self.remove_last()
        elif self.clear_button.clicked(event):
            self.request_clear_basket()
        elif self.done_button.clicked(event):
            self.confirm_clear_basket = False
            total = self.total()
            self.message = f"Checkout complete. Total to pay: {format_money(total)}. Great shopping!"
            self.message_color = GREEN
            play_sound("scan")

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_s:
                self.start_camera_scan()
            elif event.key == pygame.K_t:
                self.mode = "manual_barcode"
                self.input_text = ""
            elif event.key == pygame.K_BACKSPACE:
                self.remove_last()
            elif event.key == pygame.K_c:
                self.request_clear_basket()
            elif event.key == pygame.K_UP:
                self.scroll_basket(-1)
            elif event.key == pygame.K_DOWN:
                self.scroll_basket(1)
            elif event.key == pygame.K_PAGEUP:
                self.scroll_basket(-self.basket_visible_rows)
            elif event.key == pygame.K_PAGEDOWN:
                self.scroll_basket(self.basket_visible_rows)
            elif event.key == pygame.K_HOME:
                self.basket_scroll = 0
            elif event.key == pygame.K_END:
                self.basket_scroll = max(0, len(self.basket) - self.basket_visible_rows)

    def handle_text_input_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            self.mode = "till"
            self.input_text = ""
            self.pending_barcode = ""
            self.pending_name = ""
            self.pending_estimated_price = None
            self.suggested_name = ""
            self.lookup_status = ""
            self.message = "Cancelled."
            self.message_color = MID_GREY
            return

        if event.key == pygame.K_BACKSPACE:
            self.input_text = self.input_text[:-1]
            return

        if event.key == pygame.K_RETURN:
            self.process_text_enter()
            return

        if event.key == pygame.K_TAB:
            if self.mode == "new_name" and self.suggested_name:
                self.input_text = self.suggested_name
                self.message = "Copied the suggested item name. Press Enter to use it."
                self.message_color = GREEN
                play_sound("scan")
            elif self.mode == "new_price" and self.pending_estimated_price is not None:
                self.input_text = f"{self.pending_estimated_price:.2f}"
                self.message = "Copied the suggested price. Press Enter to use it."
                self.message_color = GREEN
                play_sound("scan")
            return

        if len(self.input_text) < 60 and event.unicode.isprintable():
            self.input_text += event.unicode

    def handle_camera_event(self, event: pygame.event.Event) -> None:
        if self.torch_button.clicked(event):
            self.toggle_torch()
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.close_camera()
                self.mode = "till"
                self.message = "Camera scan cancelled."
                self.message_color = MID_GREY
            elif event.key == pygame.K_f:
                self.toggle_torch()

    # -----------------------------
    # Logic
    # -----------------------------

    def process_text_enter(self) -> None:
        text = self.input_text.strip()

        if self.mode == "manual_barcode":
            if not text:
                play_sound("wrong")
                return
            self.handle_barcode(text)
            self.input_text = ""

        elif self.mode == "new_name":
            if not text:
                self.message = "Please type an item name."
                self.message_color = RED
                play_sound("wrong")
                return
            self.pending_name = text
            if self.pending_estimated_price is None:
                estimated, note = estimate_price_from_product_text(self.pending_name)
                self.pending_estimated_price = estimated
            else:
                estimated = self.pending_estimated_price
                _, note = estimate_price_from_product_text(self.pending_name)

            self.input_text = f"{estimated:.2f}"
            self.mode = "new_price"
            self.lookup_status = f"Approx price: {self.input_text} ({note}). Press Tab to copy it again or change it."
            self.message = f"Check or change the price for {self.pending_name}."
            self.message_color = BLUE

        elif self.mode == "new_price":
            try:
                price = float(text.replace("£", "").strip())
                if price < 0:
                    raise ValueError
            except ValueError:
                self.message = "That price does not look right. Try something like 1.25"
                self.message_color = RED
                play_sound("wrong")
                return

            product = Product(self.pending_barcode, self.pending_name, price)
            self.products[self.pending_barcode] = product
            save_products(self.products)

            self.add_product_to_basket(product)
            self.mode = "till"
            self.input_text = ""
            self.pending_barcode = ""
            self.pending_name = ""
            self.pending_estimated_price = None
            self.suggested_name = ""
            self.lookup_status = ""

    def handle_barcode(self, barcode: str) -> None:
        barcode = barcode.strip()
        self.confirm_clear_basket = False

        if barcode in self.products:
            product = self.products[barcode]
            self.add_product_to_basket(product)
            self.mode = "till"
            return

        self.pending_barcode = barcode
        self.input_text = ""

        online = lookup_product_online(barcode)

        if online.name:
            self.suggested_name = online.name
            self.pending_name = ""
            self.pending_estimated_price = online.estimated_price
            self.mode = "new_name"
            self.lookup_status = (
                f"Suggested name found. Type it for practice, or press Tab to copy it."
            )
            self.message = "Product name found. Practise typing it or press Tab."
            self.message_color = GREEN
            play_sound("scan")
        else:
            self.pending_name = ""
            self.suggested_name = ""
            self.pending_estimated_price = online.estimated_price
            self.mode = "new_name"
            self.lookup_status = "No product name found. Add the name; I will suggest an approximate price next."
            self.message = "New barcode found. Please enter the item name."
            self.message_color = ORANGE
            play_sound("wrong")

    def add_product_to_basket(self, product: Product) -> None:
        self.confirm_clear_basket = False
        self.basket.append(BasketItem(product.barcode, product.name, product.price))
        self.basket_scroll = max(0, len(self.basket) - self.basket_visible_rows)
        self.message = f"Beep! Added {product.name} for {format_money(product.price)}."
        self.message_color = GREEN
        play_sound("scan")

    def remove_last(self) -> None:
        self.confirm_clear_basket = False
        if not self.basket:
            self.message = "The basket is already empty."
            self.message_color = MID_GREY
            play_sound("wrong")
            return

        removed = self.basket.pop()
        self.clamp_basket_scroll()
        self.message = f"Removed {removed.name}."
        self.message_color = ORANGE
        play_sound("clear")

    def request_clear_basket(self) -> None:
        self.confirm_clear_basket = False
        if not self.basket:
            self.message = "The basket is already empty."
            self.message_color = MID_GREY
            self.confirm_clear_basket = False
            play_sound("wrong")
            return

        if not self.confirm_clear_basket:
            self.confirm_clear_basket = True
            self.message = "Press Clear basket again to delete all basket items."
            self.message_color = RED
            play_sound("wrong")
            return

        self.clear_basket()

    def clear_basket(self) -> None:
        self.basket.clear()
        self.basket_scroll = 0
        self.confirm_clear_basket = False
        self.message = "Basket cleared. Start a new shop!"
        self.message_color = RED
        play_sound("clear")

    def total(self) -> float:
        return sum(item.price for item in self.basket)

    def clamp_basket_scroll(self) -> None:
        max_scroll = max(0, len(self.basket) - self.basket_visible_rows)
        self.basket_scroll = max(0, min(self.basket_scroll, max_scroll))

    def scroll_basket(self, amount: int) -> None:
        self.basket_scroll += amount
        self.clamp_basket_scroll()

    # -----------------------------
    # Camera
    # -----------------------------

    def start_camera_scan(self) -> None:
        if cv2 is None or barcode_decode is None:
            self.mode = "manual_barcode"
            self.input_text = ""
            self.message = (
                "Camera scanning needs opencv-python, pyzbar and zbar. "
                "For now, type the barcode and press Enter."
            )
            self.message_color = ORANGE
            play_sound("wrong")
            return

        try:
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                raise RuntimeError("Camera could not be opened.")

            # Ask for a larger frame. Not every camera honours this, but it helps barcode accuracy when it does.
            try:
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            except Exception:
                pass

            self.mode = "camera"
            self.camera_error = ""
            self.torch_enabled = False
            self.torch_supported = False
            self.scan_attempts = 0
            self.message = "Hold the barcode steady inside the green box. Press F for torch if supported."
            self.message_color = BLUE
        except Exception as exc:
            self.close_camera()
            self.mode = "manual_barcode"
            self.input_text = ""
            self.camera_error = str(exc)
            self.message = "Camera could not open. Type the barcode instead."
            self.message_color = ORANGE
            play_sound("wrong")

    def close_camera(self) -> None:
        if self.camera is not None:
            try:
                self.camera.release()
            except Exception:
                pass
        self.camera = None
        self.camera_surface = None

    def toggle_torch(self) -> None:
        """Try to toggle camera torch/flash.

        Important:
        - Built-in MacBook cameras do not have a flash.
        - Some phone-as-webcam apps expose torch control, many do not.
        - OpenCV support depends on the camera driver/app.
        """
        if self.camera is None or cv2 is None:
            return

        self.torch_enabled = not self.torch_enabled
        value = 1 if self.torch_enabled else 0

        ok = False
        for prop_name in ("CAP_PROP_TORCH", "CAP_PROP_FLASH"):
            prop = getattr(cv2, prop_name, None)
            if prop is None:
                continue
            try:
                ok = bool(self.camera.set(prop, value)) or ok
            except Exception:
                pass

        self.torch_supported = ok
        if ok:
            self.message = "Torch/flash toggled. Hold the barcode steady."
            self.message_color = GREEN
        else:
            self.message = "Torch control is not exposed by this camera/app. Use a lamp or phone torch."
            self.message_color = ORANGE
            play_sound("wrong")

    def update(self) -> None:
        if self.mode == "camera":
            self.update_camera()

    def update_camera(self) -> None:
        if self.camera is None or cv2 is None or barcode_decode is None:
            return

        ok, frame = self.camera.read()
        if not ok:
            self.message = "Camera frame not available."
            self.message_color = RED
            return

        self.scan_attempts += 1

        # Crop the middle of the frame for decoding.
        # This helps because the barcode usually fills the centre of the view.
        h, w = frame.shape[:2]
        crop_x1 = int(w * 0.08)
        crop_x2 = int(w * 0.92)
        crop_y1 = int(h * 0.22)
        crop_y2 = int(h * 0.78)
        crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]

        # Try several versions of the frame. Barcodes often decode better in grayscale
        # or with extra contrast.
        frames_to_try = [crop, frame]

        try:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            frames_to_try.append(gray)

            # Sharpen slightly
            sharpen_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            sharp = cv2.filter2D(gray, -1, sharpen_kernel)
            frames_to_try.append(sharp)

            # Adaptive threshold helps with poor lighting / glossy packets.
            thresh = cv2.adaptiveThreshold(
                gray,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                31,
                5,
            )
            frames_to_try.append(thresh)
        except Exception:
            pass

        decoded_items = []
        for candidate in frames_to_try:
            try:
                decoded_items = barcode_decode(candidate)
                if decoded_items:
                    break
            except Exception:
                continue

        now = time.time()

        for decoded in decoded_items:
            barcode = decoded.data.decode("utf-8", errors="ignore").strip()
            if not barcode:
                continue

            # Avoid adding the same barcode many times.
            if barcode == self.last_scanned and now - self.last_scan_time < 2.0:
                continue

            self.last_scanned = barcode
            self.last_scan_time = now

            self.close_camera()
            self.handle_barcode(barcode)
            return

        if self.scan_attempts % 120 == 0:
            self.message = "Still looking... try more light, hold steady, and fill the green box."
            self.message_color = ORANGE

        # Convert camera frame into a pygame surface for display.
        try:
            display_frame = frame.copy()
            # Draw crop guide on display frame before resizing.
            cv2.rectangle(display_frame, (crop_x1, crop_y1), (crop_x2, crop_y2), (0, 255, 0), 4)
            display_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            display_frame = cv2.resize(display_frame, (600, 360))
            display_frame = display_frame.swapaxes(0, 1)
            self.camera_surface = pygame.surfarray.make_surface(display_frame)
        except Exception:
            self.camera_surface = None

    # -----------------------------
    # Drawing
    # -----------------------------

    def draw(self) -> None:
        self.draw_background()
        self.draw_header()
        self.draw_till_body()
        self.draw_basket()
        self.draw_total_panel()
        self.draw_buttons()
        self.draw_message()

        if self.mode in {"manual_barcode", "new_name", "new_price"}:
            self.draw_input_overlay()
        elif self.mode == "camera":
            self.draw_camera_overlay()

    def draw_background(self) -> None:
        self.screen.fill(LIGHT_CYAN)

        # Colourful dots
        for x in range(20, WIDTH, 80):
            for y in range(20, HEIGHT, 80):
                pygame.draw.circle(self.screen, (230, 245, 255), (x, y), 12)

    def draw_header(self) -> None:
        rounded_rect(self.screen, pygame.Rect(30, 20, 1140, 90), WHITE, 24, 4, DARK)
        draw_text(self.screen, "Kids Checkout Till", (55, 38), FONT_TITLE, BLUE)
        draw_text(
            self.screen,
            "Scan items, learn prices, count the total, and play shop.",
            (58, 82),
            FONT_SMALL,
            DARK,
        )

        # Tiny shop icon
        pygame.draw.rect(self.screen, RED, pygame.Rect(960, 48, 130, 35), border_radius=8)
        pygame.draw.polygon(self.screen, ORANGE, [(945, 48), (1105, 48), (1088, 25), (962, 25)])
        pygame.draw.rect(self.screen, LIGHT_YELLOW, pygame.Rect(985, 58, 28, 25))
        pygame.draw.rect(self.screen, LIGHT_GREEN, pygame.Rect(1035, 58, 28, 25))
        draw_text(self.screen, "SHOP", (985, 29), FONT_SMALL, WHITE)

    def draw_till_body(self) -> None:
        # Left till screen
        rounded_rect(self.screen, pygame.Rect(30, 130, 690, 510), LIGHT_BLUE, 26, 4, DARK)
        rounded_rect(self.screen, pygame.Rect(60, 160, 630, 420), WHITE, 18, 3, DARK)

        # Receipt printer top detail
        rounded_rect(self.screen, pygame.Rect(760, 130, 390, 510), LIGHT_PURPLE, 26, 4, DARK)
        rounded_rect(self.screen, pygame.Rect(800, 165, 310, 420), WHITE, 12, 3, DARK)
        pygame.draw.rect(self.screen, GREY, pygame.Rect(830, 145, 250, 22), border_radius=8)
        draw_text(self.screen, "Receipt", (905, 190), FONT_MED, DARK)

    def draw_basket(self) -> None:
        draw_text(self.screen, "Basket", (85, 180), FONT_BIG, DARK)

        basket_clip = pygame.Rect(85, 225, 585, 315)
        self.clamp_basket_scroll()

        if not self.basket:
            draw_text(self.screen, "No items yet. Scan something!", (95, 235), FONT_MED, MID_GREY)
            return

        row_height = 26
        y = basket_clip.y
        visible_items = self.basket[self.basket_scroll:self.basket_scroll + self.basket_visible_rows]

        old_clip = self.screen.get_clip()
        self.screen.set_clip(basket_clip)

        for offset, item in enumerate(visible_items):
            idx = self.basket_scroll + offset + 1
            row = pygame.Rect(90, y, 560, 23)
            row_color = LIGHT_GREEN if idx % 2 else LIGHT_YELLOW
            pygame.draw.rect(self.screen, row_color, row, border_radius=6)

            price = format_money(item.price)
            price_width = FONT_SMALL.size(price)[0]
            name_max_width = 455 - price_width
            name = fit_text(item.name, FONT_SMALL, name_max_width)

            draw_text(self.screen, f"{idx:02d}. {name}", (100, y + 3), FONT_TINY, DARK)
            draw_text(self.screen, price, (650 - price_width, y + 3), FONT_TINY, DARK)

            y += row_height

        self.screen.set_clip(old_clip)

        # Scroll bar
        if len(self.basket) > self.basket_visible_rows:
            track = pygame.Rect(665, 225, 12, 315)
            rounded_rect(self.screen, track, GREY, 6, 1, MID_GREY)

            max_scroll = max(1, len(self.basket) - self.basket_visible_rows)
            thumb_height = max(35, int(track.height * (self.basket_visible_rows / len(self.basket))))
            thumb_range = track.height - thumb_height
            thumb_y = track.y + int((self.basket_scroll / max_scroll) * thumb_range)

            thumb = pygame.Rect(track.x + 1, thumb_y, track.width - 2, thumb_height)
            rounded_rect(self.screen, thumb, BLUE, 6)

            draw_text(
                self.screen,
                f"{self.basket_scroll + 1}-{self.basket_scroll + len(visible_items)} of {len(self.basket)}",
                (95, 548),
                FONT_TINY,
                MID_GREY,
            )
            draw_text(self.screen, "Mouse wheel or ↑ ↓ to scroll", (420, 548), FONT_TINY, MID_GREY)

    def draw_total_panel(self) -> None:
        total = self.total()

        # Big total display
        rounded_rect(self.screen, pygame.Rect(80, 590, 610, 40), DARK, 12)
        draw_text(self.screen, "TOTAL", (105, 598), FONT_MED, WHITE)
        total_img = FONT_BIG.render(format_money(total), True, YELLOW)
        self.screen.blit(total_img, total_img.get_rect(midright=(660, 610)))

        # Receipt style list, clipped so text never spills outside the paper.
        receipt_clip = pygame.Rect(820, 225, 270, 300)
        y = receipt_clip.y
        receipt_items = self.basket[-12:]

        if not receipt_items:
            draw_text_clipped(
                self.screen,
                "Your receipt will appear here.",
                (830, y),
                FONT_SMALL,
                MID_GREY,
                receipt_clip,
            )
        else:
            for item in receipt_items:
                price = format_money(item.price)
                name = fit_text(item.name, FONT_RECEIPT, 150)
                line = f"{name:<16} {price:>7}"
                draw_text_clipped(self.screen, line, (830, y), FONT_RECEIPT, DARK, receipt_clip)
                y += 26

        if len(self.basket) > 12:
            extra = f"... {len(self.basket) - 12} more"
            draw_text_clipped(self.screen, extra, (830, y), FONT_TINY, MID_GREY, receipt_clip)

        pygame.draw.line(self.screen, DARK, (830, 535), (1080, 535), 2)
        total_line = fit_text(f"TOTAL {format_money(total)}", FONT_RECEIPT, 240)
        draw_text_clipped(self.screen, total_line, (830, 550), FONT_RECEIPT, DARK, pygame.Rect(820, 540, 270, 35))

    def draw_buttons(self) -> None:
        self.scan_button.draw(self.screen)
        self.type_button.draw(self.screen)
        self.remove_button.draw(self.screen)

        if self.confirm_clear_basket:
            original_text = self.clear_button.text
            original_color = self.clear_button.color
            self.clear_button.text = "Confirm clear"
            self.clear_button.color = RED
            self.clear_button.draw(self.screen)
            self.clear_button.text = original_text
            self.clear_button.color = original_color
        else:
            self.clear_button.draw(self.screen)

        self.done_button.draw(self.screen)

        draw_text(self.screen, "Keys: S = scan, T = type, Backspace = remove last, C = clear/confirm, Tab = copy suggestion, ↑ ↓ = scroll", (55, 735), FONT_TINY, DARK)

    def draw_message(self) -> None:
        # Proper till display / status window. Keeps checkout text aligned and inside a panel.
        status_rect = pygame.Rect(735, 585, 430, 70)
        rounded_rect(self.screen, status_rect, WHITE, 14, 3, DARK)
        draw_text(self.screen, "Till message", (755, 594), FONT_TINY, MID_GREY)
        draw_text(self.screen, self.message, (755, 614), FONT_TINY, self.message_color, 390)

        beep_rect = pygame.Rect(1035, 665, 130, 55)
        rounded_rect(self.screen, beep_rect, YELLOW, 14, 2, DARK)
        draw_text(self.screen, "BEEP!", (1070, 681), FONT_MED, DARK)

    def draw_input_overlay(self) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 90))
        self.screen.blit(overlay, (0, 0))

        box = pygame.Rect(210, 130, 780, 485)
        rounded_rect(self.screen, box, WHITE, 24, 4, DARK)

        if self.mode == "manual_barcode":
            title = "Type barcode"
            prompt = "Type the number from the barcode, then press Enter."
            detail = ""
            input_label = "Barcode number"
        elif self.mode == "new_name":
            title = "Item name"
            prompt = "Type the item name. If a suggested name is shown, copy it by typing or press Tab."
            detail = f"Barcode: {self.pending_barcode}"
            input_label = "Type item name"
        else:
            title = "Item price"
            prompt = "I have suggested a rough price. Press Enter to accept it or type a new price."
            detail = fit_text(self.pending_name, FONT_MED, 650)
            input_label = "Price"

        draw_text(self.screen, title, (265, 170), FONT_BIG, BLUE)
        draw_text(self.screen, prompt, (265, 220), FONT_SMALL, DARK, 670)

        y = 260
        if detail:
            rounded_rect(self.screen, pygame.Rect(265, y, 670, 44), LIGHT_BLUE, 12, 2, BLUE)
            draw_text(self.screen, detail, (285, y + 11), FONT_SMALL, DARK, 630)
            y += 58

        if self.mode == "new_name" and self.suggested_name:
            rounded_rect(self.screen, pygame.Rect(265, y, 670, 64), LIGHT_PURPLE, 12, 2, PURPLE)
            draw_text(self.screen, "Copy this item name for typing practice:", (285, y + 8), FONT_TINY, DARK)
            draw_text(self.screen, fit_text(self.suggested_name, FONT_SMALL, 620), (285, y + 32), FONT_SMALL, DARK)
            y += 78

        if self.lookup_status:
            rounded_rect(self.screen, pygame.Rect(265, y, 670, 52), LIGHT_GREEN, 12, 2, GREEN)
            draw_text(self.screen, self.lookup_status, (285, y + 13), FONT_TINY, DARK, 630)
            y += 66

        draw_text(self.screen, input_label, (265, y), FONT_TINY, MID_GREY)
        input_rect = pygame.Rect(265, y + 20, 670, 58)
        rounded_rect(self.screen, input_rect, LIGHT_YELLOW, 12, 3, DARK)
        draw_text(self.screen, self.input_text, (282, y + 36), FONT_MED, DARK)

        draw_text(self.screen, "Enter = save    Tab = copy suggestion    ESC = cancel", (265, 575), FONT_SMALL, MID_GREY)

    def draw_camera_overlay(self) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        self.screen.blit(overlay, (0, 0))

        box = pygame.Rect(220, 80, 760, 610)
        rounded_rect(self.screen, box, WHITE, 24, 4, DARK)

        draw_text(self.screen, "Camera barcode scanner", (275, 115), FONT_BIG, GREEN)
        draw_text(
            self.screen,
            "Hold the barcode flat, steady and inside the green box. Press ESC to cancel or F for torch.",
            (275, 160),
            FONT_SMALL,
            DARK,
            660,
        )

        camera_rect = pygame.Rect(300, 220, 600, 360)
        rounded_rect(self.screen, camera_rect, LIGHT_BLUE, 12, 3, DARK)

        if self.camera_surface:
            self.screen.blit(self.camera_surface, camera_rect.topleft)
            pygame.draw.rect(self.screen, GREEN, camera_rect, width=4, border_radius=12)
            # scan line
            scan_y = camera_rect.y + int((time.time() * 140) % camera_rect.height)
            pygame.draw.line(self.screen, RED, (camera_rect.x + 20, scan_y), (camera_rect.right - 20, scan_y), 3)
        else:
            draw_text(self.screen, "Starting camera...", (500, 390), FONT_MED, DARK)

        self.torch_button.draw(self.screen)
        torch_text = "Torch: on" if self.torch_enabled else "Torch: off"
        draw_text(self.screen, torch_text, (710, 596), FONT_SMALL, DARK)

        draw_text(
            self.screen,
            "Tip: MacBook cameras have no flash. Phone-as-webcam torch support depends on the app. A lamp or the phone torch may work better.",
            (275, 645),
            FONT_TINY,
            MID_GREY,
            660,
        )


if __name__ == "__main__":
    CheckoutGame().run()
