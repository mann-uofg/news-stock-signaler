import pandas as pd
from rapidfuzz import process, fuzz
from pathlib import Path

_ref = pd.read_csv(Path(__file__).parent       / "data" / "ticker_ref.csv")
COMPANY_TO_TICKER = {
    row.name.lower(): row.symbol
    for row in _ref.itertuples()
}
LONG_TO_TICKER = {
    row.long_name.lower(): row.symbol
    for row in _ref.itertuples() if isinstance(row.long_name, str)
}

def match(text: str, score_cutoff: int = 85) -> str | None:
    text = text.lower()
    # exact contains
    for name, sym in COMPANY_TO_TICKER.items():
        if name in text:
            return sym

    # fuzzy
    result = process.extractOne(
        text,
        list(COMPANY_TO_TICKER.keys()) + list(LONG_TO_TICKER.keys()),
        scorer=fuzz.partial_ratio
    )
    if result:
        best, score, _ = result
        if score >= score_cutoff:
            return COMPANY_TO_TICKER.get(best) or LONG_TO_TICKER.get(best)

    return None
