from google.adk.agents import Agent

DQ_RULE_DETAILS_TO_JSON_PAYLOAD_EXAMPLES = """
Example 1:
Input: 
  "rule_name": "avg_price_check",
  "db_name": "customer",
  "dataset_name": "sales",
  "column_name": "price",
  "rule_type": "MEAN",
  "baseline_value": 10.0,
  "threshold_value": 100.0

Assistant:
{
  "rule_name": "avg_price_check",
  "db_name": "customer",
  "dataset_name": "sales",
  "column_name": "price",
  "rule_type": "MEAN",
  "baseline_value": 10.0,
  "threshold_value": 100.0
}

Example 2:

Input: 

"rule_name": "order_count_check",
  "db_name": "customer",
  "dataset_name": "orders",
  "column_name": "RECORD_COUNT",
  "rule_type": "RECORD_COUNT",
  "baseline_value": 500.0,
  "threshold_value": null
  
Assistant:
{
  "rule_name": "order_count_check",
  "db_name": "customer",
  "dataset_name": "orders",
  "column_name": "RECORD_COUNT",
  "rule_type": "RECORD_COUNT",
  "baseline_value": 500.0,
  "threshold_value": null
}

"""

rule_generation_agent = Agent(
    name="rule_generation_agent",
    model="gemini-3-flash-preview",
    instruction=f"""
    You are a Data Quality Assistant.
    Convert {{validated_rule_details}} into a strictly valid JSON payload, example: {DQ_RULE_DETAILS_TO_JSON_PAYLOAD_EXAMPLES} for the DQ REST API.
    """,
    output_key="configure_rule_json_payload"
)