FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY master/requirements.txt ./master/requirements.txt
RUN python -m pip install --no-cache-dir -r master/requirements.txt

COPY master ./master
COPY database ./database

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "master.main:app", "--host", "0.0.0.0", "--port", "8000"]

