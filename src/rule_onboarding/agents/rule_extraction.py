from google.adk.agents import Agent
DQ_EXAMPLES = """
Example 1:
User: I need to make sure the average price in sales table of customer schema is between 10 and 100.
Assistant:

  "rule_name": "avg_price_check",
  "db_name": "customer",
  "dataset_name": "sales",
  "column_name": "price",
  "rule_type": "MEAN",
  "baseline_value": 10.0,
  "threshold_value": 100.0


Example 2:
User: Check if the row count for the customer schema orders table is at least 500.
Assistant:

  "rule_name": "order_count_check",
  "db_name": "customer",
  "dataset_name": "orders",
  "column_name": "RECORD_COUNT",
  "rule_type": "RECORD_COUNT",
  "baseline_value": 500.0,
  "threshold_value": null

"""

rule_extraction_agent = Agent(
    name="rule_extraction_agent",
    model="gemini-3-flash-preview",
    instruction=f"""
        You are a Data Quality Assistant. 
        When users describe a Check/Rule example : {DQ_EXAMPLES}, then extract rule_name, db_name, table_name, column, rule_type, baseline and threshold from the user input prompt. Save it as raw_details.
        """,
    output_key="raw_rule_details"
)