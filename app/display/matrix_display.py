from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

from app.models import ConnectorItem

LOGGER = logging.getLogger(__name__)

CONNECTOR_COLORS: dict[str, tuple[int, int, int]] = {
    "weather_openmeteo": (60, 185, 255),
    "stocks_finnhub": (76, 220, 110),
    "news_newsapi": (255, 210, 90),
    "homeassistant_entities": (255, 135, 75),
    "garmin_connect": (255, 90, 90),
    "generic": (200, 200, 200),
}

CONNECTOR_ICONS: dict[str, tuple[tuple[int, int], ...]] = {
    # Sun
    "weather_openmeteo": (
        (3, 1),
        (1, 3),
        (3, 3),
        (5, 3),
        (3, 5),
        (2, 2),
        (4, 2),
        (2, 4),
        (4, 4),
    ),
    # Up chart
    "stocks_finnhub": (
        (1, 6),
        (2, 5),
        (3, 4),
        (4, 3),
        (5, 2),
        (5, 3),
        (6, 2),
        (6, 1),
    ),
    # Newspaper
    "news_newsapi": (
        (1, 1),
        (2, 1),
        (3, 1),
        (4, 1),
        (5, 1),
        (1, 2),
        (5, 2),
        (1, 3),
        (5, 3),
        (1, 4),
        (2, 4),
        (3, 4),
        (4, 4),
        (5, 4),
        (1, 5),
        (5, 5),
    ),
    # House
    "homeassistant_entities": (
        (1, 4),
        (2, 3),
        (3, 2),
        (4, 3),
        (5, 4),
        (1, 5),
        (2, 5),
        (3, 5),
        (4, 5),
        (5, 5),
        (3, 4),
    ),
    # Shoe
    "garmin_connect": (
        (1, 5),
        (2, 5),
        (3, 5),
        (4, 5),
        (5, 5),
        (3, 4),
        (4, 4),
        (5, 4),
        (6, 4),
    ),
    # Dot
    "generic": ((3, 3),),
}


@dataclass
class DisplayConfig:
    width: int = 64
    height: int = 32
    brightness: int = 60
    no_hardware_pulse: bool = False


class MatrixDisplay:
    def __init__(self, config: DisplayConfig):
        self.config = config
        self._mode = "console"
        self._matrix = None
        self._font = ImageFont.load_default()
        self._scroll_key = ""
        self._scroll_offset = 0
        self._scroll_last_tick = 0.0
        self._scroll_pause_until = 0.0
        self._scroll_step_seconds = 0.09
        self._scroll_pause_seconds = 0.8
        self._scroll_gap_px = 10

        try:
            from rgbmatrix import RGBMatrix, RGBMatrixOptions  # type: ignore

            options = RGBMatrixOptions()
            options.rows = config.height
            options.cols = config.width
            options.chain_length = 1
            options.parallel = 1
            options.hardware_mapping = "regular"
            options.brightness = max(1, min(100, config.brightness))
            if config.no_hardware_pulse and hasattr(options, "disable_hardware_pulsing"):
                # Equivalent to --led-no-hardware-pulse for non-root execution.
                options.disable_hardware_pulsing = True

            self._matrix = RGBMatrix(options=options)
            self._mode = "hardware"
            LOGGER.info("Matrix display initialized in hardware mode")
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("Fallback to console mode (no hardware matrix): %s", exc)

    @property
    def mode(self) -> str:
        return self._mode

    def show_lines(self, lines: list[str]) -> None:
        if self._mode == "hardware" and self._matrix is not None:
            self._show_hardware(lines)
            return
        self._show_console(lines)

    def show_item(self, item: ConnectorItem) -> None:
        if self._mode == "hardware" and self._matrix is not None:
            self._show_item_hardware(item)
            return
        self._show_console(
            [
                item.title.strip()[:16],
                item.body.strip().replace("\n", " ")[:32],
                f"{item.connector_name[:8]} {item.updated_at.strftime('%H:%M')}",
            ]
        )

    def _show_hardware(self, lines: list[str]) -> None:
        image = Image.new("RGB", (self.config.width, self.config.height), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)

        y = 0
        for line in lines[:3]:
            draw.text((1, y), line[:24], font=self._font, fill=(255, 180, 20))
            y += 10

        self._matrix.SetImage(image, 0, 0)

    def _show_item_hardware(self, item: ConnectorItem) -> None:
        image = Image.new("RGB", (self.config.width, self.config.height), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)

        connector_type = item.connector_type or "generic"
        accent = CONNECTOR_COLORS.get(connector_type, CONNECTOR_COLORS["generic"])

        self._draw_icon(draw, connector_type, accent)

        title = self._truncate_text(item.title.strip(), 10)
        draw.text((10, 0), title, font=self._font, fill=accent)

        body = item.body.strip().replace("\n", " ")
        body_x = 1
        body_y = 11
        max_body_width = self.config.width - 2
        self._draw_scrolling_text(draw, body, body_x, body_y, max_body_width)

        footer = self._truncate_text(f"{item.updated_at.strftime('%H:%M')} {item.connector_name}", 13)
        draw.text((1, 22), footer, font=self._font, fill=(170, 170, 170))

        self._matrix.SetImage(image, 0, 0)

    def _draw_icon(
        self,
        draw: ImageDraw.ImageDraw,
        connector_type: str,
        color: tuple[int, int, int],
    ) -> None:
        for px, py in CONNECTOR_ICONS.get(connector_type, CONNECTOR_ICONS["generic"]):
            draw.point((px, py), fill=color)

    def _draw_scrolling_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: int,
        y: int,
        max_width: int,
    ) -> None:
        text_width = self._text_width(draw, text)
        if text_width <= max_width:
            draw.text((x, y), text, font=self._font, fill=(255, 210, 120))
            self._reset_scroll()
            return

        key = text
        now = time.time()
        if key != self._scroll_key:
            self._scroll_key = key
            self._scroll_offset = 0
            self._scroll_last_tick = now
            self._scroll_pause_until = now + self._scroll_pause_seconds

        if now >= self._scroll_pause_until and (now - self._scroll_last_tick) >= self._scroll_step_seconds:
            self._scroll_last_tick = now
            self._scroll_offset += 1

            cycle_width = text_width + self._scroll_gap_px
            if self._scroll_offset >= cycle_width:
                self._scroll_offset = 0
                self._scroll_pause_until = now + self._scroll_pause_seconds

        offset_x = x - self._scroll_offset
        draw.text((offset_x, y), text, font=self._font, fill=(255, 210, 120))
        draw.text((offset_x + text_width + self._scroll_gap_px, y), text, font=self._font, fill=(255, 210, 120))

    def _text_width(self, draw: ImageDraw.ImageDraw, text: str) -> int:
        left, _, right, _ = draw.textbbox((0, 0), text, font=self._font)
        return right - left

    def _truncate_text(self, text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        if max_chars <= 1:
            return text[:max_chars]
        return f"{text[: max_chars - 1]}."

    def _reset_scroll(self) -> None:
        self._scroll_key = ""
        self._scroll_offset = 0
        self._scroll_last_tick = 0.0
        self._scroll_pause_until = 0.0

    def _show_console(self, lines: list[str]) -> None:
        print("\n" + "=" * 30)
        for line in lines:
            print(line)
        print("=" * 30)
