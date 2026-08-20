import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from db import run_sql_query, list_schema
from tools import SYSTEM_PROMPT

load_dotenv()

# Configure Google Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
MODEL_NAME = "gemini-3.5-flash-lite"




def ask_agent(question: str, history: list = None):
    messages = list(history) if history else []
    messages.append({"role": "user", "content": question})
    
    # State tracking for intermediate tool executions
    last_called = {"sql": None, "result": None}
    
    def run_sql_query_wrapper(sql: str, row_limit: int = 200):
        """Runs a read-only SELECT SQL query against the database 'gold' and 'silver' schemas.
        
        Args:
            sql: A single valid PostgreSQL SELECT query.
            row_limit: The maximum number of rows to return (default 200).
        """
        last_called["sql"] = sql
        res = run_sql_query(sql, row_limit)
        last_called["result"] = res
        return res
        
    def list_schema_wrapper():
        """Returns the list of all tables and columns available in the database schemas ('gold', 'silver')."""
        return list_schema()
        
    # Build model and register tools
    model = genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_PROMPT,
        tools=[run_sql_query_wrapper, list_schema_wrapper]
    )
    
    # Start chat with automatic function calling enabled
    chat = model.start_chat(enable_automatic_function_calling=True)
    
    # Construct combined prompt for context history
    prompt = ""
    if len(messages) > 1:
        prompt += "Conversation history:\n"
        for msg in messages[:-1]:
            content = msg.get("content")
            if isinstance(content, list):
                content = "[Tool Results]"
            prompt += f"- {msg['role'].upper()}: {content}\n"
        prompt += "\n"
    prompt += f"New Question: {question}"
    
    # Run the model
    response = chat.send_message(prompt)
    final_text = response.text
    
    # Append the assistant response to history
    messages.append({"role": "assistant", "content": final_text})
    
    return final_text, last_called["sql"], last_called["result"], messages
