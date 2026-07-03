from __future__ import annotations

import logging
import os
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from datetime import datetime, timezone
from typing import Any

import requests

from app.connectors.base import BaseConnector
from app.models import ConnectorItem


LOGGER = logging.getLogger(__name__)


class HomeAssistantEntitiesConnector(BaseConnector):
    def _resolve_numeric_decimals(self, entity_cfg: Any) -> int | None:
        connector_default = self.settings.get("numeric_decimals")
        entity_override = entity_cfg.get("numeric_decimals") if isinstance(entity_cfg, dict) else None
        raw = entity_override if entity_override is not None else connector_default
        if raw is None:
            return None
        try:
            return max(0, int(raw))
        except (TypeError, ValueError):
            return None

    def _format_numeric_value(self, value: Any, decimals: int | None) -> str:
        if decimals is None:
            return str(value)

        if isinstance(value, bool):
            return str(value)

        if isinstance(value, int):
            if decimals == 0:
                return str(value)
            return f"{value:.{decimals}f}"

        if isinstance(value, float):
            quant = Decimal("1") if decimals == 0 else Decimal("1").scaleb(-decimals)
            truncated = Decimal(str(value)).quantize(quant, rounding=ROUND_DOWN)
            return f"{truncated:.{decimals}f}" if decimals > 0 else f"{truncated:.0f}"

        if isinstance(value, str):
            text = value.strip()
            if not text:
                return text
            normalized = text.replace(",", ".")
            try:
                parsed = Decimal(normalized)
            except InvalidOperation:
                return str(value)

            quant = Decimal("1") if decimals == 0 else Decimal("1").scaleb(-decimals)
            truncated = parsed.quantize(quant, rounding=ROUND_DOWN)
            return f"{truncated:.{decimals}f}" if decimals > 0 else f"{truncated:.0f}"

        return str(value)

    def fetch(self) -> list[ConnectorItem]:
        base_url = str(self.settings.get("base_url", "http://homeassistant.local:8123")).rstrip("/")
        timeout_seconds = float(self.settings.get("timeout_seconds", 10))
        token = self.settings.get("token")
        token_env = self.settings.get("token_env")
        if not token and token_env:
            token = os.getenv(token_env)

        if not token:
            return [
                ConnectorItem(
                    connector_name=self.name,
                    title="Home Assistant",
                    body="Token Home Assistant manquant",
                    updated_at=datetime.now(timezone.utc),
                )
            ]

        entities_cfg = self.settings.get("entities", [])
        if not entities_cfg:
            return [
                ConnectorItem(
                    connector_name=self.name,
                    title="Home Assistant",
                    body="Aucune entite configuree",
                    updated_at=datetime.now(timezone.utc),
                )
            ]

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.get(f"{base_url}/api/states", headers=headers, timeout=timeout_seconds)
            response.raise_for_status()
        except requests.RequestException as exc:
            LOGGER.warning("Home Assistant indisponible (%s): %s", base_url, exc)
            return [
                ConnectorItem(
                    connector_name=self.name,
                    title="Home Assistant",
                    body="HA indisponible - reconnexion...",
                    icon_mdi="mdiHome",
                    updated_at=datetime.now(timezone.utc),
                )
            ]

        states = response.json()
        states_by_entity = {state.get("entity_id"): state for state in states}

        items: list[ConnectorItem] = []
        for entity_cfg in entities_cfg:
            if isinstance(entity_cfg, str):
                entity_id = entity_cfg
                title_override = None
                attribute = None
                icon_mdi = None
            else:
                entity_id = entity_cfg.get("entity_id")
                title_override = entity_cfg.get("title")
                attribute = entity_cfg.get("attribute")
                icon_mdi = entity_cfg.get("icon_mdi") or entity_cfg.get("icon")

            numeric_decimals = self._resolve_numeric_decimals(entity_cfg)

            if not entity_id:
                continue

            state_obj = states_by_entity.get(entity_id)
            if not state_obj:
                items.append(
                    ConnectorItem(
                        connector_name=self.name,
                        title=title_override or entity_id,
                        body="Entite introuvable",
                        icon_mdi=str(icon_mdi) if icon_mdi else None,
                        updated_at=datetime.now(timezone.utc),
                    )
                )
                continue

            attrs = state_obj.get("attributes") or {}
            title = title_override or attrs.get("friendly_name") or entity_id
            effective_icon_mdi = icon_mdi or attrs.get("icon")

            if attribute:
                value = attrs.get(attribute, "N/A")
                formatted_value = self._format_numeric_value(value, numeric_decimals)
                body = f"{attribute}: {formatted_value}"
            else:
                value = state_obj.get("state", "unknown")
                unit = attrs.get("unit_of_measurement")
                formatted_value = self._format_numeric_value(value, numeric_decimals)
                body = f"{formatted_value} {unit}" if unit else formatted_value

            items.append(
                ConnectorItem(
                    connector_name=self.name,
                    title=str(title),
                    body=str(body),
                    icon_mdi=str(effective_icon_mdi) if effective_icon_mdi else None,
                    updated_at=datetime.now(timezone.utc),
                )
            )

        if items:
            return items

        return [
            ConnectorItem(
                connector_name=self.name,
                title="Home Assistant",
                body="Configuration entites vide",
                updated_at=datetime.now(timezone.utc),
            )
        ]
