import os
import sys
import time
import webbrowser
import subprocess

# Define colors for terminal output
RESET = "\033[0m"
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
ORANGE = "\033[38;5;208m"

def main():
    print(f"{ORANGE}=================================================={RESET}")
    print(f"{GREEN}🚀 Starting FIFA World Cup Pipeline Local Server...{RESET}")
    print(f"{ORANGE}=================================================={RESET}")
    print(f"👉 {YELLOW}Chatbot Web UI{RESET}:  {CYAN}http://localhost:5501{RESET}")
    print(f"👉 {YELLOW}FastAPI Agent Docs{RESET}: {CYAN}http://localhost:8000/docs{RESET}")
    print(f"👉 {YELLOW}Airflow Portal{RESET}:     {CYAN}http://localhost:8080{RESET}")
    print(f"{ORANGE}=================================================={RESET}")
    print("\nStarting browser and web server...")
    
    # Wait half a second, then open the browser automatically
    time.sleep(0.5)
    try:
        webbrowser.open("http://localhost:5501")
    except Exception:
        pass
        
    # Start the HTTP server on port 5501 in the chatbot/frontend directory
    frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chatbot", "frontend")
    try:
        subprocess.run([sys.executable, "-m", "http.server", "5501"], cwd=frontend_dir)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Server stopped successfully.{RESET}")

if __name__ == '__main__':
    main()
