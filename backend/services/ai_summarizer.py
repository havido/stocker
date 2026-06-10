"""
AI summarizer.

Uses Groq's OpenAI-compatible Chat Completions API to generate an investment
summary from the ticker, scraped texts, and FinBERT sentiment analysis.
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
# Override with GROQ_MODEL if desired (e.g. llama-3.1-8b-instant for more volume).
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


def generate_summary(
    ticker: str,
    sentiment_summary: dict,
    sample_texts: list[str],
    log_callback=None,
) -> str:
    """
    Generate an AI investment summary.

    Args:
        ticker: Stock ticker symbol.
        sentiment_summary: The FinBERT aggregate result (counts, scores, grade).
        sample_texts: A sample of the raw scraped texts (capped for context window).
        log_callback: Optional callback for SSE progress updates.

    Returns:
        Markdown-formatted investment summary string, or "" on any failure
        (so the frontend cleanly hides the panel instead of showing an error).
    """
    if log_callback:
        log_callback('{"step": "summary", "message": "Generating AI investment summary..."}')

    # Cap sample texts to avoid blowing the context window
    capped_texts = sample_texts[:15]
    sources_block = "\n".join(f"- {t[:300]}" for t in capped_texts)

    prompt = f"""You are a senior equity research analyst. Based on the following data for ${ticker}, write a concise investment summary in markdown.

## Sentiment Analysis Results
- Positive articles: {sentiment_summary.get('positive', 0)}
- Negative articles: {sentiment_summary.get('negative', 0)}
- Neutral articles: {sentiment_summary.get('neutral', 0)}
- Overall grade: {sentiment_summary.get('grade', 'N/A')}
- Average positive confidence: {sentiment_summary.get('average_positive_score', 0):.1%}
- Average negative confidence: {sentiment_summary.get('average_negative_score', 0):.1%}

## Sample Source Material
{sources_block}

## Instructions
Write a 3-section summary:
1. **Bull Case** — Key positive catalysts and drivers (2-3 bullet points)
2. **Bear Case** — Key risks and concerns (2-3 bullet points)
3. **Bottom Line** — One-paragraph verdict synthesizing both sides

Keep it professional, data-driven, and under 250 words total. Do not invent facts not present in the source material."""

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY not set — skipping AI summary for %s", ticker)
        return ""

    try:
        resp = requests.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
                "max_tokens": 600,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return (data["choices"][0]["message"]["content"] or "").strip()
    except Exception as e:
        # Log the real reason server-side but never surface a raw API error.
        logger.warning("Groq summary failed for %s: %s", ticker, e)
        return ""
