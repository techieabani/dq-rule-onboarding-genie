from google.adk.agents import Agent
from src.rule_onboarding.utils.logger import setup_logger

#--- LOGGER SETUP ---
logger = setup_logger("DQ_RULE_EXTRACTION_AGENT")

DQ_EXAMPLES = """
Example 1:
User: Onboard a Rule for Rule_Type MEAN on column price in sales table of customer schema  with  baseline source as Config baseline value 10 and threshold value 100.
Assistant:
{
  "rule_name": "CUSTOMER_SALES_COLUMN_MEAN_RULE",
  "db_name": "customer",
  "dataset_name": "sales",
  "column_name": "price",
  "rule_type": "MEAN",
  "baseline_source": "CONFIG",
  "baseline_value": 10.0,
  "threshold_value": 100.0
}

Example 2:
User: onboard a Rule for Rule_Type STALE_COUNT on customer table of orders schema with baseline source as PREVIOUS baseline value as 1.0 and threshold value as 10.0.
Assistant:
{
  "rule_name": "ORDERS_CUSTOMER_STALE_COUNT_RULE",
  "db_name": "orders",
  "dataset_name": "customer",
  "column_name": "STALE_COUNT",
  "rule_type": "STALE_COUNT",
  "baseline_source": "PREVIOUS",
  "baseline_value": 1.0,
  "threshold_value": 10.0
}

"""

rule_extraction_agent1 = Agent(
    name="rule_extraction_agent",
    model="gemini-3-flash-preview",
    instruction=f"""
        You are a Data Quality Assistant. 
        When users describe a Check/Rule example : {DQ_EXAMPLES}, then extract rule_name, db_name, table_name, column, rule_type, baseline and threshold from the user input prompt. Save it as raw_details in JSON format.
        """,
    output_key="raw_rule_details"
)