import json
from typing import AsyncGenerator
from google.adk.events import Event
from google.adk.agents import BaseAgent
import google.genai.types as types
from src.rule_onboarding.utils.logger import setup_logger

class HardcodedExtractionAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="rule_extraction_agent")
        self._logger = setup_logger("DQ_RULE_EXTRACTION_AGENT")
        self._output_key = "raw_rule_details"

    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        # 1. Your requested hardcoded JSON
        hardcoded_json = {
            "rule_name": "CUSTOMER_SALES_STALE_COUNT_RULE",
            "db_name": "customer",
            "dataset_name": "sales",
            "repository_name": "AWSRepo",
            "attributes": [
                {
                  "column_name": "STALE",
                  "rule_type": "STALE_COUNT",
                  "baseline_source": "PREVIOUS",
                  "rule_details": {
                      "baseline_value": 1.0,
                      "threshold_value": 100.0
                  }
                }
              ]  
        }
    
        ctx.session.state[self._output_key] = hardcoded_json
        self._logger.info(f" {self.name} injected hardcoded JSON into state.")
        msg = f"Static Extraction Complete for Rule: {hardcoded_json['rule_name']}"
        yield Event(
            author=self.name,
            content=types.Content(
            role="assistant",
            parts=[types.Part(text=msg)]
        )
        )

# Instantiate for use
rule_extraction_agent = HardcodedExtractionAgent()