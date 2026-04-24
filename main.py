import uuid
import logging
from dotenv import load_dotenv
from langchain_core.messages import AIMessage

from graph import savey

load_dotenv()
logging.getLogger("httpx").setLevel(logging.WARNING)


def login() -> str:
    """
    Placeholder login function.
    Returns a user_id string.
    When the memory team pushes their branch, replace this with their auth function.
    """
    print("\n💾 Welcome to Savey!")
    username = input("Username: ").strip()
    password = input("Password: ").strip()

    # TODO: replace with memory team's auth function
    # from memory import authenticate
    # user_id = authenticate(username, password)
    
    # For now, use username as user_id
    user_id = username
    return user_id


def chat():
    user_id = login()
    if not user_id:
        print("Login failed.")
        return

    config = {"configurable": {"thread_id": user_id}}
    is_first_turn = True

    print(f"\nHello, {user_id}! Type 'exit' to quit, '/state' to see your expense summary.\n")

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