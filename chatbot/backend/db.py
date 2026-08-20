import os
import psycopg2
import psycopg2.extras
from datetime import date, datetime
from decimal import Decimal
from dotenv import load_dotenv


load_dotenv()

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": os.environ.get("DB_PORT", "5432"),
    "database": os.environ.get("DB_NAME", "fifa_dw"),
    "user": os.environ.get("DB_USER", "chatbot_readonly"),
    "password": os.environ.get("DB_PASSWORD", "chatbot_readonly_pw"),
}

FORBIDDEN_KEYWORDS = [
    "insert", "update", "delete", "drop", "alter", "truncate",
    "grant", "revoke", "create", "commit", "rollback", "--", ";--"
]

def get_connection():
    conn = psycopg2.connect(**DB_CONFIG, connect_timeout=5)
    conn.set_client_encoding('UTF8')
    return conn

def run_sql_query(sql: str, row_limit: int = 200):
    clean_sql = sql.strip().rstrip(";")
    lowered = clean_sql.lower()
    
    if not lowered.startswith("select") and not lowered.startswith("with"):
        return {"error": "Only SELECT queries are allowed."}
        
    for word in FORBIDDEN_KEYWORDS:
        if word in lowered:
            return {"error": f"Query contains a forbidden keyword: '{word}'."}
            
    conn = None
    try:
        conn = get_connection()
        conn.set_session(readonly=True, autocommit=True)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SET statement_timeout = 5000;")
        cur.execute(f"{clean_sql} LIMIT {row_limit};")
        rows = cur.fetchall()
        cur.close()
        serializable_rows = []
        for r in rows:
            clean_row = {}
            for k, v in dict(r).items():
                if isinstance(v, (date, datetime)):
                    clean_row[k] = v.isoformat()
                elif isinstance(v, Decimal):
                    clean_row[k] = float(v)
                else:
                    clean_row[k] = v
            serializable_rows.append(clean_row)
        return {"rows": serializable_rows, "row_count": len(rows)}

    except Exception as e:
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()

def list_schema():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT table_schema, table_name, column_name, data_type
            FROM information_schema.columns
            WHERE table_schema IN ('gold', 'silver')
            ORDER BY table_schema, table_name, ordinal_position;
            """
        )
        rows = cur.fetchall()
        cur.close()
        schema = {}
        for schema_name, table, col, dtype in rows:
            key = f"{schema_name}.{table}"
            schema.setdefault(key, []).append(f"{col} ({dtype})")
        return schema
    except Exception as e:
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()

def log_chat_query(session_id, question, sql, result, answer, status, error_msg=None):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO metadata.chat_queries
            (session_id, user_question, generated_sql, sql_result,
            final_answer, status, error_message)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
            """,
            (session_id, question, sql, psycopg2.extras.Json(result) if result else None, answer, status, error_msg)
        )
        conn.commit()
        cur.close()
    except Exception as e:
        print(f"Failed to log chat query: {e}")
    finally:
        if conn:
            conn.close()
