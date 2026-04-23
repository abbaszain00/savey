import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain.chat_models import init_chat_model
from langgraph.prebuilt import create_react_agent

from tools import get_today_date

load_dotenv()


# ── Duration sub-agent ────────────────────────────────────────────────────────

DURATION_SYSTEM_PROMPT = """You are a specialist in reading expense descriptions and
identifying how many distinct days they span.
You have access to a tool that returns today's date — use it to resolve relative
references like 'last Monday' or 'three days ago'.
Return ONLY a single integer — the number of days. Do not explain your answer."""

_duration_model = init_chat_model(
    model="openai/gpt-4.1-mini",
    model_provider="openai",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    temperature=0.0
)

duration_agent = create_react_agent(
    _duration_model,
    tools=[get_today_date],
    prompt=DURATION_SYSTEM_PROMPT
)


@tool
def ask_duration_agent(text: str) -> str:
    """
    Delegate to the duration sub-agent to determine how many distinct days
    a natural language expense description spans.
    Use this whenever the user mentions multiple days or relative time references
    like 'yesterday' or 'last week'.

    Example input:  "Today I bought a £4 coffee. Yesterday I got a £8 sandwich."
    Example output: "2"
    """
    result = duration_agent.invoke(
        {"messages": [{"role": "user", "content": text}]}
    )
    return result["messages"][-1].content