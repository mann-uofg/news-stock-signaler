FROM python:3.11-slim

WORKDIR /app

# add a C/C++ tool-chain so pandas can compile
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential gcc g++ libpq-dev git && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy the app code
COPY . .

CMD ["python", "main.py"]
