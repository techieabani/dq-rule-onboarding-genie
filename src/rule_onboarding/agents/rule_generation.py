import json
from google.adk.agents import BaseAgent
from google.adk.events import Event
from typing import AsyncGenerator
from google.genai import types
from src.rule_onboarding.utils.logger import setup_logger

class DQRuleGenerationCustomAgent(BaseAgent):

    def __init__(self):
        super().__init__(
            name="rule_generation_agent",
        )
        self._output_key = "configure_rule_request_payload"
        self._logger = setup_logger("DQ_RULE_GENERATION_AGENT")

    async def _run_async_impl(self, context)-> AsyncGenerator[Event, None]:
        
        """
        Overrides the ADK base implementation to transform validated data 
        into the final REST API JSON structure.
        """
        state = context.session.state
        # Retrieve the output from the Rule Validation Agent
        validated_data = state.get("validated_rule_details", "")

        # If it contains a validation error, output nothing and stop
        if not validated_data or isinstance(validated_data, str):
            # We yield nothing here. The pipeline effectively halts for the UI.
           self._logger.warning("Generation skipped: No validated data found.")
           return 

        # Convert validated data into the REST API JSON format
        try:
            self._logger.info(f"Generating final payload for: {validated_data.get('rule_name')}")
            # If data is already a dict (passed by Custom Validation Agent), use it directly
            # Otherwise, try to parse it if it's a string
            validated_rule_data = validated_data if isinstance(validated_data, dict) else json.loads(validated_data)
            
            # Construct the final JSON payload based on your examples
            final_json_payload = {
                "rule_name": validated_rule_data.get("rule_name"),
                "db_name": validated_rule_data.get("db_name"),
                "dataset_name": validated_rule_data.get("dataset_name"),
                "connectivity_id": validated_rule_data.get("connectivity_id"),
                "attributes": validated_rule_data.get("attributes", [])
            }

            # Save the final JSON to state so the Deployment Agent can use it
            state[self._output_key] = final_json_payload
            self._logger.info(f"Final Payload Generated: {json.dumps(final_json_payload)}")
            # Yield Success Event
            yield Event(
                author=self.name,
                content=types.Content(role='assistant', parts=[types.Part(text="RULE_GENERATION_SUCCESS")])
            )

        except Exception as e:
            error_msg = f"GENERATION_ERROR: {str(e)}"
            self._logger.error(error_msg)
            yield Event(
                author=self.name,
                content=types.Content(role='assistant', parts=[types.Part(text=error_msg)])
            )
            return

# Instantiate for use in orchestrator
rule_generation_agent = DQRuleGenerationCustomAgent()