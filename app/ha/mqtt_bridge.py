from __future__ import annotations

import json
import logging
from typing import Any

import paho.mqtt.client as mqtt

LOGGER = logging.getLogger(__name__)


class MqttBridge:
    def __init__(self, settings: dict[str, Any]):
        self.settings = settings
        self.enabled = bool(settings.get("enabled", False))
        self.client: mqtt.Client | None = None

        self.discovery_prefix = settings.get("discovery_prefix", "homeassistant")
        self.state_prefix = settings.get("state_prefix", "led_matrix")
        self.device_id = settings.get("device_id", "led_matrix_pi")

        if self.enabled:
            self._connect()

    def _connect(self) -> None:
        host = self.settings.get("host", "localhost")
        port = int(self.settings.get("port", 1883))
        username = self.settings.get("username") or None
        password = self.settings.get("password") or None
        client_id = self.settings.get("client_id") or "led-matrix-client"

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        if username and password:
            self.client.username_pw_set(username, password)

        self.client.connect(host, port, 60)
        self.client.loop_start()
        LOGGER.info("Connected to MQTT broker %s:%s", host, port)

    def publish_discovery_for_connector(self, connector_name: str) -> None:
        if not self.enabled or not self.client:
            return

        unique_id = f"{self.device_id}_{connector_name}"
        topic = f"{self.discovery_prefix}/sensor/{unique_id}/config"
        state_topic = f"{self.state_prefix}/{self.device_id}/{connector_name}/state"

        payload = {
            "name": f"LED Matrix {connector_name}",
            "unique_id": unique_id,
            "state_topic": state_topic,
            "icon": "mdi:led-strip-variant",
            "device": {
                "identifiers": [self.device_id],
                "name": "LED Matrix Dashboard",
                "manufacturer": "Custom",
                "model": "Raspberry Pi 64x32",
            },
        }

        self.client.publish(topic, json.dumps(payload), qos=0, retain=True)

    def publish_connector_state(self, connector_name: str, state: str) -> None:
        if not self.enabled or not self.client:
            return

        topic = f"{self.state_prefix}/{self.device_id}/{connector_name}/state"
        self.client.publish(topic, state, qos=0, retain=True)

    def publish_status(self, status: str) -> None:
        self.publish_connector_state("status", status)

    def shutdown(self) -> None:
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
