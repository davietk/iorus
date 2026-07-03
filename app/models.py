from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ConnectorItem:
    connector_name: str
    title: str
    body: str
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def as_lines(self) -> list[str]:
        body_line = self.body.strip().replace("\n", " ")
        return [self.title.strip(), body_line]
