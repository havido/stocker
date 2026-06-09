"""
Gemini AI summarizer.

Uses Google Gemini 2.0 Flash to generate an investment summary
given the ticker, scraped texts, and FinBERT sentiment analysis.
"""

import logging
import os
import google.generativeai as genai

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    """Lazy-load the Gemini model."""
    global _model
    if _model is None:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        _model = genai.GenerativeModel("gemini-2.0-flash")
    return _model


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
        Markdown-formatted investment summary string.
    """
    if log_callback:
        log_callback(f'{{"step": "gemini", "message": "Generating AI investment summary..."}}')

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

    try:
        model = _get_model()
        response = model.generate_content(prompt)
        # Empty response (or any failure below) → return "" so the frontend
        # cleanly hides the AI summary panel instead of rendering a raw error.
        return response.text or ""
    except Exception as e:
        # Log the real reason server-side (e.g. a 429 quota error) but never
        # surface the raw API error to users.
        logger.warning("Gemini summary failed for %s: %s", ticker, e)
        return ""
