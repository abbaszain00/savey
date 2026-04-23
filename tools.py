import re
import os
import requests
from datetime import date
from statistics import mode, StatisticsError
from langchain_core.tools import tool

@tool
def retrieve_total_expenses(text: str) -> str:
    """
    Parse a natural language expense message and return the total GBP amount.
    Handles GBP (£) amounts only, including decimals (e.g. £4.50).
    Use convert_to_gbp first for any non-GBP currency.
    Returns 0.0 if no amounts are found.
    """
    matches = re.findall(r"£(\d+(?:\.\d+)?)", text)
    return str(round(sum(float(x) for x in matches), 2))


@tool
def retrieve_purchased_item(text: str) -> str:
    """
    Parse a natural language expense message and return the most frequently purchased item.
    If all items appear equally often, returns the last item mentioned.
    Returns 'unknown' if no items can be parsed.
    """
    matches = re.findall(r"[£$]\d+(?:\.\d+)?\s+(\w+)", text)
    if not matches:
        return "unknown"
    try:
        return mode(matches)
    except StatisticsError:
        return matches[-1]


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
    Convert a foreign currency amount to GBP.
    Use this whenever an expense is not already in GBP (£).
    Supported currencies: USD, EUR, JPY, CAD, AUD, CHF.
    Example: convert_to_gbp(20.0, 'USD') → '20.0 USD = £15.8 GBP'
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

