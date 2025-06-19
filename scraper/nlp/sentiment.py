from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch, huggingface_hub, os, pathlib

MODEL_NAME = "ProsusAI/finbert"
CACHE = pathlib.Path("/app/.cache")  # inside container

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, cache_dir=CACHE)
model     = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME, cache_dir=CACHE
).eval()

def score(text: str) -> float:
    """Returns scaled sentiment in -1…1."""
    with torch.no_grad():
        inputs = tokenizer(text, truncation=True, padding=True, return_tensors="pt")
        logits = model(**inputs).logits.squeeze().tolist()
    # FinBERT order: [negative, neutral, positive]
    neg, neu, pos = torch.softmax(torch.tensor(logits), dim=0)
    return (pos - neg).item()
