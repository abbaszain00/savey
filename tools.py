import re
import os
from datetime import date
from statistics import mode, StatisticsError
from mcp.server.fastmcp import FastMCP
from langchain_core.tools import tool

mcp = FastMCP("savey_tools")

MOCK_EXCHANGE_RATES = {
    "USD": 0.79,
    "EUR": 0.85,
    "JPY": 0.0053,
    "CAD": 0.58,
    "AUD": 0.51,
    "CHF": 0.89,
}


@tool()
def retrieve_total_expenses(text: str) -> str:
    """
    Parse a natural language expense message and return the total amount as a float.
    Handles GBP (£) and USD ($) amounts, including decimals (e.g. £4.50, $20.99).
    Returns 0.0 if no amounts are found.
    """
    matches = re.findall(r'[£$](\d+(?:\.\d+)?)', text)
    return str(round(sum(float(x) for x in matches), 2))


@tool
def retrieve_purchased_item(text: str) -> str:
    """
    Parse a natural language expense message and return the most frequently purchased item.
    If all items appear equally often, returns the last item mentioned.
    Returns 'unknown' if no items can be parsed.
    """
    matches = re.findall(r'[£$]\d+(?:\.\d+)?\s+(\w+)', text)
    if not matches:
        return "unknown"
    try:
        return mode(matches)
    except StatisticsError:
        return matches[-1]


@tool
def convert_to_gbp(amount: float, currency: str) -> str:
    """
    Convert a foreign currency amount to GBP.
    Use this whenever an expense is not already in GBP (£).
    Supported currencies: USD, EUR, JPY, CAD, AUD, CHF.
    Example: convert_to_gbp(20.0, 'USD') → '20.0 USD = £15.8 GBP'
    """
    currency = currency.upper()
    if currency not in MOCK_EXCHANGE_RATES:
        return f"Could not convert: Unrecognised currency code: {currency}. Please use one of: {', '.join(MOCK_EXCHANGE_RATES.keys())}"
    rate = MOCK_EXCHANGE_RATES[currency]
    converted = round(amount * rate, 2)
    return f"{amount} {currency} = £{converted} GBP"


@tool
def get_today_date() -> str:
    """
    Returns today's date as a human-readable string.
    Used by the duration sub-agent to resolve relative time references
    like 'yesterday', 'last Monday', or 'three days ago'.
    """
    return date.today().strftime("%A, %d %B %Y")


if __name__ == "__main__":
    mcp.run(transport="stdio")