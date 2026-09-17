"""
Sensor "simulator" -- now a real-data replay service.

There is no physical sensor hardware deployed yet, so this replays real
recorded rows from the AI4I 2020 dataset over MQTT, standing in for a live
feed until hardware is wired up. This is a standard technique for testing
streaming pipelines before real-time hardware exists -- the values
themselves are genuine recorded machine measurements, only their
publication timing is simulated.

Each machine is restricted to rows matching its configured dataset Type
(L/M/H). P-204 is played back ordered by ascending tool wear so a demo
run visibly approaches the tool-wear-failure zone; every other machine
plays its rows back in random (shuffled) order, since the dataset has no
native time ordering.

Run:
    python simulator/sensor_simulator.py
"""

import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import paho.mqtt.client as mqtt

sys.path.append(str(Path(__file__).resolve().parents[1]))
from common.machines_config import DATASET_PATH, MACHINES, MQTT_HOST, MQTT_PORT, TELEMETRY_TOPIC_TMPL

TICK_SECONDS = 2.0

COLS = {
    "Air temperature [K]": "air_temperature",
    "Process temperature [K]": "process_temperature",
    "Rotational speed [rpm]": "rotational_speed",
    "Torque [Nm]": "torque",
    "Tool wear [min]": "tool_wear",
}


def load_playback_queues():
    df = pd.read_csv(DATASET_PATH).rename(columns=COLS)
    queues = {}
    for machine_id, cfg in MACHINES.items():
        subset = df[df["Type"] == cfg["dataset_type"]]
        if cfg["demo_playback"] == "wear_ascending":
            subset = subset.sort_values("tool_wear")
        else:
            subset = subset.sample(frac=1, random_state=hash(machine_id) % (2**31))
        queues[machine_id] = subset[list(COLS.values())].to_dict("records")
        print(f"[simulator] {machine_id} ({cfg['dataset_type']}-type): {len(queues[machine_id])} real rows queued, "
              f"order={cfg['demo_playback']}")
    return queues


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sensor-replay")
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    client.loop_start()

    queues = load_playback_queues()
    cursors = {mid: 0 for mid in MACHINES}
    print(f"[simulator] replaying real AI4I2020 rows for {len(MACHINES)} machines every {TICK_SECONDS}s ...")

    try:
        while True:
            for machine_id in MACHINES:
                queue = queues[machine_id]
                i = cursors[machine_id] % len(queue)
                row = queue[i]
                cursors[machine_id] += 1

                payload = {"machine_id": machine_id, "ts": datetime.now(timezone.utc).isoformat(), **row}
                topic = TELEMETRY_TOPIC_TMPL.format(machine_id=machine_id)
                client.publish(topic, json.dumps(payload), qos=1)
                print(f"[simulator] -> {topic} {payload}")
            time.sleep(TICK_SECONDS)
    except KeyboardInterrupt:
        print("\n[simulator] stopped.")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
