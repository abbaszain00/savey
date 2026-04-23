# Savey 💾

A stateful personal expense tracking agent built with LangGraph.

## Setup

1. Clone the repo
2. Create a virtual environment:
    ```bash
    python -m venv venv
    venv\Scripts\activate  # Windows
    source venv/bin/activate  # Mac/Linux
    ```
3. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4. Create a `.env` file:
    ```
    OPENROUTER_API_KEY=sk-or-your-key-here
    ```

## Run

```bash
python main.py
```

Type `/state` at any point to see your current expense summary.
Type `exit` to end the session.

## File Structure

```
savey/
├── state.py        # SaveyState definition
├── tools.py        # Core tools (retrieve_total_expenses, retrieve_purchased_item, convert_to_gbp)
├── agents.py       # Duration sub-agent
├── graph.py        # StateGraph — nodes, edges, system prompt
├── main.py         # Continuous chat interface
└── requirements.txt
```

## Architecture

```
START
  ↓
agent_node  (LLM — decides which tool to call)
  ↓
should_continue?
  ├── tool_call → tool_node → update_state_node → agent_node (loop)
  └── END
```

### Tools

| Tool | Description | Fixed in v4 |
|------|-------------|-------------|
| `retrieve_total_expenses` | Parses GBP/USD amounts from text | Decimal fix (£4.50) |
| `retrieve_purchased_item` | Identifies most purchased item | `mode()` crash fix |
| `convert_to_gbp` | Converts foreign currency to GBP | Mock rates (live API — see below) |
| `ask_duration_agent` | Determines how many days a description spans | `days_tracked` accumulation fix |

### Bug fixes from v3

- `retrieve_total_expenses` — regex `(\d+)` missed decimals like `£4.50`. Fixed to `(\d+(?:\.\d+)?)`
- `retrieve_purchased_item` — `statistics.mode()` crashed when all items appeared equally. Added `StatisticsError` fallback
- `days_tracked` — was overwriting instead of accumulating across turns. Fixed to `+=`
- Double-count guard — was checking for old `convert_to_gbp` tool name, updated correctly

## Placeholders for teammates

- `savings_recommendation` tool — to be added to `SAVEY_TOOLS` in `graph.py` (Sam)
- Live currency API — replace `MOCK_EXCHANGE_RATES` in `tools.py` (currency team)
- Long-term memory — to be integrated alongside `MemorySaver` in `graph.py` (memory team)

## Models

| Component | Model | Why |
|-----------|-------|-----|
| Main agent | `gpt-4.1-mini` | Complex reasoning, tool selection |
| Duration sub-agent | `gpt-4.1-mini` | Simple task, just counting days |

All models route via OpenRouter. To upgrade the main agent for production, change `SAVEY_MODEL` in `graph.py`.

## Memory

- **Short-term** — `MemorySaver` keeps state alive across turns within a session. Restarting `main.py` clears it.
- **Long-term** — to be implemented by the memory team using a persistent database.
