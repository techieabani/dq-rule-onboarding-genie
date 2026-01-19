import os
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

#--- LOGGER SETUP ---
logger = setup_logger("DQ_RULE_ONBOARDING_API_SERVER")

# This looks for a .env file in the current directory or parents
load_dotenv() 

# ADK can find the key
api_key = os.getenv("GOOGLE_API_KEY")

app = FastAPI()

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
        
@app.post("/onboard-rule")
async def onboard_rule(request: ChatRequest):
    logger.info(f"Received onboarding request for session: {request.session_id}")
    return StreamingResponse(dq_rule_onboarding_agent_streamer(request.message, request.session_id), media_type="text/plain")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8083)
