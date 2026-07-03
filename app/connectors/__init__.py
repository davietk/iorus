from __future__ import annotations

from typing import Any

from app.connectors.base import BaseConnector
from app.connectors.garmin_connect import GarminConnectConnector
from app.connectors.homeassistant_entities import HomeAssistantEntitiesConnector
from app.connectors.news_newsapi import NewsApiConnector
from app.connectors.stocks_finnhub import FinnhubStocksConnector
from app.connectors.weather_openmeteo import OpenMeteoConnector


CONNECTOR_FACTORIES = {
    "weather_openmeteo": OpenMeteoConnector,
    "stocks_finnhub": FinnhubStocksConnector,
    "news_newsapi": NewsApiConnector,
    "homeassistant_entities": HomeAssistantEntitiesConnector,
    "garmin_connect": GarminConnectConnector,
}


def build_connectors(connector_configs: list[dict[str, Any]]) -> list[BaseConnector]:
    connectors: list[BaseConnector] = []

    for connector_cfg in connector_configs:
        if not connector_cfg.get("enabled", True):
            continue

        connector_type = connector_cfg.get("type")
        connector_class = CONNECTOR_FACTORIES.get(connector_type)
        if connector_class is None:
            continue

        connectors.append(connector_class(connector_cfg))

    return connectors
