from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import requests

from app.connectors.base import BaseConnector
from app.models import ConnectorItem


class HomeAssistantEntitiesConnector(BaseConnector):
    def fetch(self) -> list[ConnectorItem]:
        base_url = str(self.settings.get("base_url", "http://homeassistant.local:8123")).rstrip("/")
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
                    updated_at=datetime.utcnow(),
                )
            ]

        entities_cfg = self.settings.get("entities", [])
        if not entities_cfg:
            return [
                ConnectorItem(
                    connector_name=self.name,
                    title="Home Assistant",
                    body="Aucune entite configuree",
                    updated_at=datetime.utcnow(),
                )
            ]

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        response = requests.get(f"{base_url}/api/states", headers=headers, timeout=10)
        response.raise_for_status()

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
                        updated_at=datetime.utcnow(),
                    )
                )
                continue

            attrs = state_obj.get("attributes") or {}
            title = title_override or attrs.get("friendly_name") or entity_id
            effective_icon_mdi = icon_mdi or attrs.get("icon")

            if attribute:
                value = attrs.get(attribute, "N/A")
                body = f"{attribute}: {value}"
            else:
                value = state_obj.get("state", "unknown")
                unit = attrs.get("unit_of_measurement")
                body = f"{value} {unit}" if unit else str(value)

            items.append(
                ConnectorItem(
                    connector_name=self.name,
                    title=str(title),
                    body=str(body),
                    icon_mdi=str(effective_icon_mdi) if effective_icon_mdi else None,
                    updated_at=datetime.utcnow(),
                )
            )

        if items:
            return items

        return [
            ConnectorItem(
                connector_name=self.name,
                title="Home Assistant",
                body="Configuration entites vide",
                updated_at=datetime.utcnow(),
            )
        ]
