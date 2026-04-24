import os
import re
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from state import SaveyState
from tools import (
    retrieve_total_expenses,
    retrieve_purchased_item,
    convert_to_gbp,
    get_today_date,
)
from agents import ask_duration_agent

load_dotenv()

# ── Tool registry ─────────────────────────────────────────────────────────────

SAVEY_TOOLS = [
    retrieve_total_expenses,
    retrieve_purchased_item,
    ask_duration_agent,
    convert_to_gbp,
    get_today_date,
    # savings_recommendation will be added here once teammate implements the tool
]


# ── System prompt ─────────────────────────────────────────────────────────────

AGENT_SYSTEM_PROMPT = """You are Savey 💾 — a helpful, precise personal expense tracking assistant.

For every expense message, you MUST call these tools:
1. ask_duration_agent — always, no exceptions
2. retrieve_total_expenses — if the amount is in GBP (£)
3. convert_to_gbp — if the amount is in any other currency (USD, EUR etc.) — call get_today_date first to get the date
4. retrieve_purchased_item — if the user mentions buying a specific item

For non-expense messages (greetings, questions, advice requests) do NOT call expense tools.

Tool details:
- retrieve_total_expenses: GBP (£) amounts only, handles decimals and thousands separators
- retrieve_purchased_item: returns most commonly purchased item
- ask_duration_agent: returns number of distinct days the message spans
- get_today_date: returns today's date — use before convert_to_gbp to get the correct date in yyyy-mm-dd format
- convert_to_gbp: converts foreign currency to GBP using live rates — requires amount, currency, and date

General rules:
- For summaries or totals, read from the state below — do NOT recalculate
- If the message is ambiguous or incomplete, state that clearly

ADVICE MODE: If the user asks for 'advice', 'recommendations', or 'how they are doing', analyze their expense_log and provide 2 actionable savings tips. DO NOT offer further help — wait for the user to request it.

{state_context}"""


# ── Model ─────────────────────────────────────────────────────────────────────


def _make_model(temperature: float = 0.0):
    return init_chat_model(
        model="openai/gpt-4.1",
        model_provider="openai",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1",
        temperature=temperature,
    )


# ── Nodes ─────────────────────────────────────────────────────────────────────


def agent_node(state: SaveyState) -> dict:
    model = _make_model()
    model_with_tools = model.bind_tools(SAVEY_TOOLS)

    expense_log = state.get("expense_log", [])
    total_spent = state.get("total_spent", 0.0)
    days_tracked = state.get("days_tracked", 0)

    if expense_log:
        log_lines = "\n".join(
            f"  - {e.get('item', 'expense')}: £{e.get('amount_gbp', 0)}"
            for e in expense_log
        )
        state_context = (
            f"Current state:\n"
            f"- Total spent so far: £{total_spent}\n"
            f"- Days tracked: {days_tracked}\n"
            f"- Expense log:\n{log_lines}\n\n"
            f"If the user asks for totals or summaries, read from this state — do NOT recalculate."
        )
    else:
        state_context = "Current state: No expenses logged yet."

    system_message = SystemMessage(
        content=AGENT_SYSTEM_PROMPT.format(state_context=state_context)
    )

    response = model_with_tools.invoke([system_message] + state["messages"])
    return {"messages": [response]}


tool_node = ToolNode(SAVEY_TOOLS)


def update_state_node(state: SaveyState) -> dict:
    expense_log = list(state.get("expense_log", []))
    days_tracked = state.get("days_tracked", 0)

    messages = state["messages"]

    last_ai_idx = next(
        (
            i
            for i in reversed(range(len(messages)))
            if isinstance(messages[i], AIMessage) and messages[i].tool_calls
        ),
        None,
    )

    if last_ai_idx is None:
        return {}

    current_tool_messages = [
        m for m in messages[last_ai_idx + 1 :] if isinstance(m, ToolMessage)
    ]

    if not current_tool_messages:
        return {}

    tools_this_round = {m.name for m in current_tool_messages}
    currency_converted_this_round = "convert_to_gbp" in tools_this_round

    for msg in current_tool_messages:
        content = msg.content.strip()

        if msg.name == "convert_to_gbp":
            fx_match = re.search(r"= £([\d.]+) GBP", content)
            if fx_match:
                expense_log.append(
                    {
                        "item": "(foreign currency expense)",
                        "amount_gbp": float(fx_match.group(1)),
                    }
                )

        elif (
            msg.name == "retrieve_total_expenses" and not currency_converted_this_round
        ):
            try:
                amount_gbp = float(content)
                if amount_gbp > 0:
                    expense_log.append(
                        {"item": "(expenses from message)", "amount_gbp": amount_gbp}
                    )
            except (ValueError, TypeError):
                pass

        elif msg.name == "ask_duration_agent":
            try:
                new_days = int(content.strip())
                days_tracked += new_days
            except (ValueError, TypeError):
                pass

    total_spent = round(sum(e["amount_gbp"] for e in expense_log), 2)

    return {
        "expense_log": expense_log,
        "total_spent": total_spent,
        "days_tracked": days_tracked,
    }


def should_continue(state: SaveyState) -> str:
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return END


# ── Graph assembly ────────────────────────────────────────────────────────────


def build_savey_graph(checkpointer=None):
    if checkpointer is None:
        checkpointer = MemorySaver()

    builder = StateGraph(SaveyState)

    builder.add_node("agent", agent_node)
    builder.add_node("tools", tool_node)
    builder.add_node("update_state", update_state_node)

    builder.set_entry_point("agent")
    builder.add_conditional_edges("agent", should_continue)
    builder.add_edge("tools", "update_state")
    builder.add_edge("update_state", "agent")

    return builder.compile(checkpointer=checkpointer)


savey = build_savey_graph()
