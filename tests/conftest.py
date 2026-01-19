import pytest
from unittest.mock import AsyncMock, MagicMock
from google.adk.tools.mcp_tool import McpToolset

@pytest.fixture
def mock_mcp_toolset(monkeypatch):
    """
    Mocks the McpToolset to simulate MCP server responses 
    without network calls or a running database.
    """
    mock_toolset = MagicMock(spec=McpToolset)
    
    # 1. Create a Mock Tool object
    mock_tool = AsyncMock()
    mock_tool.name = "get_connectivity_id_by_repository_name"
    
    # 2. Define the tool's run_async behavior
    async def side_effect(args, tool_context):
        repo_name = args.get("repository_name")
        
        # Simulate a 404 for a specific name
        if repo_name == "NonExistentRepo":
            # Mocking the ADK result object structure
            result = MagicMock()
            result.isError = True
            result.content = [MagicMock(text='{"detail": "Not Found"}')]
            return result
            
        # Simulate success for any other name
        success_result = MagicMock()
        success_result.isError = False
        success_result.structuredContent = {"connectivity_id": "mock-uuid-123"}
        return success_result

    mock_tool.run_async.side_effect = side_effect

    # 3. Mock get_tools to return our mock tool
    mock_toolset.get_tools = AsyncMock(return_value=[mock_tool])
    
    # 4. Patch the toolset inside your agent module
    # Adjust the path to where your agent is defined
    monkeypatch.setattr("src.rule_onboarding.agents.custom_validation.McpToolset", lambda **k: mock_toolset)
    
    return mock_toolset