import os
from dotenv import load_dotenv
import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel
from src.rule_onboarding.core.dq_rule_onboarding_orchestrator import dq_rule_onboarding_orchestrator
import uvicorn

# This looks for a .env file in the current directory or parents
load_dotenv() 

# Now the ADK can find the key
api_key = os.getenv("GOOGLE_API_KEY")

app = FastAPI()

# Initialize Persistence: Persistent in-memory store (lives as long as the API is up)
session_service = InMemorySessionService()

class ChatRequest(BaseModel):
    message: str
    session_id: str

async def dq_rule_onboarding_agent_streamer(user_message: str, session_id: str):

    # 1. Check if session exists; if not, create it
    try:
        # Some versions of ADK have a 'get_session' method
        await session_service.get_session(session_id)
    except Exception:
        # Create the session if it's missing
        await session_service.create_session(
            app_name="dq_rule_onboarding_app",
            user_id="2323ad05035",
            session_id=session_id
        )
    # Initialize the Runner
    runner = Runner(
      agent = dq_rule_onboarding_orchestrator,
      app_name="dq_rule_onboarding_app",
      session_service = session_service
    )
    
    # Format message for ADK
    content = types.Content(role='user', parts=[types.Part(text=user_message)])
    
    # Use run_async for real-time output
    # The Runner fetches history for 'session_id' and appends the new message
    # The run_async is the core of the multi-turn memory logic
    async for event in runner.run_async(session_id = session_id, user_id="2323ad05035", new_message = content):
        
        # Handle Text Chunks
        # We only stream 'partial' text chunks or the final text
        # Only yield text if it belongs to the deployment agent.
        if event.author == "rule_deployment_agent":
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        # In a streaming setup, yielding raw text is fine for st.write_stream
                        yield part.text
        
        # API console for debugging/logging without showing the user.
        else:
            print(f"Skipping intermediate output from: {event.author}")

        # 2. Optional: Log Tool Calls (Great for debugging)
        if event.get_function_calls():
            print(f"DEBUG: Agent calling tools: {event.get_function_calls()}")
            
        await asyncio.sleep(0.01)
@app.post("/onboard-rule")
async def onboard_rule(request: ChatRequest):
    # result = await dq_rule_onboarding_orchestrator.run_async(request.message)
    # return {"status": "success", "response": result.content.text}
    # Using 'text/plain' works for simple HTTP streaming. 
    # For a browser-based frontend, 'text/event-stream' is more standard.
    return StreamingResponse(dq_rule_onboarding_agent_streamer(request.message, request.session_id), media_type="text/plain")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8085)
