from __future__ import annotations

import logging
import time
import unicodedata
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

from app.models import ConnectorItem

LOGGER = logging.getLogger(__name__)

CONNECTOR_COLORS: dict[str, tuple[int, int, int]] = {
    "weather_openmeteo": (60, 185, 255),
    "stocks_finnhub": (76, 220, 110),
    "news_newsapi": (255, 210, 90),
    "homeassistant_entities": (255, 135, 75),
    "generic": (200, 200, 200),
}

CONNECTOR_ICONS: dict[str, tuple[str, ...]] = {
    "weather_openmeteo": (
        "001100",
        "011110",
        "111111",
        "111111",
        "011110",
        "001100",
    ),
    "stocks_finnhub": (
        "000001",
        "000011",
        "001101",
        "011001",
        "110001",
        "100000",
    ),
    "news_newsapi": (
        "111111",
        "100001",
        "111101",
        "101101",
        "111101",
        "100001",
    ),
    "homeassistant_entities": (
        "001100",
        "011110",
        "111111",
        "110011",
        "110011",
        "111111",
    ),
    "generic": (
        "000000",
        "001100",
        "001100",
        "000000",
        "001100",
        "001100",
    ),
}

MDI_ICON_ALIASES: dict[str, tuple[str, ...]] = {
    "mdi-account-circle": (
        "011110",
        "100001",
        "101101",
        "100001",
        "100001",
        "011110",
    ),
    "mdi-home": (
        "001100",
        "011110",
        "111111",
        "110011",
        "110011",
        "111111",
    ),
    "mdi-weather-partly-cloudy": (
        "001100",
        "011110",
        "111111",
        "111111",
        "011110",
        "001100",
    ),
    "mdi-newspaper": (
        "111111",
        "100001",
        "111101",
        "101101",
        "111101",
        "100001",
    ),
    "mdi-chart-line": (
        "000001",
        "000011",
        "001101",
        "011001",
        "110001",
        "100000",
    ),
    "mdi-lightbulb": (
        "011110",
        "011110",
        "011110",
        "001100",
        "001100",
        "001100",
    ),
    "mdi-lightbulb-outline": (
        "011110",
        "010010",
        "011110",
        "001100",
        "001100",
        "001100",
    ),
    "mdi-thermometer": (
        "001000",
        "001000",
        "001000",
        "001000",
        "011100",
        "011100",
    ),
    "mdi-currency-eur": (
        "011110",
        "110000",
        "111100",
        "110000",
        "111100",
        "011110",
    ),
}

PIXEL_FONT_3X5: dict[str, tuple[str, ...]] = {
    " ": ("000", "000", "000", "000", "000"),
    ".": ("000", "000", "000", "000", "010"),
    "'": ("010", "010", "000", "000", "000"),
    ",": ("000", "000", "000", "010", "100"),
    ":": ("000", "010", "000", "010", "000"),
    "%": ("101", "001", "010", "100", "101"),
    "/": ("001", "001", "010", "100", "100"),
    "-": ("000", "000", "111", "000", "000"),
    "+": ("000", "010", "111", "010", "000"),
    "?": ("111", "001", "010", "000", "010"),
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "001", "001", "001"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
    "A": ("111", "101", "111", "101", "101"),
    "B": ("110", "101", "110", "101", "110"),
    "C": ("111", "100", "100", "100", "111"),
    "D": ("110", "101", "101", "101", "110"),
    "E": ("111", "100", "110", "100", "111"),
    "F": ("111", "100", "110", "100", "100"),
    "G": ("111", "100", "101", "101", "111"),
    "H": ("101", "101", "111", "101", "101"),
    "I": ("111", "010", "010", "010", "111"),
    "J": ("001", "001", "001", "101", "111"),
    "K": ("101", "101", "110", "101", "101"),
    "L": ("100", "100", "100", "100", "111"),
    "M": ("101", "111", "111", "101", "101"),
    "N": ("101", "111", "111", "111", "101"),
    "O": ("111", "101", "101", "101", "111"),
    "P": ("111", "101", "111", "100", "100"),
    "Q": ("111", "101", "101", "111", "001"),
    "R": ("110", "101", "110", "101", "101"),
    "S": ("111", "100", "111", "001", "111"),
    "T": ("111", "010", "010", "010", "010"),
    "U": ("101", "101", "101", "101", "111"),
    "V": ("101", "101", "101", "101", "010"),
    "W": ("101", "101", "111", "111", "101"),
    "X": ("101", "101", "010", "101", "101"),
    "Y": ("101", "101", "010", "010", "010"),
    "Z": ("111", "001", "010", "100", "111"),
}


@dataclass
class DisplayConfig:
    width: int = 64
    height: int = 32
    brightness: int = 60
    no_hardware_pulse: bool = False
    scroll_step_seconds: float = 0.09
    main_font_height_px: int = 16
    main_font_style: str = "regular"


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
        self._scroll_step_seconds = max(0.01, float(config.scroll_step_seconds))
        self._scroll_pause_seconds = 0.8
        self._scroll_gap_px = 8

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

        title_height = 12
        content_height = max(8, self.config.height - title_height)
        requested_text_height = int(self.config.main_font_height_px)
        max_text_height = max(5, content_height)
        content_text_height_px = max(5, min(requested_text_height, max_text_height))
        font_style = self._normalize_font_style(self.config.main_font_style)
        content_scale_x, content_spacing, content_bold = self._font_style_params(font_style)
        content_row_heights = self._build_row_heights(content_text_height_px)

        icon_size = 8
        icon_top = max(0, (title_height - icon_size) // 2)
        self._draw_icon(
            draw,
            connector_type,
            accent,
            item.icon_mdi,
            top_y=icon_top,
            size=icon_size,
        )

        title = self._normalize_text(item.title.strip())
        title = self._truncate_text(title, 11)
        title_scale = 1
        title_y = max(0, (title_height - (5 * title_scale)) // 2)
        self._draw_pixel_text(draw, title, x=11, y=title_y, scale=title_scale, color=accent)

        body = item.body.strip().replace("\n", " ")
        body = self._normalize_text(body)
        body_x = 1
        text_height = sum(content_row_heights)
        content_top = title_height
        body_y = content_top + max(0, (content_height - text_height) // 2)
        max_body_width = self.config.width - 2
        self._draw_scrolling_text(
            draw,
            body,
            body_x,
            body_y,
            max_body_width,
            content_scale_x,
            content_spacing,
            content_bold,
            content_row_heights,
        )

        self._matrix.SetImage(image, 0, 0)

    def _draw_icon(
        self,
        draw: ImageDraw.ImageDraw,
        connector_type: str,
        color: tuple[int, int, int],
        icon_mdi: str | None,
        top_y: int,
        size: int,
    ) -> None:
        # Contrast frame makes icons readable on low-pitch HUB75 panels.
        right = size - 1
        bottom = top_y + size - 1
        draw.rectangle((0, top_y, right, bottom), fill=(12, 12, 12), outline=color)
        icon = self._resolve_icon_bitmap(connector_type, icon_mdi)
        for y, row in enumerate(icon):
            for x, bit in enumerate(row):
                if bit == "1":
                    draw.point((x + 1, top_y + y + 1), fill=(255, 255, 255))

    def _draw_scrolling_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: int,
        y: int,
        max_width: int,
        scale_x: int,
        spacing: int,
        bold: bool,
        row_heights: list[int],
    ) -> None:
        text_width = self._text_width(draw, text, scale_x, spacing, bold)
        if text_width <= max_width:
            centered_x = x + max(0, (max_width - text_width) // 2)
            self._draw_pixel_text(
                draw,
                text,
                x=centered_x,
                y=y,
                scale=scale_x,
                color=(255, 210, 120),
                spacing=spacing,
                bold=bold,
                row_heights=row_heights,
            )
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
        self._draw_pixel_text(
            draw,
            text,
            x=offset_x,
            y=y,
            scale=scale_x,
            color=(255, 210, 120),
            spacing=spacing,
            bold=bold,
            row_heights=row_heights,
        )
        self._draw_pixel_text(
            draw,
            text,
            x=offset_x + text_width + self._scroll_gap_px,
            y=y,
            scale=scale_x,
            color=(255, 210, 120),
            spacing=spacing,
            bold=bold,
            row_heights=row_heights,
        )

    def _text_width(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        scale: int,
        spacing: int,
        bold: bool,
    ) -> int:
        del draw
        normalized = self._normalize_text(text)
        return self._pixel_text_width(normalized, scale=scale, spacing=spacing, bold=bold)

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

    def _normalize_text(self, text: str) -> str:
        replacements = {
            "œ": "oe",
            "Œ": "OE",
            "æ": "ae",
            "Æ": "AE",
            "ç": "c",
            "Ç": "C",
            "’": "'",
            "`": "'",
            "´": "'",
        }
        for source, target in replacements.items():
            text = text.replace(source, target)

        normalized = unicodedata.normalize("NFKD", text)
        ascii_only = normalized.encode("ascii", "ignore").decode("ascii")
        upper = ascii_only.upper()

        filtered_chars: list[str] = []
        for char in upper:
            if char in PIXEL_FONT_3X5:
                filtered_chars.append(char)
            elif char.isalnum():
                filtered_chars.append("?")
            else:
                filtered_chars.append(" ")
        return "".join(filtered_chars)

    def _pixel_text_width(self, text: str, scale: int, spacing: int, bold: bool) -> int:
        if not text:
            return 0
        glyph_width = (3 * scale) + (1 if bold else 0)
        return (len(text) * glyph_width) + ((len(text) - 1) * max(0, spacing))

    def _normalize_font_style(self, style: str | None) -> str:
        raw = (style or "regular").strip().lower().replace("_", "-")
        aliases = {
            "classic": "regular",
            "normal": "regular",
            "condensed": "compact",
            "large": "wide",
            "expanded": "wide",
            "strong": "bold",
            "readable": "spaced",
        }
        normalized = aliases.get(raw, raw)
        if normalized in {"compact", "regular", "wide", "bold", "spaced"}:
            return normalized
        return "regular"

    def _font_style_params(self, style: str) -> tuple[int, int, bool]:
        presets: dict[str, tuple[int, int, bool]] = {
            "compact": (2, 1, False),
            "regular": (3, 1, False),
            "wide": (4, 1, False),
            "bold": (3, 1, True),
            "spaced": (3, 2, False),
        }
        return presets.get(style, presets["regular"])

    def _resolve_icon_bitmap(self, connector_type: str, icon_mdi: str | None) -> tuple[str, ...]:
        if icon_mdi:
            mdi_key = self._normalize_mdi_name(icon_mdi)
            if mdi_key in MDI_ICON_ALIASES:
                return MDI_ICON_ALIASES[mdi_key]

            # Keyword fallback when exact icon isn't in local alias table.
            if any(token in mdi_key for token in ("account", "person", "user")):
                return MDI_ICON_ALIASES["mdi-account-circle"]
            if any(token in mdi_key for token in ("home", "house")):
                return MDI_ICON_ALIASES["mdi-home"]
            if any(token in mdi_key for token in ("weather", "sun", "cloud")):
                return MDI_ICON_ALIASES["mdi-weather-partly-cloudy"]
            if any(token in mdi_key for token in ("chart", "stock", "finance", "trend")):
                return MDI_ICON_ALIASES["mdi-chart-line"]
            if any(token in mdi_key for token in ("news", "newspaper")):
                return MDI_ICON_ALIASES["mdi-newspaper"]
            if any(token in mdi_key for token in ("light", "lamp", "bulb")):
                return MDI_ICON_ALIASES["mdi-lightbulb"]
            if any(token in mdi_key for token in ("thermo", "temp", "temperature")):
                return MDI_ICON_ALIASES["mdi-thermometer"]
            if any(token in mdi_key for token in ("currency", "euro", "eur", "money", "cash")):
                return MDI_ICON_ALIASES["mdi-currency-eur"]

        return CONNECTOR_ICONS.get(connector_type, CONNECTOR_ICONS["generic"])

    def _normalize_mdi_name(self, name: str) -> str:
        raw = name.strip()
        if not raw:
            return ""
        if raw.startswith("mdi") and not raw.startswith("mdi-"):
            raw = "mdi-" + raw[3:]

        normalized_chars: list[str] = []
        for index, char in enumerate(raw):
            if char.isupper() and index > 0 and raw[index - 1] != "-":
                normalized_chars.append("-")
            if char == "_":
                normalized_chars.append("-")
            else:
                normalized_chars.append(char.lower())
        return "".join(normalized_chars)

    def _draw_pixel_text(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: int,
        y: int,
        scale: int,
        color: tuple[int, int, int],
        spacing: int = 1,
        bold: bool = False,
        row_heights: list[int] | None = None,
    ) -> None:
        cursor_x = x
        heights = row_heights if row_heights and len(row_heights) == 5 else [scale] * 5
        for char in text:
            glyph = PIXEL_FONT_3X5.get(char, PIXEL_FONT_3X5["?"])
            y_cursor = y
            for gy, row in enumerate(glyph):
                row_height = heights[gy]
                for gx, bit in enumerate(row):
                    if bit != "1":
                        continue
                    px = cursor_x + gx * scale
                    py = y_cursor
                    draw.rectangle(
                        (px, py, px + scale - 1, py + row_height - 1),
                        fill=color,
                    )
                    if bold:
                        draw.rectangle(
                            (px + 1, py, px + scale, py + row_height - 1),
                            fill=color,
                        )
                y_cursor += row_height
            cursor_x += (3 * scale) + (1 if bold else 0) + max(0, spacing)

    def _build_row_heights(self, target_height: int) -> list[int]:
        target = max(5, target_height)
        base = target // 5
        remainder = target % 5
        heights = [base] * 5
        for index in range(remainder):
            heights[index] += 1
        return heights

    def _show_console(self, lines: list[str]) -> None:
        print("\n" + "=" * 30)
        for line in lines:
            print(line)
        print("=" * 30)
