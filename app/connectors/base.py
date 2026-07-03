from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.models import ConnectorItem


class BaseConnector(ABC):
    def __init__(self, settings: dict[str, Any]):
        self.settings = settings
        self.connector_type = str(settings.get("type", self.__class__.__name__.lower()))
        self.name = settings.get("name", self.__class__.__name__.lower())
        self.interval_seconds = int(settings.get("interval_seconds", 300))

    @abstractmethod
    def fetch(self) -> list[ConnectorItem]:
        raise NotImplementedError
