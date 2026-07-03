from __future__ import annotations

import argparse
import logging
import time
from datetime import datetime, timezone

from app.config import DEFAULT_CONFIG_PATH, load_config
from app.connectors import build_connectors
from app.display.matrix_display import DisplayConfig, MatrixDisplay
from app.ha.mqtt_bridge import MqttBridge
from app.models import ConnectorItem


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LED Matrix Dashboard")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to YAML config")
    return parser


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def run() -> None:
    _setup_logging()
    parser = _build_parser()
    args = parser.parse_args()

    config = load_config(args.config)

    display_cfg = config.get("display", {})
    rotation_seconds = int(display_cfg.get("rotation_seconds", 6))
    display = MatrixDisplay(
        DisplayConfig(
            width=int(display_cfg.get("width", 64)),
            height=int(display_cfg.get("height", 32)),
            brightness=int(display_cfg.get("brightness", 60)),
            no_hardware_pulse=bool(display_cfg.get("no_hardware_pulse", False)),
            scroll_step_seconds=float(display_cfg.get("scroll_step_seconds", 0.09)),
            main_font_height_px=int(display_cfg.get("main_font_height_px", 16)),
        )
    )

    mqtt_bridge = MqttBridge(config.get("mqtt", {}))

    connectors = build_connectors(config.get("connectors", []))
    logging.info("Connectors actifs: %s", [connector.name for connector in connectors])

    for connector in connectors:
        mqtt_bridge.publish_discovery_for_connector(connector.name)
    mqtt_bridge.publish_discovery_for_connector("status")

    app_poll_sleep_seconds = float(config.get("app", {}).get("poll_sleep_seconds", 1.0))
    frame_sleep_seconds = float(display_cfg.get("frame_sleep_seconds", 0.15))
    fallback_message = str(config.get("app", {}).get("fallback_message", "Aucune donnee"))

    next_fetch_at: dict[str, float] = {}
    latest_items: dict[str, list[ConnectorItem]] = {}
    display_cursor = 0
    last_rotation = 0.0

    for connector in connectors:
        next_fetch_at[connector.name] = 0.0

    try:
        while True:
            now = time.time()
            for connector in connectors:
                if now < next_fetch_at[connector.name]:
                    continue

                try:
                    items = connector.fetch()
                    for item in items:
                        if not item.connector_type or item.connector_type == "generic":
                            item.connector_type = connector.connector_type
                    latest_items[connector.name] = items
                    if items:
                        mqtt_bridge.publish_connector_state(connector.name, items[0].body[:255])
                    else:
                        mqtt_bridge.publish_connector_state(connector.name, "No data")
                except Exception as exc:
                    logging.exception("Erreur connecteur %s", connector.name)
                    latest_items[connector.name] = [
                        ConnectorItem(
                            connector_name=connector.name,
                            title="Erreur",
                            body=str(exc)[:80],
                            connector_type=connector.connector_type,
                            updated_at=datetime.now(timezone.utc),
                        )
                    ]
                    mqtt_bridge.publish_connector_state(connector.name, f"Erreur: {exc}")

                next_fetch_at[connector.name] = now + connector.interval_seconds

            playlist: list[ConnectorItem] = []
            for items in latest_items.values():
                playlist.extend(items)

            if not playlist:
                display.show_lines(["LED Matrix", fallback_message, "Attente donnees"])
                mqtt_bridge.publish_status("idle")
            else:
                mqtt_bridge.publish_status("running")
                if now - last_rotation >= rotation_seconds:
                    display_cursor = (display_cursor + 1) % len(playlist)
                    last_rotation = now
                else:
                    display_cursor = display_cursor % len(playlist)
                current_item = playlist[display_cursor]
                display.show_item(current_item)

            time.sleep(min(app_poll_sleep_seconds, frame_sleep_seconds))
    except KeyboardInterrupt:
        logging.info("Arret manuel")
    finally:
        mqtt_bridge.shutdown()


if __name__ == "__main__":
    run()
