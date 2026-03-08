"""
Sentiment analysis using FinBERT.

Uses the ProsusAI/finbert model from HuggingFace to classify
financial text as positive, negative, or neutral.
"""

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Lazy-loaded globals
_tokenizer = None
_model = None
_labels = ["positive", "negative", "neutral"]


def _load_model():
    """Load FinBERT model and tokenizer (cached after first call)."""
    global _tokenizer, _model
    if _tokenizer is None:
        _tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
        _model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
        _model.eval()
    return _tokenizer, _model


def analyze_sentiment(texts: list[str], log_callback=None) -> list[dict]:
    """
    Run FinBERT sentiment analysis on a list of texts.

    Args:
        texts: List of strings to analyze.

    Returns:
        List of dicts with keys: text (truncated), label, score
    """
    if not texts:
        return []

    tokenizer, model = _load_model()
    results = []

    # Process in batches of 16 to manage memory
    batch_size = 16
    total_batches = (len(texts) + batch_size - 1) // batch_size
    for i in range(0, len(texts), batch_size):
        batch_num = (i // batch_size) + 1
        if log_callback:
            log_callback(f'{{"step": "sentiment", "message": "Analyzing sentiment batch {batch_num} of {total_batches}..."}}')
            
        batch = texts[i : i + batch_size]

        # Filter out empty strings
        batch = [t for t in batch if t.strip()]
        if not batch:
            continue

        inputs = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )

        with torch.no_grad():
            outputs = model(**inputs)

        probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)

        for j, text in enumerate(batch):
            probs = probabilities[j]
            best_idx = torch.argmax(probs).item()
            results.append(
                {
                    "text": text[:200] + "..." if len(text) > 200 else text,
                    "label": _labels[best_idx],
                    "score": round(probs[best_idx].item(), 4),
                }
            )

    return results


def compute_summary(sentiments: list[dict]) -> dict:
    """
    Compute aggregate sentiment summary.

    Args:
        sentiments: List of sentiment dicts from analyze_sentiment().

    Returns:
        Dict with counts, average scores per label, and overall verdict.
    """
    if not sentiments:
        return {
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "average_positive_score": 0.0,
            "average_negative_score": 0.0,
            "average_neutral_score": 0.0,
            "verdict": "neutral",
        }

    counts = {"positive": 0, "negative": 0, "neutral": 0}
    score_sums = {"positive": 0.0, "negative": 0.0, "neutral": 0.0}

    for s in sentiments:
        label = s["label"]
        counts[label] += 1
        score_sums[label] += s["score"]

    avg_scores = {}
    for label in _labels:
        avg_scores[label] = (
            round(score_sums[label] / counts[label], 4) if counts[label] > 0 else 0.0
        )

    # Verdict = label with the most entries
    verdict = max(counts, key=counts.get)

    return {
        "positive": counts["positive"],
        "negative": counts["negative"],
        "neutral": counts["neutral"],
        "average_positive_score": avg_scores["positive"],
        "average_negative_score": avg_scores["negative"],
        "average_neutral_score": avg_scores["neutral"],
        "verdict": verdict,
    }

class SentimentAnalyzer:
    def analyze(self, texts: list[str], log_callback=None) -> dict:
        sentiments = analyze_sentiment(texts, log_callback)
        summary = compute_summary(sentiments)
        return summary

