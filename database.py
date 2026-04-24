import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from hash import *

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "34.39.82.3"),
    "port": os.getenv("DB_PORT", "5432"),
    "database": os.getenv("DB_NAME", "savey"),
    "user": os.getenv("DB_USER", "savey_user"),
    "password": os.getenv("DB_PASSWORD")
}


# --- Database Connection Helper ---
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


# --- Logic: Save/Update Session Summary ---
def save_session_memory(user_id: str, new_context_updates: dict):
    """
    Merges new discoveries into the context_json using the Postgres || operator.
    This ensures the most recent information takes precedence.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # The || operator merges two JSONB objects.
    # If a key exists in both, the right-side (new) value wins.
    sql = """
        UPDATE user_profiles 
        SET context_json = context_json || %s::jsonb 
        WHERE user_id = %s
    """

    cur.execute(sql, (json.dumps(new_context_updates), user_id))

    conn.commit()
    cur.close()
    conn.close()


def authenticate_and_load_user(username, provided_password):
    """
    Verifies credentials and returns the user's ID and Identity JSON.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # We fetch the hash, the user_id, and the identity_json at once
            sql = "SELECT user_id, password_hash, identity_json FROM user_profiles WHERE user_id = %s"
            cur.execute(sql, (username,))
            user_record = cur.fetchone()

            if not user_record:
                return None, "User not found."

            # Verify the password
            if verify_password(provided_password, user_record['password_hash']):
                return {
                    "user_id": user_record['user_id'],
                    "identity": user_record['identity_json']
                }, None
            else:
                return None, "Invalid password."
    finally:
        conn.close()


def register_new_user(username, password, display_name, primary_goal):
    """
    Creates a new user with an initial identity structure.
    """
    hashed_pw = hash_password(password)

    # Initial identity structure
    initial_identity = {
        "display_name": display_name,
        "primary_goal": primary_goal,
        "onboarding_completed": True
    }

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            sql = """
                INSERT INTO user_profiles (user_id, password_hash, identity_json)
                VALUES (%s, %s, %s)
                RETURNING user_id;
            """
            cur.execute(sql, (username, hashed_pw, json.dumps(initial_identity)))
            new_id = cur.fetchone()[0]
            conn.commit()
            return new_id
    except Exception as e:
        conn.rollback()
        print(f"Error during registration: {e}")
        return None
    finally:
        conn.close()

#register_new_user("savey", "savey", "Savey", "Saving for a new car (~£15,000)")
#print(authenticate_and_load_user("savey", "savey"))
