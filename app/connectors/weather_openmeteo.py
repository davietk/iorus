from __future__ import annotations

from datetime import datetime

import requests

from app.connectors.base import BaseConnector
from app.models import ConnectorItem


WEATHER_CODE_LABELS = {
    0: "Degage",
    1: "Peu nuageux",
    2: "Nuageux",
    3: "Couvert",
    45: "Brouillard",
    48: "Brouillard",
    51: "Bruine",
    53: "Bruine",
    55: "Bruine",
    61: "Pluie faible",
    63: "Pluie",
    65: "Pluie forte",
    71: "Neige faible",
    73: "Neige",
    75: "Neige forte",
    80: "Averses",
    81: "Averses",
    82: "Averses fortes",
    95: "Orage",
}


class OpenMeteoConnector(BaseConnector):
    URL = "https://api.open-meteo.com/v1/forecast"

    def fetch(self) -> list[ConnectorItem]:
        latitude = self.settings.get("latitude")
        longitude = self.settings.get("longitude")
        timezone = self.settings.get("timezone", "Europe/Paris")

        if latitude is None or longitude is None:
            return [
                ConnectorItem(
                    connector_name=self.name,
                    title="Meteo",
                    body="Coordonnees manquantes",
                    updated_at=datetime.utcnow(),
                )
            ]

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,weather_code",
            "timezone": timezone,
        }

        response = requests.get(self.URL, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()

        current = payload.get("current", {})
        temperature = current.get("temperature_2m", "?")
        humidity = current.get("relative_humidity_2m", "?")
        weather_code = current.get("weather_code")
        label = WEATHER_CODE_LABELS.get(weather_code, "Inconnu")

        text = f"{label} {temperature}C HR {humidity}%"
        return [
            ConnectorItem(
                connector_name=self.name,
                title="Meteo",
                body=text,
                updated_at=datetime.utcnow(),
            )
        ]
