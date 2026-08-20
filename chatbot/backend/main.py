import uuid
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import ask_agent
from db import log_chat_query

app = FastAPI(title="FIFA World Cup Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSIONS = {}

class ChatRequest(BaseModel):
    question: str
    session_id: str | None = None

@app.post("/chat")
def chat(req: ChatRequest):
    session_id = req.session_id or str(uuid.uuid4())
    history = SESSIONS.get(session_id, [])
    
    try:
        answer, sql_used, sql_result, updated_history = ask_agent(req.question, history)
        SESSIONS[session_id] = updated_history
        log_chat_query(session_id, req.question, sql_used, sql_result, answer, "SUCCESS")
        return {
            "session_id": session_id, 
            "answer": answer, 
            "sql_used": sql_used,
            "sql_result": sql_result
        }
    except Exception as e:
        log_chat_query(session_id, req.question, None, None, None, "FAILED", str(e))
        return {
            "session_id": session_id, 
            "answer": f"Something went wrong: {e}", 
            "sql_used": None,
            "sql_result": None
        }


@app.get("/stats")
def get_stats():
    from db import run_sql_query
    try:
        editions_res = run_sql_query("SELECT COUNT(*) as count FROM gold.dim_editions;")
        matches_res = run_sql_query("SELECT COUNT(*) as count FROM gold.fact_matches;")
        goals_res = run_sql_query("SELECT SUM(goals_count) as count FROM gold.dim_editions;")
        
        editions_count = editions_res.get("rows", [{}])[0].get("count", 24)
        matches_count = matches_res.get("rows", [{}])[0].get("count", 1004)
        goals_count = goals_res.get("rows", [{}])[0].get("count", 2984)
        
        return {
            "status": "success",
            "editions": editions_count,
            "matches": matches_count,
            "goals": goals_count
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "editions": 24,
            "matches": 1004,
            "goals": 2984
        }

@app.get("/health")
def health():
    return {"status": "ok"}

