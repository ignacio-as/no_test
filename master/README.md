# Master

API sencilla que guarda los eventos en PostgreSQL.

## Archivos

- `main.py`: contiene las funciones y endpoints.
- `requirements.txt`: contiene las librerias necesarias.
- `../database/schema.sql`: contiene la tabla de PostgreSQL.

## Base de datos local

Crear un usuario y una base de datos en PostgreSQL:

```sql
CREATE USER energyshark WITH PASSWORD 'energyshark';
CREATE DATABASE energyshark OWNER energyshark;
```

La API crea la tabla automaticamente cuando inicia.

## Ejecucion

Desde la raiz del proyecto:

```powershell
pip install -r master/requirements.txt
uvicorn master.main:app --reload
```

## Endpoints

```text
POST /events
GET  /history?page=1&limit=25
GET  /history/{id}
GET  /health
```

El historial se puede filtrar por `id`, `idpk`, `type`, `msgId`, `timestamp`,
`receivedAt`, `validUntil`, `metaContent`, `constraints`, `code`, `city`,
`demand` y `unit`.
