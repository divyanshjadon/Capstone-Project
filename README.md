# Predictive Maintenance System for Industrial Equipment Using IoT
### Backend — now trained and driven by real data

This backend was rebuilt to remove the earlier hand-rolled synthetic
generator. It's now trained on the **AI4I 2020 Predictive Maintenance
Dataset** (Matzka, 2020) — a published, peer-reviewed industrial benchmark
(10,000 labeled rows from a real milling machine's operating envelope),
widely used in predictive-maintenance research. Citation:
S. Matzka, "Explainable Artificial Intelligence for Predictive Maintenance
Applications," 3rd Int'l Conf. on AI for Industries, 2020.

```
Real Dataset (AI4I2020) --replayed via MQTT--> Ingestion --> ML Inference --> API --> Dashboard
```

## What changed from the earlier prototype

| Before (prototype) | Now (real) |
|---|---|
| Hand-written synthetic sensor generator | Real AI4I2020 dataset rows, replayed over MQTT |
| Hand-written synthetic training data | Trained directly on the real dataset's labeled failures |
| RUL from a regressor trained on made-up degradation curves | RUL from real tool-wear data against a threshold derived from the dataset's own tool-wear-failure cases (198–253 min) |
| Dashboard generated its own fake data in the browser | Dashboard polls the real FastAPI backend (`API_BASE_URL`) for every number it shows |
| Health formula was a hand-tuned heuristic | Health = `100 × (1 − real model's predicted failure probability)` |

## Real model performance (held-out test set, from `ml/train_model.py`)

- Accuracy: **0.979**
- Precision: **0.771**
- Recall: **0.544**
- F1: **0.638**
- ROC-AUC: **0.957**

Recall is moderate because real machine failures are rare (3.4% of the
dataset) and the classifier is deliberately biased toward not crying wolf;
this is a real, reportable trade-off worth discussing with a supervisor,
not a limitation to hide.

## Machine → dataset mapping

The dataset has no notion of "4 named machines" — it has a `Type` column
(L/M/H, representing product quality tiers). Each of our 4 machines is
mapped to real rows filtered by Type:

| Machine | Type | Playback order |
|---|---|---|
| M-101 (Conveyor Drive Motor) | M | shuffled |
| P-204 (Coolant Circulation Pump) | L | **ascending tool wear** (demo visibly approaches wear-out) |
| C-310 (Air Compressor) | H | shuffled |
| CV-05 (Main Conveyor Belt) | L | shuffled |

Every value shown is a real recorded row — only the *order* rows are
replayed in is chosen, since the dataset itself carries no timestamps.

## Honest status: what's real vs. what's still pending

- **Real:** the ML models, their training data, their evaluation metrics,
  the database schema, the API, and the dashboard's data source.
- **Still simulated:** live *timing* — there's no physical sensor hardware
  yet, so historical rows are replayed on a fixed interval rather than
  arriving from an actual machine in real time. This is the one piece
  needed to take the system from ~80% to fully deployed: point
  `simulator/sensor_simulator.py`'s topic at real hardware publishers (or
  retire it entirely) and everything downstream needs no changes.

## Running it locally

```bash
pip install -r requirements.txt --break-system-packages
mosquitto -p 1883 &

python ml/train_model.py          # trains on data/ai4i2020.csv, prints metrics

python ingestion/ingestion_service.py &
python ml/inference_service.py &
python simulator/sensor_simulator.py &
uvicorn api.app:app --reload --port 8000
```

Then point the dashboard's `API_BASE_URL` (top of the .jsx file) at
`http://localhost:8000` and open it — it polls the live API directly.

## Project structure

```
backend/
├── data/ai4i2020.csv     # real dataset (Matzka, 2020)
├── common/                # shared config + SQLite helpers
├── simulator/             # replays real rows over MQTT
├── ingestion/              # MQTT -> SQLite
├── ml/                    # real training + real-time inference
│   └── models/             # trained .pkl files (classifier, anomaly detector)
├── api/                   # FastAPI for the dashboard
├── docker-compose.yml
└── requirements.txt
```
