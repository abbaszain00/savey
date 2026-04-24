import uuid
from dotenv import load_dotenv
from langchain_core.messages import AIMessage

from graph import savey
from database import authenticate_and_load_user

import logging
logging.getLogger("httpx").setLevel(logging.WARNING)

load_dotenv()


def chat():
    session_id = str(uuid.uuid4())
    user_data = authenticate_and_load_user("savey", "savey")[0]
    config = {"configurable": {"thread_id": session_id, "user_id": user_data["user_id"]}}
    savey.update_state(config, {"identity": user_data["identity"]})
    is_first_turn = True

    print(f"\n💾 Savey is ready! (session: {session_id[:8]}...)")
    print("Type 'exit' to quit, '/state' to see your expense summary.\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        if user_input.lower() == "exit":
            print("👋 Goodbye!")
            break

        if user_input.lower() == "/state":
            state = savey.get_state(config)
            if state and state.values:
                v = state.values
                print(f"\n📊 Current State:")
                print(f"   Total spent  : £{v.get('total_spent', 0.0)}")
                print(f"   Days tracked : {v.get('days_tracked', 0)}")
                print(f"   Expense log  : {v.get('expense_log', [])}")
                print()
            continue

        if is_first_turn:
            payload = {
                "messages": [{"role": "user", "content": user_input}],
                "expense_log": [],
                "total_spent": 0.0,
                "days_tracked": 0,
                "todo": [],
            }
            is_first_turn = False
        else:
            payload = {
                "messages": [{"role": "user", "content": user_input}]
            }

        result = savey.invoke(payload, config=config)

        last_ai = next(
            (m for m in reversed(result["messages"]) if isinstance(m, AIMessage)),
            None
        )

        if last_ai:
            print(f"\nSavey: {last_ai.content}\n")


if __name__ == "__main__":
    chat()