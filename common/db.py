"""
SQLite storage layer -- shared by the ingestion service, inference service,
and API.
"""

import sqlite3
from pathlib import Path

from common.machines_config import DB_PATH


def get_connection():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id TEXT NOT NULL,
            ts TEXT NOT NULL,
            air_temperature REAL NOT NULL,
            process_temperature REAL NOT NULL,
            rotational_speed REAL NOT NULL,
            torque REAL NOT NULL,
            tool_wear REAL NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS health_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id TEXT NOT NULL,
            ts TEXT NOT NULL,
            health REAL NOT NULL,
            failure_probability REAL NOT NULL,
            is_anomaly INTEGER NOT NULL,
            rul_minutes REAL,
            status TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id TEXT NOT NULL,
            ts TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL
        )
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_readings_machine ON readings(machine_id, ts)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_health_machine ON health_scores(machine_id, ts)")
    conn.commit()
    conn.close()


def insert_reading(machine_id, ts, air_temperature, process_temperature, rotational_speed, torque, tool_wear):
    conn = get_connection()
    conn.execute(
        "INSERT INTO readings (machine_id, ts, air_temperature, process_temperature, rotational_speed, torque, tool_wear) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (machine_id, ts, air_temperature, process_temperature, rotational_speed, torque, tool_wear),
    )
    conn.commit()
    conn.close()


def insert_health(machine_id, ts, health, failure_probability, is_anomaly, rul_minutes, status):
    conn = get_connection()
    conn.execute(
        "INSERT INTO health_scores (machine_id, ts, health, failure_probability, is_anomaly, rul_minutes, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (machine_id, ts, health, failure_probability, int(is_anomaly), rul_minutes, status),
    )
    conn.commit()
    conn.close()


def insert_alert(machine_id, ts, severity, message):
    conn = get_connection()
    conn.execute(
        "INSERT INTO alerts (machine_id, ts, severity, message) VALUES (?, ?, ?, ?)",
        (machine_id, ts, severity, message),
    )
    conn.commit()
    conn.close()
