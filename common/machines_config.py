"""
Shared configuration.

Machines are now mapped onto product-quality "Type" categories (L / M / H)
from the AI4I 2020 Predictive Maintenance dataset (Matzka, 2020) -- a
published, peer-reviewed benchmark modeled on a real industrial milling
machine, widely used in predictive-maintenance research. Each simulated
machine below replays real recorded rows filtered to its Type, standing
in for a live sensor feed until physical hardware is deployed.

TOOL_WEAR_FAILURE_THRESHOLD (240 min) is not arbitrary: it's derived from
the dataset itself -- Tool-Wear-Failure (TWF) events in AI4I 2020 cluster
between 198 and 253 minutes of tool wear (mean ~216 min), so 240 min is
used as the point at which tool-wear risk is considered acute.
"""

MQTT_HOST = "localhost"
MQTT_PORT = 1883
TELEMETRY_TOPIC_TMPL = "plant/line2/{machine_id}/telemetry"
HEALTH_TOPIC_TMPL = "plant/line2/{machine_id}/health"
TELEMETRY_TOPIC_WILDCARD = "plant/+/+/telemetry"

DATASET_PATH = "data/ai4i2020.csv"
DB_PATH = "data/telemetry.db"
MODEL_FAILURE_PATH = "ml/models/failure_model.pkl"
MODEL_ANOMALY_PATH = "ml/models/anomaly_model.pkl"
MODEL_FEATURES_PATH = "ml/models/feature_columns.pkl"

TOOL_WEAR_FAILURE_THRESHOLD = 240  # minutes; data-derived, see module docstring

NUMERIC_FEATURES = [
    "air_temperature", "process_temperature", "rotational_speed", "torque", "tool_wear",
]

MACHINES = {
    "M-101": {
        "name": "Conveyor Drive Motor",
        "unit": "Line 2 - Assembly",
        "dataset_type": "M",
        "demo_playback": "shuffled",
    },
    "P-204": {
        "name": "Coolant Circulation Pump",
        "unit": "Line 2 - Cooling Loop",
        "dataset_type": "L",
        # played back ordered by ascending tool wear so the demo visibly
        # progresses toward wear-out -- still real recorded rows, only the
        # *order* of playback is chosen; see simulator for details
        "demo_playback": "wear_ascending",
    },
    "C-310": {
        "name": "Air Compressor",
        "unit": "Utilities - Bay 3",
        "dataset_type": "H",
        "demo_playback": "shuffled",
    },
    "CV-05": {
        "name": "Main Conveyor Belt",
        "unit": "Line 2 - Assembly",
        "dataset_type": "L",
        "demo_playback": "shuffled",
    },
}
