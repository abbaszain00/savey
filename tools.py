import re
import os
import requests
from datetime import date
from statistics import StatisticsError
from collections import Counter
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from database import get_db_connection


ITEM_STOPWORDS = {
    "and", "or", "but", "then", "also", "today", "yesterday",
    "only", "just", "a", "an", "the",
}

CONNECTORS = {
    "and", "or", "but", "then", "also",
}


@tool
def retrieve_total_expenses(text: str) -> float:
    """
    Parse a natural language expense message and return the total GBP amount.
    Only handles GBP (£) amounts. Use convert_to_gbp first for other currencies.
    Example input: 'Today I bought a £4 coffee and a £8 sandwich.'
    """
    pattern = r"""
        £                     # GBP symbol only
        \s*                   # optional whitespace
        (                     # capture numeric amount
            (?:
               \d{1,3}(?:,\d{3})+  # numbers with thousands separators
                |\d+                # plain numbers
            )
            (?:\.\d+)?        # optional decimal part
            |
            \.\d+             # amounts like £.99
        )
    """
    matches = re.findall(pattern, text, flags=re.VERBOSE)
    return sum(float(x.replace(",", "")) for x in matches)


@tool
def retrieve_purchased_item(text: str) -> str:
    """
    Parse a natural language expense message and return the most commonly purchased item.
    Example input: 'Today I bought a £4 coffee and a £8 sandwich. Yesterday I only got a £4 coffee.'
    """
    pattern = r"""
        [£$]\s*
        (?:
            (?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?
            |
            \.\d+
        )
        \s+
        ([A-Za-z][A-Za-z'-]*(?:\s+[A-Za-z][A-Za-z'-]*){0,2})
    """
    raw_matches = re.findall(pattern, text, flags=re.VERBOSE)
    items = []
    for match in raw_matches:
        words = []
        for word in match.lower().split():
            cleaned = word.strip(".,!?;:")
            if cleaned in CONNECTORS:
                break
            if cleaned not in ITEM_STOPWORDS:
                words.append(cleaned)
        if words:
            items.append(" ".join(words))

    if not items:
        return "unknown"

    return Counter(items).most_common(1)[0][0]


def _fetch_rate(currency: str, date: str) -> float:
    """Calls Frankfurter API to collect most recent exchange rates to GBP."""
    frankfurter_url = f"https://api.frankfurter.dev/v2/rates?base={currency}&quotes=GBP"
    if date:
        frankfurter_url += f"&date={date}"
    response = requests.get(frankfurter_url)
    data = response.json()
    if "status" in data:
        raise ValueError(data["message"])
    return data[0]["rate"]


@tool
def convert_to_gbp(amount: float, currency: str, date: str) -> str:
    """
    Convert a foreign currency amount to GBP using live exchange rates.
    Use this whenever an expense is not already in GBP (£).
    Example: convert_to_gbp(20.0, 'USD', '2026-04-23') → '20.0 USD = £14.81 GBP'
    """
    try:
        rate = _fetch_rate(currency, date)
        converted = round(amount * rate, 2)
        return f"{amount} {currency.upper()} = £{converted} GBP"
    except ValueError as e:
        return f"Could not convert: {e}"


@tool
def get_today_date() -> str:
    """
    Returns today's date as a human-readable string.
    Used by the duration sub-agent to resolve relative time references
    like 'yesterday', 'last Monday', or 'three days ago'.
    """
    return date.today().strftime("%A, %d %B %Y")


@tool
def query_user_history(query_key: str, config: RunnableConfig):
    """
    Look up specific past information or preferences from long-term memory.
    Use this if you encounter a merchant, goal, or preference you don't recognize.
    """
    # Extract the user_id from the config (passed by the backend, not the LLM)
    user_id = config.get("configurable", {}).get("user_id")

    conn = get_db_connection()
    cur = conn.cursor()

    # We use the ->> operator to find specific keys in the context_json
    # Or a more general search if needed.
    sql = "SELECT context_json->>%s FROM users WHERE id = %s"

    cur.execute(sql, (query_key, user_id))
    result = cur.fetchone()

    cur.close()
    conn.close()

    if result and result[0]:
        return f"Context found for {query_key}: {result[0]}"
    return f"No prior context found for {query_key}."