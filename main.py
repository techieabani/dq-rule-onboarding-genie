import multiprocessing
import subprocess
import time
from src.rule_onboarding.utils.logger import setup_logger

# --- CONFIGURATION ---
MCP_PORT = 8082
BACKEND_PORT = 8083
UI_PORT = 8084

logger = setup_logger("DQ_RULE_ONBOARDING_GENIE_LAUNCHER")

# 1. To run MCP Server
def run_mcp_server():
    logger.info(f"[MCP] Starting on port {MCP_PORT}...")
    subprocess.run(["uv", "run", "python", "-m", "src.rule_onboarding.services.mcp_server"])

# 2. To run the FastAPI Backend
def run_fastapi():
    logger.info(f"[API] Starting on port {BACKEND_PORT}...")
    cmd = [
        "uv", "run", "python", "-m", "uvicorn", 
        "src.rule_onboarding.api.backend:app", 
        "--env-file", ".env", 
        "--host", "127.0.0.1", 
        "--port", str(BACKEND_PORT)
    ]
    subprocess.run(cmd)

# 3. To run the Streamlit UI
def run_streamlit():
    logger.info(f"[UI] Starting on port {UI_PORT}...")
    cmd = [
        "uv", "run", "python", "-m", "streamlit", "run", 
        "src/rule_onboarding/ui/app.py", 
        "--server.port", str(UI_PORT)
    ]
    subprocess.run(cmd)

if __name__ == "__main__":
  
    # Create processes
    mcp_p = multiprocessing.Process(target=run_mcp_server)
    api_p = multiprocessing.Process(target=run_fastapi)
    ui_p = multiprocessing.Process(target=run_streamlit)

    try:
        # Sequence: Tools -> Backend -> Frontend
        mcp_p.start()
        time.sleep(2) 
        
        api_p.start()
        time.sleep(3)
        
        ui_p.start()

        logger.info("\n DQ RULE ONBOARDING GENIE IS FULLY OPERATIONAL")
        logger.info(f"Access the UI at: http://localhost:{UI_PORT}")
        
        # Keep main process alive
        api_p.join() 

    except KeyboardInterrupt:
        logger.info("\n Shutting down DQ RULE ONBOARDING GENIE...")
        ui_p.terminate()
        api_p.terminate()
        mcp_p.terminate()
        logger.info("Shutdown complete.")