"""
API service -- REST layer in front of SQLite, for the dashboard to consume
instead of generating data client-side.

Run:
    uvicorn api.app:app --reload --port 8000
"""

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(str(Path(__file__).resolve().parents[1]))
from common.db import get_connection, init_db
from common.machines_config import MACHINES

app = FastAPI(title="Predictive Maintenance API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before any real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/machines")
def list_machines():
    conn = get_connection()
    result = []
    for machine_id, cfg in MACHINES.items():
        latest_reading = conn.execute(
            "SELECT * FROM readings WHERE machine_id = ? ORDER BY id DESC LIMIT 1", (machine_id,)
        ).fetchone()
        latest_health = conn.execute(
            "SELECT * FROM health_scores WHERE machine_id = ? ORDER BY id DESC LIMIT 1", (machine_id,)
        ).fetchone()
        result.append(
            {
                "machine_id": machine_id,
                "name": cfg["name"],
                "unit": cfg["unit"],
                "dataset_type": cfg["dataset_type"],
                "latest_reading": dict(latest_reading) if latest_reading else None,
                "health": dict(latest_health) if latest_health else None,
            }
        )
    conn.close()
    return result


@app.get("/api/machines/{machine_id}/history")
def machine_history(machine_id: str, limit: int = 50):
    if machine_id not in MACHINES:
        raise HTTPException(status_code=404, detail="unknown machine_id")
    conn = get_connection()
    rows = conn.execute(
        "SELECT machine_id, ts, air_temperature, process_temperature, rotational_speed, torque, tool_wear "
        "FROM readings WHERE machine_id = ? ORDER BY id DESC LIMIT ?",
        (machine_id, limit),
    ).fetchall()
    conn.close()
    return list(reversed([dict(r) for r in rows]))


@app.get("/api/alerts")
def list_alerts(limit: int = 20):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
