from google.adk.agents import SequentialAgent
from src.rule_onboarding.agents.rule_extraction import rule_extraction_agent
from src.rule_onboarding.agents.rule_validation import rule_validation_agent
from src.rule_onboarding.agents.rule_generation import rule_generation_agent
from src.rule_onboarding.agents.rule_deployment import rule_deployment_agent

dq_rule_onboarding_orchestrator = SequentialAgent(
    name="dq_rule_onboarding_orchestrator",
    sub_agents=[
        rule_extraction_agent,
        rule_validation_agent,
        rule_generation_agent,
        rule_deployment_agent
    ]
)