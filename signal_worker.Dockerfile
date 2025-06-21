FROM python:3.11-slim

WORKDIR /app

COPY signal_worker/requirements.txt .
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y build-essential && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY signal_worker/ .

CMD ["python", "-u", "signal_worker.py"]
