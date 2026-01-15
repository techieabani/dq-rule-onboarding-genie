from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams

params = StreamableHTTPConnectionParams(url="http://127.0.0.1:8086/mcp")

rule_deployment_agent = Agent(
    name="rule_deployment_agent",
    model="gemini-3-flash-preview",
    instruction="""
    Using the payload: {configure_rule_json_payload}, call the 'onboard_rule' tool.
    Once the tool returns success, provide a concise confirmation to the user.
    Do NOT repeat the JSON payload in your text response.
    """,
    tools=[McpToolset(connection_params=params)]
)