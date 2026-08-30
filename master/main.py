"""API sencilla para guardar y consultar eventos."""

import json
import os
from pathlib import Path
from uuid import UUID

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from psycopg.rows import dict_row


load_dotenv()

app = FastAPI()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://energyshark:energyshark@localhost:5432/energyshark",
)


def connect_to_database():
    """Abre una conexion con PostgreSQL."""
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def create_table():
    """Crea la tabla si todavia no existe."""
    schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
    schema = schema_path.read_text(encoding="utf-8")

    with connect_to_database() as connection:
        connection.execute(schema)


def valid_event(event):
    """Revisa los campos basicos del mensaje."""
    try:
        UUID(event["idpk"])
        body = event["packageBody"]

        return (
            event["type"] == "demand-set"
            and isinstance(body["demands"], list)
            and "validUntil" in body
            and "metaContent" in body
            and "constraints" in body
        )
    except (KeyError, TypeError, ValueError):
        return False


def format_event(row):
    """Agrega el ID y receivedAt al evento original."""
    event = dict(row["event_data"])
    event["id"] = row["id"]
    event["receivedAt"] = row["received_at"]
    return event


def save_event(event):
    """Guarda un evento en PostgreSQL."""
    query = """
        INSERT INTO events (idpk, event_data)
        VALUES (%s, %s::jsonb)
        RETURNING id, event_data, received_at
    """

    with connect_to_database() as connection:
        row = connection.execute(
            query,
            (event["idpk"], json.dumps(event)),
        ).fetchone()

    return format_event(row)


def find_event(event_id):
    """Busca un evento usando su ID interno."""
    query = """
        SELECT id, event_data, received_at
        FROM events
        WHERE id = %s
    """

    with connect_to_database() as connection:
        row = connection.execute(query, (event_id,)).fetchone()

    if row is None:
        return None

    return format_event(row)


def add_filters(query_parameters):
    """Convierte los query parameters en condiciones para PostgreSQL."""
    conditions = []
    values = []

    simple_fields = {
        "id": "id::text",
        "idpk": "idpk::text",
        "type": "event_data ->> 'type'",
        "msgId": "event_data ->> 'msgId'",
        "timestamp": "event_data ->> 'timestamp'",
        "validUntil": "event_data -> 'packageBody' ->> 'validUntil'",
        "metaContent": "event_data -> 'packageBody' ->> 'metaContent'",
    }
    demand_fields = ["code", "city", "demand", "unit"]

    for field, value in query_parameters.items():
        if field in ["page", "limit"]:
            continue

        if field in simple_fields:
            conditions.append(simple_fields[field] + " = %s")
            values.append(value)
        elif field == "receivedAt":
            conditions.append("received_at::date = %s::date")
            values.append(value)
        elif field == "constraints":
            conditions.append(
                "event_data -> 'packageBody' -> 'constraints' = %s::jsonb"
            )
            values.append(value)
        elif field in demand_fields:
            conditions.append(
                "EXISTS ("
                "SELECT 1 FROM jsonb_array_elements("
                "event_data -> 'packageBody' -> 'demands'"
                f") AS demand WHERE demand ->> '{field}' = %s"
                ")"
            )
            values.append(value)

    return conditions, values


def list_events(page, limit, query_parameters):
    """Devuelve una pagina del historial."""
    conditions, values = add_filters(query_parameters)

    query = "SELECT id, event_data, received_at FROM events"

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY received_at DESC LIMIT %s OFFSET %s"
    values.extend([limit, (page - 1) * limit])

    with connect_to_database() as connection:
        rows = connection.execute(query, values).fetchall()

    return [format_event(row) for row in rows]


@app.on_event("startup")
def startup():
    """Prepara la tabla al iniciar la API."""
    create_table()


@app.get("/health")
def health():
    """Comprueba que PostgreSQL responda."""
    try:
        with connect_to_database() as connection:
            connection.execute("SELECT 1")
        return {"status": "ok"}
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="Database unavailable")


@app.post("/events", status_code=201)
def create_event(event: dict):
    """Recibe un evento enviado por connector."""
    if not valid_event(event):
        raise HTTPException(status_code=400, detail="Invalid event")

    try:
        return save_event(event)
    except psycopg.errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="idpk already exists")


@app.get("/history")
def history(
    request: Request,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=100),
):
    """Entrega una pagina del historial."""
    events = list_events(page, limit, request.query_params)

    return {
        "page": page,
        "limit": limit,
        "results": events,
    }


@app.get("/history/{event_id}")
def history_detail(event_id: int):
    """Entrega un evento usando su ID interno."""
    event = find_event(event_id)

    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")

    return event
