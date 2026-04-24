from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages


class SaveyState(TypedDict):
    messages: Annotated[list, add_messages]
    expense_log: list        # [{"item": str, "amount_gbp": float}]
    total_spent: float       # always recomputed from expense_log
    days_tracked: int        # cumulative across turns
    identity: dict           #
