import os
import re
from fastapi import HTTPException
from dotenv import load_dotenv
import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from pydantic import BaseModel
from src.rule_onboarding.core import dq_rule_onboarding_orchestrator
import uvicorn
from src.rule_onboarding.utils.logger import setup_logger
from src.rule_onboarding.utils.gpu_monitor import get_gpu_status
from src.rule_onboarding.finetune.wrapper import RuleExtractionModelWrapper
#--- LOGGER SETUP ---
logger = setup_logger("DQ_RULE_ONBOARDING_API_SERVER")

# This looks for a .env file in the current directory or parents
load_dotenv() 

# ADK can find the key
api_key = os.getenv("GOOGLE_API_KEY")

app = FastAPI()

# Global variable to hold the model
model_wrapper = None

# This will create a 'sessions.db' file in project root
DB_URL = "sqlite:///sessions.db"

# Initialize the persistent service
session_service = DatabaseSessionService(db_url = DB_URL)

class ChatRequest(BaseModel):
    message: str
    session_id: str

async def dq_rule_onboarding_agent_streamer(user_message: str, session_id: str):

    # Check if session exists; if not, create it
    try:
        session = await session_service.get_session(session_id=session_id)
    except Exception:
        # If get_session fails or session doesn't exist, ONLY THEN create it
        session = None
    if not session:
        try:
            await session_service.create_session(
                app_name="dq_rule_onboarding_app",
                user_id="2323ad05035",
                session_id=session_id
            )
            logger.info(f"Created new session: {session_id}")
        except Exception as e:
            # Handle the case where it might have been created by a parallel request
            logger.warning(f"Session creation skipped or failed: {e}")
       
    # Initialize the Runner
    runner = Runner(
      agent = dq_rule_onboarding_orchestrator,
      app_name="dq_rule_onboarding_app",
      session_service = session_service
    )
    
    # Format message for ADK
    content = types.Content(role='user', parts=[types.Part(text=user_message)])
    
    # The run_async is used for real-time output
    # The Runner fetches history for 'session_id' and appends the new message
    # The run_async is the core of the multi-turn memory logic
    async for event in runner.run_async(session_id = session_id, user_id="2323ad05035", new_message = content):
        
        # Check for Validation Errors from RuleValidation Custom Agent
        if event.author == "rule_validation_agent":
            text_output = event.content.parts[0].text
            if "VALIDATION_ERROR" in text_output:
                yield text_output.replace("VALIDATION_ERROR: ", "❌ ")
                return  # Stop the stream and the pipeline here
        # Handle Text Chunks
        # We only stream 'partial' text chunks or the final text
        # Only yield text if it belongs to the deployment agent.
        if event.author == "rule_deployment_agent":
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        # In a streaming setup, yielding raw text is fine for st.write_stream
                        yield part.text
        
        # Tool Calls
        if event.get_function_calls():
            logger.info(f"Agent calling tools: {event.get_function_calls()}")
            
        await asyncio.sleep(0.01)
# --- THE GUARDRAIL ---
def validate_input_guardrail(prompt: str):
    """
    Blocks off-topic or malicious queries before they hit the GPU.
    """
    p_lower = prompt.lower()
    
    # 1. Topic Restriction (DQ Domain Only)
    # List keywords that MUST be present in some form for a valid DQ request
    dq_keywords = ["rule", "check", "dq", "data quality","onboard", "mean", "average","sum","record","count","context","stale","schema","baseline", "null", "unique", "column", "table", "threshold", "dataset", "repo"]
    if not any(word in p_lower for word in dq_keywords):
        raise HTTPException(
            status_code=400, 
            detail="OFF_TOPIC: DQ Rule Onboarding Genie only handles Data Quality Rule onboarding requests."
        )

    # 2. Prompt Injection Protection
    # Blocks attempts to hijack the model persona or leak instructions
    injection_patterns = [
        r"ignore (all )?previous instructions",
        r"you are now a",
        r"system prompt",
        r"verbatim",
        r"repeat the above",
        r"delete all",
        r"drop table" # Prevention of SQL-like injections if strings are used downstream
    ]
    for pattern in injection_patterns:
        if re.search(pattern, p_lower):
            raise HTTPException(
                status_code=403, 
                detail="SECURITY_VIOLATION: Malicious prompt pattern detected."
            )
    
    # 3. Length Constraint (VRAM Safety for GTX 1650)
    if len(prompt) > 500:
         raise HTTPException(
            status_code=400, 
            detail="INPUT_TOO_LONG: Please keep rule descriptions under 500 characters."
        )      
@app.post("/onboard-rule")
async def onboard_rule(request: ChatRequest):
    logger.info(f"Received onboarding request for session: {request.session_id}")
    logger.info(f"User Message: {request.message}")
    # Run guardrail first!
    validate_input_guardrail(request.message)
    return StreamingResponse(dq_rule_onboarding_agent_streamer(request.message, request.session_id), media_type="text/plain")

@app.get("/health/gpu")
async def health_check():
    status = get_gpu_status()
    # Logic to warn if VRAM is going low
    if status.get("free_mb", 1000) < 500:
        status["status"] = "CRITICAL - Low VRAM"
    else:
        status["status"] = "HEALTHY"
    return status
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8083)
