import re
import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent

from tools import get_today_date

load_dotenv()


DURATION_SYSTEM_PROMPT = """You are a specialist in reading expense descriptions and identifying how many distinct calendar days they span.
Today's date is available through the get_today_date tool. Use it when resolving relative references such as "today", "yesterday", "last Monday", or "three days ago".

Rules:
* Count distinct calendar days, not purchases.
* Multiple expenses on the same day count as 1 day.
* If no explicit date or relative day is mentioned, assume the message covers 1 day.
* Return ONLY a single integer.
* Do not explain your answer."""

duration_model = init_chat_model(
    model="openai/gpt-4.1-mini",
    model_provider="openai",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    temperature=0.0
)

duration_agent = create_react_agent(
    duration_model,
    tools=[get_today_date],
    prompt=DURATION_SYSTEM_PROMPT,
)


@tool
def ask_duration_agent(text: str) -> str:
    """
    Delegate to the duration sub-agent to determine how many distinct calendar days
    a natural language expense description spans.
    Use this whenever the user asks about duration, number of days, or time period.

    Example input:  "Today I bought a £4 coffee. Yesterday I got a £8 sandwich."
    Example output: "2"
    """
    try:
        today = get_today_date.invoke({})
        result = duration_agent.invoke({
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Today's date is {today}.\n\n"
                        f"Expense description:\n{text}"
                    ),
                }
            ]
        })
        output = result["messages"][-1].content.strip()
        match = re.search(r"\d+", output)
        if not match:
            return "1"
        return match.group(0)
    except Exception:
        return "1"