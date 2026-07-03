from __future__ import annotations

import os
from datetime import datetime

import requests

from app.connectors.base import BaseConnector
from app.models import ConnectorItem


class FinnhubStocksConnector(BaseConnector):
    URL = "https://finnhub.io/api/v1/quote"

    def fetch(self) -> list[ConnectorItem]:
        symbols = self.settings.get("symbols", [])
        token = self.settings.get("token")
        token_env = self.settings.get("token_env")
        if not token and token_env:
            token = os.getenv(token_env)

        if not symbols:
            return [
                ConnectorItem(
                    connector_name=self.name,
                    title="Bourse",
                    body="Aucun symbole configure",
                    updated_at=datetime.utcnow(),
                )
            ]

        if not token:
            return [
                ConnectorItem(
                    connector_name=self.name,
                    title="Bourse",
                    body="Token Finnhub manquant",
                    updated_at=datetime.utcnow(),
                )
            ]

        items: list[ConnectorItem] = []
        for symbol in symbols:
            params = {"symbol": symbol, "token": token}
            response = requests.get(self.URL, params=params, timeout=10)
            response.raise_for_status()
            quote = response.json()

            current = quote.get("c", 0)
            previous_close = quote.get("pc", 0)
            delta_pct = 0.0
            if previous_close:
                delta_pct = ((current - previous_close) / previous_close) * 100

            sign = "+" if delta_pct >= 0 else ""
            body = f"{current:.2f} USD ({sign}{delta_pct:.2f}%)"
            items.append(
                ConnectorItem(
                    connector_name=self.name,
                    title=f"{symbol}",
                    body=body,
                    updated_at=datetime.utcnow(),
                )
            )

        return items
