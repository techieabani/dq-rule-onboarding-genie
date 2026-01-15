import pytest
from rule_onboarding.core.dq_rule_onboarding_orchestrator import dq_rule_onboarding_orchestrator

@pytest.mark.asyncio
async def test_sequential_flow():
    # Mock user input
    user_input = "Set a MEAN_VARIANCE check for sales table"
    result = await dq_rule_onboarding_orchestrator.run_async(user_input)
    assert result is not None
    # Add logic to check if validation agent forced baseline to 1.0