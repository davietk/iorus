from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from app.connectors.base import BaseConnector
from app.models import ConnectorItem


class GarminConnectConnector(BaseConnector):
    def fetch(self) -> list[ConnectorItem]:
        email = self.settings.get("email")
        password = self.settings.get("password")

        email_env = self.settings.get("email_env")
        password_env = self.settings.get("password_env")

        if not email and email_env:
            email = os.getenv(email_env)
        if not password and password_env:
            password = os.getenv(password_env)

        if not email or not password:
            return [
                ConnectorItem(
                    connector_name=self.name,
                    title="Garmin",
                    body="Identifiants Garmin manquants",
                    updated_at=datetime.utcnow(),
                )
            ]

        try:
            from garminconnect import Garmin  # type: ignore
        except Exception:
            return [
                ConnectorItem(
                    connector_name=self.name,
                    title="Garmin",
                    body="Lib garminconnect non installee",
                    updated_at=datetime.utcnow(),
                )
            ]

        try:
            client = Garmin(email, password)
            client.login()
        except Exception as exc:
            return [
                ConnectorItem(
                    connector_name=self.name,
                    title="Garmin",
                    body=f"Connexion impossible: {str(exc)[:60]}",
                    updated_at=datetime.utcnow(),
                )
            ]

        next_session = self._read_next_session(client)
        if not next_session:
            return [
                ConnectorItem(
                    connector_name=self.name,
                    title="Garmin",
                    body="Aucun entrainement planifie",
                    updated_at=datetime.utcnow(),
                )
            ]

        title = str(next_session.get("title") or "Prochaine seance")
        when = str(next_session.get("when") or "Date inconnue")
        sport = str(next_session.get("sport") or "")
        body = f"{when} {sport}".strip()

        return [
            ConnectorItem(
                connector_name=self.name,
                title=title,
                body=body,
                updated_at=datetime.utcnow(),
            )
        ]

    def _read_next_session(self, client: Any) -> dict[str, Any] | None:
        workouts = self._collect_scheduled_workouts(client)
        if not workouts:
            return None

        now = datetime.now(timezone.utc)
        parsed: list[tuple[datetime, dict[str, Any]]] = []
        for workout in workouts:
            start_dt = self._extract_start_datetime(workout)
            if not start_dt:
                continue
            if start_dt >= now:
                parsed.append((start_dt, workout))

        if not parsed:
            return None

        parsed.sort(key=lambda item: item[0])
        workout_dt, workout = parsed[0]

        sport = (
            workout.get("sportType")
            or workout.get("workoutName")
            or workout.get("typeKey")
            or ""
        )
        title = workout.get("workoutName") or workout.get("title") or "Prochaine seance"

        return {
            "title": str(title),
            "when": workout_dt.astimezone().strftime("%d/%m %H:%M"),
            "sport": str(sport),
        }

    def _collect_scheduled_workouts(self, client: Any) -> list[dict[str, Any]]:
        candidates: list[Any] = []

        method_names = [
            "get_workouts",
            "get_calendar_data",
            "get_training_calendar",
            "get_calendar",
        ]
        for method_name in method_names:
            method = getattr(client, method_name, None)
            if not callable(method):
                continue

            try:
                result = method()
                candidates.append(result)
            except TypeError:
                try:
                    start_dt = datetime.utcnow()
                    end_dt = start_dt + timedelta(days=14)
                    start = start_dt.strftime("%Y-%m-%d")
                    end = end_dt.strftime("%Y-%m-%d")
                    result = method(start, end)
                    candidates.append(result)
                except Exception:
                    continue
            except Exception:
                continue

        workouts: list[dict[str, Any]] = []
        for candidate in candidates:
            workouts.extend(self._flatten_workouts(candidate))

        unique: list[dict[str, Any]] = []
        seen_ids: set[str] = set()
        for workout in workouts:
            workout_id = str(
                workout.get("workoutId")
                or workout.get("eventId")
                or workout.get("id")
                or id(workout)
            )
            if workout_id in seen_ids:
                continue
            seen_ids.add(workout_id)
            unique.append(workout)

        return unique

    def _flatten_workouts(self, payload: Any) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []

        if isinstance(payload, dict):
            possible_lists = [
                payload.get("workouts"),
                payload.get("calendarItems"),
                payload.get("items"),
                payload.get("events"),
            ]
            for maybe_list in possible_lists:
                items.extend(self._flatten_workouts(maybe_list))

            if any(key in payload for key in ["workoutName", "startTime", "startTimeGMT", "date"]):
                items.append(payload)
            return items

        if isinstance(payload, list):
            for item in payload:
                items.extend(self._flatten_workouts(item))

        return items

    def _extract_start_datetime(self, workout: dict[str, Any]) -> datetime | None:
        value = (
            workout.get("startTimeGMT")
            or workout.get("startTimeLocal")
            or workout.get("startTime")
            or workout.get("date")
            or workout.get("calendarDate")
        )
        if not value:
            return None

        text = str(value).strip().replace("Z", "+00:00")

        for fmt in [None, "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]:
            try:
                if fmt is None:
                    dt = datetime.fromisoformat(text)
                else:
                    dt = datetime.strptime(text, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except ValueError:
                continue

        return None
