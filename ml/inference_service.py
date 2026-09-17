"""
Inference service -- scores live (replayed-real) telemetry with the models
trained in ml/train_model.py on the real AI4I2020 dataset.

For each reading: builds the same feature vector used at training time
(numeric sensor values + one-hot machine type), gets a real failure
probability from the RandomForest classifier, an anomaly flag from the
IsolationForest, and a Remaining-Useful-Life estimate derived directly
from tool wear against the data-derived TOOL_WEAR_FAILURE_THRESHOLD.

Run (after ml/train_model.py has produced the model files):
    python ml/inference_service.py
"""

import json
import sys
from pathlib import Path

import joblib
import pandas as pd
import paho.mqtt.client as mqtt

sys.path.append(str(Path(__file__).resolve().parents[1]))
from common.db import init_db, insert_alert, insert_health
from common.machines_config import (
    HEALTH_TOPIC_TMPL, MACHINES, MODEL_ANOMALY_PATH, MODEL_FAILURE_PATH,
    MODEL_FEATURES_PATH, MQTT_HOST, MQTT_PORT, NUMERIC_FEATURES,
    TELEMETRY_TOPIC_WILDCARD, TOOL_WEAR_FAILURE_THRESHOLD,
)

_last_status = {}  # machine_id -> last known status, for alert de-duplication


def status_from_health(health):
    if health >= 75:
        return "healthy"
    if health >= 50:
        return "warning"
    return "critical"


def build_features(payload, machine_id, feature_cols):
    dtype = MACHINES[machine_id]["dataset_type"]
    row = {f: payload[f] for f in NUMERIC_FEATURES}
    for col in feature_cols:
        if col.startswith("type_"):
            row[col] = 1 if col == f"type_{dtype}" else 0
    return pd.DataFrame([row])[feature_cols]


def main():
    init_db()
    failure_model = joblib.load(MODEL_FAILURE_PATH)
    anomaly_model = joblib.load(MODEL_ANOMALY_PATH)
    feature_cols = joblib.load(MODEL_FEATURES_PATH)
    print(f"[inference] real models loaded (features: {feature_cols})")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="inference-service")

    def on_connect(c, userdata, flags, reason_code, properties=None):
        print(f"[inference] connected (rc={reason_code})")
        c.subscribe(TELEMETRY_TOPIC_WILDCARD, qos=1)

    def on_message(c, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            machine_id = payload["machine_id"]
            cfg = MACHINES[machine_id]

            X = build_features(payload, machine_id, feature_cols)
            failure_probability = float(failure_model.predict_proba(X)[0, 1])
            is_anomaly = bool(anomaly_model.predict(X)[0] == -1)

            health = max(2, min(100, round(100 * (1 - failure_probability))))
            status = status_from_health(health)

            rul_minutes = max(0.0, TOOL_WEAR_FAILURE_THRESHOLD - payload["tool_wear"])

            ts = payload["ts"]
            insert_health(machine_id, ts, health, failure_probability, is_anomaly, rul_minutes, status)

            c.publish(
                HEALTH_TOPIC_TMPL.format(machine_id=machine_id),
                json.dumps({
                    "machine_id": machine_id, "ts": ts, "health": health,
                    "status": status, "rul_minutes": rul_minutes,
                    "failure_probability": round(failure_probability, 4), "is_anomaly": is_anomaly,
                }),
                qos=1,
            )

            prev = _last_status.get(machine_id, "healthy")
            if status != prev and status in ("warning", "critical"):
                message = (
                    f"{cfg['name']} ({machine_id}) crossed critical threshold "
                    f"- health {health}%, failure probability {failure_probability:.1%}, "
                    f"~{rul_minutes:.0f} min of tool life remaining."
                    if status == "critical"
                    else f"{cfg['name']} ({machine_id}) trending abnormal - health {health}%."
                )
                insert_alert(machine_id, ts, status, message)
                print(f"[ALERT:{status.upper()}] {message}")
            _last_status[machine_id] = status

            print(f"[inference] {machine_id}: health={health} status={status} "
                  f"p_fail={failure_probability:.3f} anomaly={is_anomaly} rul={rul_minutes:.0f}min")
        except Exception as exc:  # noqa: BLE001
            print(f"[inference] failed to process message on {msg.topic}: {exc}")

    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    client.loop_forever()


if __name__ == "__main__":
    main()
