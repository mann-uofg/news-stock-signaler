from prometheus_client import Counter, Histogram

SCRAPE_COUNTER = Counter("scraper_rss_total", "RSS scrape requests")
SCRAPE_TIME = Histogram("scraper_rss_seconds", "RSS scrape latency")
