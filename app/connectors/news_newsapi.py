from __future__ import annotations

import os
from datetime import datetime

import requests

from app.connectors.base import BaseConnector
from app.models import ConnectorItem


class NewsApiConnector(BaseConnector):
    URL = "https://newsapi.org/v2/everything"

    def fetch(self) -> list[ConnectorItem]:
        api_key = self.settings.get("api_key")
        api_key_env = self.settings.get("api_key_env")
        if not api_key and api_key_env:
            api_key = os.getenv(api_key_env)

        if not api_key:
            return [
                ConnectorItem(
                    connector_name=self.name,
                    title="Actu",
                    body="Cle NewsAPI manquante",
                    updated_at=datetime.utcnow(),
                )
            ]

        query = self.settings.get("query", "technologie")
        language = self.settings.get("language", "fr")
        page_size = int(self.settings.get("page_size", 3))

        params = {
            "q": query,
            "language": language,
            "pageSize": page_size,
            "sortBy": "publishedAt",
            "apiKey": api_key,
        }
        response = requests.get(self.URL, params=params, timeout=10)
        response.raise_for_status()
        payload = response.json()

        articles = payload.get("articles", [])
        if not articles:
            return [
                ConnectorItem(
                    connector_name=self.name,
                    title="Actu",
                    body="Aucune actualite",
                    updated_at=datetime.utcnow(),
                )
            ]

        items: list[ConnectorItem] = []
        for article in articles:
            title = article.get("title", "Sans titre")
            source = (article.get("source") or {}).get("name") or "Source"
            items.append(
                ConnectorItem(
                    connector_name=self.name,
                    title=f"Actu {source}",
                    body=title,
                    updated_at=datetime.utcnow(),
                )
            )

        return items
