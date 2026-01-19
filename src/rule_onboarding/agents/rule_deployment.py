from typing import AsyncGenerator
import google.genai.types as types
from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from src.rule_onboarding.utils.logger import setup_logger

# Define connection params
mcp_params = StreamableHTTPConnectionParams(url="http://127.0.0.1:8082/mcp")

class DQRuleDeploymentCustomAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="rule_deployment_agent")
        self._logger = setup_logger("DQ_RULE_DEPLOYMENT_AGENT")
        self._mcp_toolset = McpToolset(connection_params=mcp_params)
        self._output_key = "deployment_status"

    # _run_async_impl is for BaseAgent inheritance
    async def _run_async_impl(self, context) -> AsyncGenerator[Event, None]:
        # 1. Retrieve data from shared state
        validation_output = context.session.state.get("validated_rule_details", "")
        # Ensure this key matches exactly what the Generation Agent saved!
        payload = context.session.state.get("configure_rule_request_payload", None)
        
        self._logger.info(f"Deployment Agent retrieved payload: {payload}")

        # 2. Halt if validation failed
        if isinstance(validation_output, str) and "VALIDATION_ERROR" in validation_output:
            self._logger.info(f"{self.name} aborted deployment due to validation error.")
            return

        if payload:
            try:
                # 3. Access the MCP tool
                tools = await self._mcp_toolset.get_tools() 
                tool = next((t for t in tools if t.name == "onboard_rule"), None) 
                
                if not tool: 
                    raise RuntimeError("Tool 'onboard_rule' not found in MCP server") 

                # 4. Execute the tool call
                # Note: passing 'input=payload' and 'tool_context=context'
                result = await tool.run_async(args=payload, tool_context=context) 
                self._logger.info(f"DEBUG: MCP Tool Result: {result}")
                # Check if the result returned an error from the MCP side
                if getattr(result, "isError", False):
                    # Extract the error text from the content array
                    error_detail = result.content[0].text if result.content else "Unknown error"
                    self._logger.error(f"MCP Validation Error: {error_detail}")
                    raise RuntimeError("Data validation failed at MCP layer. Check logs for details.")
                # 5. Success Logic
                success_msg = f"✅ Success! Rule '{payload.get('rule_name')}' has been onboarded."
                context.session.state[self._output_key] = success_msg
                
                yield Event(
                    author=self.name, 
                    content=types.Content(role='assistant', parts=[types.Part(text=success_msg)])
                )
                
            except Exception as e:
                error_msg = f"❌ Deployment failed: {str(e)}"
                self._logger.error(f"Error detail: {e}")
                yield Event(
                    author=self.name, 
                    content=types.Content(role='assistant', parts=[types.Part(text=error_msg)])
                )
        else:
            yield Event(
                author=self.name, 
                content=types.Content(role='assistant', parts=[types.Part(text="⚠️ Deployment skipped: No valid rule payload found.")])
            )

# Instantiate for use in orchestrator
rule_deployment_agent = DQRuleDeploymentCustomAgent()