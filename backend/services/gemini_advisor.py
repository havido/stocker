"""
Gemini-powered investment advisor service.

Takes sentiment analysis results and stock data, then uses Google's Gemini
to produce an educated investment recommendation.
"""

import os
import json
from google import genai
from dotenv import load_dotenv

load_dotenv()

SYSTEM_PROMPT = (
    "You are a financial analyst. Based on the sentiment analysis of a stock, "
    "give an educated recommendation on whether it's a wise decision to "
    "purchase this stock and how much the user should invest."
)


def get_investment_advice(sentiment_data: dict) -> dict:
    """
    Call Gemini with the sentiment analysis results to get an
    investment recommendation.

    Args:
        sentiment_data: JSON output from the sentiment-analysis service.

    Returns:
        dict with a single key ``recommendation`` containing the Gemini response.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in environment variables")

    client = genai.Client(api_key=api_key)

    user_message = (
        f"Here is the sentiment analysis for the stock:\n"
        f"```json\n{json.dumps(sentiment_data, indent=2)}\n```\n\n"
        f"Based on this information, provide your investment recommendation."
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=SYSTEM_PROMPT + "\n\n" + user_message,
    )

    return {"recommendation": response.text}
