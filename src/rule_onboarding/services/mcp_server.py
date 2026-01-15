from fastmcp import FastMCP
from pydantic import BaseModel
import httpx

mcp = FastMCP("Rule Onboarding MCP Server")

RULE_ONBOARDING_API_URL = "http://localhost:8081/configure-rule"

class OnboardRuleRequest(BaseModel):
    rule_name: str
    db_name: str
    dataset_name: str
    column_name: str
    rule_type: str
    baseline_value: float
    threshold_value: float

@mcp.tool()
async def onboard_rule(
    request: OnboardRuleRequest
) -> str:
    """
    Deploy a data quality rule using the Rule Onboarding API.
    """

    async with httpx.AsyncClient() as client:
        response = await client.post(RULE_ONBOARDING_API_URL, json=request.dict())
        response.raise_for_status()
        result = response.json()

    return result["message"]

if __name__ == "__main__":
    mcp.run(transport="http", port=8086, host="127.0.0.1")