from google.adk.agents import Agent

rule_validation_agent = Agent(
    name="rule_validation_agent",
    model="gemini-3-flash-preview",
    instruction="""
    Validate the rule details from {raw_rule_details}.
    BUSINESS RULE: If rule_type is 'MEAN_VARIANCE', the baseline_value MUST be 1.0.
    Output the final validated parameters as a clean string.
    """,
    output_key="validated_rule_details"
)