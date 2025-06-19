# scraper/metrics_price.py
from prometheus_client import Counter

price_upserts = Counter(
    "price_upserts_total", "Rows inserted/updated by price_worker"
)
