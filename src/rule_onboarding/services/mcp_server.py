from fastmcp import FastMCP
from pydantic import BaseModel
import httpx
from src.rule_onboarding.utils.logger import setup_logger
from fastapi import HTTPException

#--- LOGGER SETUP ---
logger = setup_logger("DQ_RULE_ONBOARDING_MCP_SERVER")

#--- MCP SERVER SETUP ---
mcp = FastMCP("Rule Onboarding MCP Server")

# --- API URLs ---
RULE_ONBOARDING_API_URL = "http://127.0.0.1:8081/api/dq/config/v1/rules"
CONNECTIVITY_API_BASE_URL = "http://127.0.0.1:8081/api/dq/config/v1/repositories"

# -------------------------
# Models
# -------------------------

class AttributeRuleInfo(BaseModel):
    baseline_value: float
    threshold_value: float
    
class AttributeInfo(BaseModel):
    column_name: str
    rule_type: str
    baseline_source: str
    rule_details: AttributeRuleInfo
    
class OnboardRuleRequest(BaseModel):
    rule_name: str
    db_name: str
    dataset_name: str
    connectivity_id: str
    attributes: list[AttributeInfo]

class ConnectivityResponse(BaseModel):
    connectivity_id: str

# -------------------------
# MCP Tool: Rule Onboarding
# -------------------------
@mcp.tool()
async def onboard_rule(
    rule_name: str,
    db_name: str,
    dataset_name: str,
    connectivity_id: str,
    attributes: list[AttributeInfo]
) -> str:
    """
    Deploy a data quality rule using the Rule Onboarding API.
    """
    request = OnboardRuleRequest(
        rule_name=rule_name,
        db_name=db_name,
        dataset_name=dataset_name,
        connectivity_id=connectivity_id,
        attributes=attributes
    )
    logger.info(f"Attempting to onboard rule: {request}")

    async with httpx.AsyncClient() as client:
        response = await client.post(RULE_ONBOARDING_API_URL, json=request.dict())
        response.raise_for_status()
        result = response.json()
    logger.info(f"Rule onboarded successfully: {result}")
    return result["message"]


# ----------------------------------------
# MCP Tool: Repository Connectivity Lookup
# ----------------------------------------
@mcp.tool()
async def get_connectivity_id_by_repository_name(repository_name: str) -> ConnectivityResponse:
    """
    Get connectivity id for a given repository name.
    """

    url = f"{CONNECTIVITY_API_BASE_URL}/{repository_name}/connectivity"
    logger.info(f"Fetching connectivity for repo: {repository_name}")

    async with httpx.AsyncClient() as client:
        response = await client.get(url)

        # Success Scenario
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Connectivity found: {data}")
            return ConnectivityResponse(**data)

        # Repo not found
        if response.status_code == 404:
            error = response.json()
            logger.error(f"Repository not found: {repository_name}")
            raise HTTPException(
                status_code=404,
                detail=error.get("detail", "Repository not found")
            )

        # Unexpected error
        logger.error(
            f"Unexpected error {response.status_code}: {response.text}"
        )
        response.raise_for_status()
        
if __name__ == "__main__":
    mcp.run(transport="http", port=8082, host="127.0.0.1")