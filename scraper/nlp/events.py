# scraper/nlp/events.py

# simple keyword-based event labeling
POS_KEYWORDS = ["rise", "rally", "gain", "soar", "beat", "surge", "up"]
NEG_KEYWORDS = ["fall", "drop", "decline", "pullback", "selloff", "plunge", "down"]

def label(text: str) -> str:
    t = text.lower()
    if any(word in t for word in POS_KEYWORDS):
        return "bullish_event"
    if any(word in t for word in NEG_KEYWORDS):
        return "bearish_event"
    return "noise"
