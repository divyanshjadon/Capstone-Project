"""
Ingestion service.

Subscribes to all machine telemetry topics and persists every reading
(now real AI4I2020-sourced values, replayed by the simulator) to SQLite.

Run:
    python ingestion/ingestion_service.py
"""

import json
import sys
from pathlib import Path

import paho.mqtt.client as mqtt

sys.path.append(str(Path(__file__).resolve().parents[1]))
from common.db import init_db, insert_reading
from common.machines_config import MQTT_HOST, MQTT_PORT, TELEMETRY_TOPIC_WILDCARD


def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"[ingestion] connected to broker (rc={reason_code})")
    client.subscribe(TELEMETRY_TOPIC_WILDCARD, qos=1)
    print(f"[ingestion] subscribed to {TELEMETRY_TOPIC_WILDCARD}")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        insert_reading(
            payload["machine_id"],
            payload["ts"],
            payload["air_temperature"],
            payload["process_temperature"],
            payload["rotational_speed"],
            payload["torque"],
            payload["tool_wear"],
        )
        print(f"[ingestion] stored reading for {payload['machine_id']} @ {payload['ts']}")
    except Exception as exc:  # noqa: BLE001 -- log and keep the service alive
        print(f"[ingestion] failed to process message on {msg.topic}: {exc}")


def main():
    init_db()
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ingestion-service")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    client.loop_forever()


if __name__ == "__main__":
    main()
