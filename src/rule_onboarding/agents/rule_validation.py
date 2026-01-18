import json
from typing import AsyncGenerator
from unittest import result
from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.genai import types
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from src.rule_onboarding.utils.logger import setup_logger

# MCP Connection for repository lookups
mcp_params = StreamableHTTPConnectionParams(url="http://127.0.0.1:8082/mcp")

class DQRuleValidationCustomAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="rule_validation_agent")
        self._output_key = "validated_rule_details"
        self._logger = setup_logger("DQ_RULE_VALIDATION_AGENT")
        # Initialize toolset as a private attribute to avoid Pydantic issues
        self._mcp_toolset = McpToolset(connection_params=mcp_params)

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        raw_data = state.get("raw_rule_details", "")
        self._logger.info(f"Received raw data for validation: {raw_data}")

        try:
            # Parse Payload
            if isinstance(raw_data, str):
                if raw_data.startswith("```json") and raw_data.endswith("```"):
                    raw_data = raw_data[7:-3].strip()  # remove ```json and ```
                data = json.loads(raw_data)
            else:
                data = raw_data
            self._logger.info(f"Parsed data: {data}")
            # Repository Validation via MCP Tool
            repo_name = data.get("repository_name")
            self._logger.info(f"Validating repository: {repo_name}")
            if not repo_name:
                 async for event in self._yield_error(ctx, "VALIDATION_ERROR: Please provide the 'repository_name' for connectivity to be used."):
                    yield event
                 return
            # 1. Connectivity Lookup via MCP
            try:
                # Find and call the get_connectivity_id tool
                tool_name = "get_connectivity_id_by_repository_name"
                tools = await self._mcp_toolset.get_tools()
                tool = next((t for t in tools if t.name == tool_name), None)
                
                if not tool:
                    available = [t.name for t in tools]
                    self._logger.error(f"Tool '{tool_name}' not found. Available tools: {available}")
                    raise RuntimeError(f"Tool '{tool_name}' not found. Available tools: {available}")

                # 2. Call tool (Pass repository_name as a keyword arg in a dict)
                # Expected return: {"connectivity_id": "1"} or a 404 message
                
                tool_result = await tool.run_async(args={"repository_name": repo_name}, tool_context=ctx)
                self._logger.info(f"MCP Tool result: {tool_result}")
           
                # 3. Handle Errors (Check isError flag or 404 in content)
                if getattr(tool_result, "isError", False) or "404" in str(tool_result):
                    msg = f"VALIDATION_ERROR: Repository '{repo_name}' was not found as part of existing configuration."
                    async for event in self._yield_error(ctx, msg):
                        yield event
                    return

                # 4. Extract connectivity_id from structuredContent (Pydantic mapped)
                conn_id = None
                if hasattr(tool_result, 'structuredContent') and tool_result.structuredContent:
                    conn_id = tool_result.structuredContent.get("connectivity_id")
                if not conn_id:
                    msg = f"VALIDATION_ERROR: Could not retrieve Connectivity ID missing for repository '{repo_name}'."
                    async for event in self._yield_error(ctx, msg):
                        yield event
                    return

                # Update payload: Remove repo_name, Add connectivity_id
                data.pop("repository_name")
                data["connectivity_id"] = conn_id
                self._logger.info(f"Successfully mapped {repo_name} to {conn_id}")

            except Exception as e:
                 async for event in self._yield_error(ctx, f"VALIDATION_ERROR: MCP Connectivity lookup failed: {str(e)}"):
                    yield event
                 return

            # 3. Rule Attributes Validation
            attributes = data.get("attributes", [])
            for attr in attributes:
                rule_type = attr.get("rule_type", "").upper()
                baseline_source = attr.get("baseline_source", "").upper()
                details = attr.get("rule_details", {})
                baseline_val = float(details.get("baseline_value", 0))

                # Logic for STALE_COUNT / STALE_CONTEXT / RECORD_COUNT
                if rule_type in ["STALE_COUNT", "STALE_CONTEXT","RECORD_COUNT"]:
                    if baseline_source == "PREVIOUS" and baseline_val != 1.0:
                        msg = f"VALIDATION_ERROR: Rule {rule_type} with PREVIOUS baseline must have value 1.0."
                        async for event in self._yield_error(ctx, msg):
                            yield event
                        return

            # 4. Success - Save updated data (with connectivity_id)
            state[self._output_key] = data
            yield Event(
                author=self.name, 
                content=types.Content(role='assistant', parts=[types.Part(text="VALIDATION_SUCCESS")])
            )

        except Exception as e:
            msg = f"VALIDATION_ERROR: {str(e)}"
            async for event in self._yield_error(ctx, msg):
                yield event
            return

    async def _yield_error(self, ctx, msg:str) -> AsyncGenerator[Event, None]:
        self._logger.error(msg)
        ctx.session.state[self._output_key] = msg
        yield Event(
        author=self.name, 
        content=types.Content(role='assistant', parts=[types.Part(text=msg)])
    )

rule_validation_agent = DQRuleValidationCustomAgent()