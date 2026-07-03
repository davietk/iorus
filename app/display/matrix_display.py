from __future__ import annotations

import logging
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont

LOGGER = logging.getLogger(__name__)


@dataclass
class DisplayConfig:
    width: int = 64
    height: int = 32
    brightness: int = 60


class MatrixDisplay:
    def __init__(self, config: DisplayConfig):
        self.config = config
        self._mode = "console"
        self._matrix = None
        self._font = ImageFont.load_default()

        try:
            from rgbmatrix import RGBMatrix, RGBMatrixOptions  # type: ignore

            options = RGBMatrixOptions()
            options.rows = config.height
            options.cols = config.width
            options.chain_length = 1
            options.parallel = 1
            options.hardware_mapping = "regular"
            options.brightness = max(1, min(100, config.brightness))

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

    def _show_hardware(self, lines: list[str]) -> None:
        image = Image.new("RGB", (self.config.width, self.config.height), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)

        y = 0
        for line in lines[:3]:
            draw.text((1, y), line[:24], font=self._font, fill=(255, 180, 20))
            y += 10

        self._matrix.SetImage(image, 0, 0)

    def _show_console(self, lines: list[str]) -> None:
        print("\n" + "=" * 30)
        for line in lines:
            print(line)
        print("=" * 30)
