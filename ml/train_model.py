"""
Model training -- trained on real data.

Uses the AI4I 2020 Predictive Maintenance Dataset (Matzka, 2020), a
published, peer-reviewed industrial benchmark, in place of the earlier
hand-written synthetic generator. Trains:

  1. RandomForestClassifier  -- supervised failure predictor, trained on
                                 labeled real machine-failure outcomes.
  2. IsolationForest         -- unsupervised anomaly detector, fit only on
                                 rows the dataset itself labels as normal
                                 operation (Machine failure == 0).

Run:
    python ml/train_model.py
"""

import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import train_test_split

sys.path.append(str(Path(__file__).resolve().parents[1]))
from common.machines_config import (
    DATASET_PATH, MODEL_ANOMALY_PATH, MODEL_FAILURE_PATH, MODEL_FEATURES_PATH,
    NUMERIC_FEATURES,
)

RENAME = {
    "Air temperature [K]": "air_temperature",
    "Process temperature [K]": "process_temperature",
    "Rotational speed [rpm]": "rotational_speed",
    "Torque [Nm]": "torque",
    "Tool wear [min]": "tool_wear",
    "Machine failure": "machine_failure",
    "Type": "machine_type",
}


def load_dataset():
    df = pd.read_csv(DATASET_PATH)
    df = df.rename(columns=RENAME)
    df = pd.get_dummies(df, columns=["machine_type"], prefix="type")
    return df


def main():
    df = load_dataset()
    type_cols = [c for c in df.columns if c.startswith("type_")]
    feature_cols = NUMERIC_FEATURES + type_cols
    print(f"[train] loaded {len(df)} real rows from {DATASET_PATH}")
    print(f"[train] features: {feature_cols}")

    X = df[feature_cols]
    y = df["machine_failure"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # --- Supervised failure classifier ---
    clf = RandomForestClassifier(
        n_estimators=300, max_depth=12, class_weight="balanced", random_state=42
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)[:, 1]
    print("[train] failure classifier (held-out test set, real labels):")
    print(f"        accuracy  = {accuracy_score(y_test, y_pred):.3f}")
    print(f"        precision = {precision_score(y_test, y_pred):.3f}")
    print(f"        recall    = {recall_score(y_test, y_pred):.3f}")
    print(f"        f1        = {f1_score(y_test, y_pred):.3f}")
    print(f"        roc_auc   = {roc_auc_score(y_test, y_proba):.3f}")

    # --- Unsupervised anomaly detector, fit on normal-only rows ---
    normal_df = df[df["machine_failure"] == 0]
    anomaly_model = IsolationForest(n_estimators=200, contamination=0.05, random_state=42)
    anomaly_model.fit(normal_df[feature_cols])
    flagged_rate = (anomaly_model.predict(df[feature_cols]) == -1).mean()
    print(f"[train] anomaly model: flagged {flagged_rate:.1%} of all rows as anomalous")

    Path(MODEL_FAILURE_PATH).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, MODEL_FAILURE_PATH)
    joblib.dump(anomaly_model, MODEL_ANOMALY_PATH)
    joblib.dump(feature_cols, MODEL_FEATURES_PATH)
    print(f"[train] saved -> {MODEL_FAILURE_PATH}, {MODEL_ANOMALY_PATH}, {MODEL_FEATURES_PATH}")


if __name__ == "__main__":
    main()
