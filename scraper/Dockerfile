FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
# runs when CMD is overridden
COPY mapper.py ticker_matcher.py ./ 
# cache HuggingFace model weights at build-time
RUN python - <<'PY'
from transformers import AutoModelForSequenceClassification, AutoTokenizer
AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
AutoTokenizer.from_pretrained("ProsusAI/finbert")
PY
# expose metrics on :8010
EXPOSE 8010
CMD ["python", "price_worker.py"]
