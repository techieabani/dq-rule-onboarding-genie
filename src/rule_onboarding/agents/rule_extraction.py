from google.adk.agents import Agent
from src.rule_onboarding.utils.logger import setup_logger

#--- LOGGER SETUP ---
logger = setup_logger("DQ_RULE_EXTRACTION_AGENT")

DQ_EXAMPLES = """
Example 1:
User: Onboard Rules for sales table of customer schema with repository name AWSRepo 1) Record count with baseline_source CONFIG baseline_value 10 threshold_value 100 2) Mean on order column with baseline_source CONFIG baseline_value 1 threshold_value 40.
Assistant:
{
  "rule_name": "DQ_CUSTOMER_SALES_RULE",
  "db_name": "customer",
  "dataset_name": "sales",
  "repository_name": "AWSRepo",
  "attributes": [
    {
      "column_name": "RECORD_COUNT",
      "rule_type": "RECORD_COUNT",
      "baseline_source": "CONFIG",
      "rule_details": {
        "baseline_value": 10,
        "threshold_value": 100
      }
    },
	 {
      "column_name": "order",
      "rule_type": "MEAN",
      "baseline_source": "CONFIG",
      "rule_details": {
        "baseline_value": 1,
        "threshold_value": 40
      }
    }
  ]
}

Example 2:
User: Onboard Rules for Employee table of Databricks schema with repository name DatabricksRepo 
1) STALE count with baseline_source PREVIOUS baseline_value 10 threshold_value 100 
2) Mean variance on salary column with baseline_source PREVIOUS baseline_value 3 threshold_value 80.
3) Sum on salary column baseline_source CONFIG baseline_value 1 threshold_value 100000
Assistant:
{
  "rule_name": "DQ_DATABRICKS_EMPLOYEE_RULE",
  "db_name": "customer",
  "dataset_name": "sales",
  "repository_name": "AWSRepo",
  "attributes": [
    {
      "column_name": "STALE_COUNT",
      "rule_type": "STALE_COUNT",
      "baseline_source": "PREVIOUS",
      "rule_details": {
        "baseline_value": 10,
        "threshold_value": 100
      }
    },
	 {
      "column_name": "salary",
      "rule_type": "MEAN",
      "baseline_source": "PREVIOUS",
      "rule_details": {
        "baseline_value": 3,
        "threshold_value": 80
      }
    },
	 {
      "column_name": "salary",
      "rule_type": "SUM",
      "baseline_source": "CONFIG",
      "rule_details": {
        "baseline_value": 1,
        "threshold_value": 100000
      }
    }
  ]
}

Example 3:
User: Onboard a rule with name CSTMR_SALES_NULL_COUNT for ensuring NULL COUNT rule on order column of sales table of customer schema use baseline_source CONFIG baseline_value 1 threshold_value 5 for repository name GKPRepo 

Assistant:
{
  "rule_name": "CSTMR_SALES_NULL_COUNT",
  "db_name": "customer",
  "dataset_name": "sales",
  "repository_name": "GKPRepo",
  "attributes": [
    {
      "column_name": "order",
      "rule_type": "NULL_COUNT",
      "baseline_source": "CONFIG",
      "rule_details": {
        "baseline_value": 1,
        "threshold_value": 5
      }
    }
  ]
}

Example 4:
User: Ensure the average price in sales table of customer schema is between 10 and 100

Assistant:
{
  "rule_name": "DQ_CUSTOMER_SALES_MEAN_RULE",
  "db_name": "customer",
  "dataset_name": "sales",
  "repository_name": null,
  "attributes": [
    {
      "column_name": "price",
      "rule_type": "MEAN",
      "baseline_source": "CONFIG",
      "rule_details": {
        "baseline_value": 10,
        "threshold_value": 100
      }
    }
  ]
}

Example 5:
User: Check if the row count for the customer schema orders table is at least 500.

Assistant:
{
  "rule_name": "DQ_CUSTOMER_ORDERS_RECORD_COUNT_RULE",
  "db_name": "customer",
  "dataset_name": "sales",
  "repository_name": null,
  "attributes": [
    {
      "column_name": "RECORD_COUNT",
      "rule_type": "RECORD_COUNT",
      "baseline_source": "CONFIG",
      "rule_details": {
        "baseline_value": 500,
        "threshold_value": null
      }
    }
  ]
}

Example 6:
User: Onboard a Record count check on dataset s3://bucket-name/key-name/invoices.parquet baseline_value 1 threshold_value 100 

Assistant:
{
  "rule_name": "DQ_AWS_S3_INVOICES_RECORD_COUNT_RULE",
  "db_name": "parquet",
  "dataset_name": "s3://bucket-name/key-name/invoices.parquet",
  "repository_name": null,
  "attributes": [
    {
      "column_name": "RECORD_COUNT",
      "rule_type": "RECORD_COUNT",
      "baseline_source": "CONFIG",
      "rule_details": {
        "baseline_value": 1,
        "threshold_value": 100
      }
    }
  ]
}

Example 7:
User: Configure  STALE count check on dataset s3://bucket-name/key-name/sales.csv  baseline_source PREVIOUS baseline_value 3 threshold_value 15. Use repository AWSRepo

Assistant:
{
  "rule_name": "DQ_AWS_S3_SALES_STALE_COUNT_RULE",
  "db_name": "CSV",
  "dataset_name": "s3://bucket-name/key-name/sales.csv",
  "repository_name": "AWSRepo",
  "attributes": [
    {
      "column_name": "STALE_COUNT",
      "rule_type": "STALE_COUNT",
      "baseline_source": "PREVIOUS",
      "rule_details": {
        "baseline_value": 3,
        "threshold_value": 15
      }
    }
  ]
}

Example 8:
User: Create rule for Median Variance on column salary for dataset s3://bucket-name/key-name/employee.json  baseline_value 3000 threshold_value 1000000 with repository AWSRepo

Assistant:
{
  "rule_name": "DQ_AWS_S3_EMPLOYEE_MEDIAN_VARIANCE_RULE",
  "db_name": "JSON",
  "dataset_name": "s3://bucket-name/key-name/employee.json",
  "repository_name": "AWSRepo",
  "attributes": [
    {
      "column_name": "salary",
      "rule_type": "MEDIAN_VARIANCE",
      "baseline_source": "CONFIG",
      "rule_details": {
        "baseline_value": 3000,
        "threshold_value": 1000000
      }
    }
  ]
}

"""

# Define the logical structure and behavior
SYSTEM_INSTRUCTION = """
You are a specialized Data Quality Extraction Assistant. Your goal is to convert natural language requests into a structured JSON format for rule onboarding.

### Extraction Rules:
1. **Hierarchy**: Group common metadata (db_name, dataset_name, repository_name) at the top level. Put specific rule checks in the 'attributes' array.
2. **Rule Naming**: Generate a unique 'rule_name' if not provided, following the pattern: DQ_[DB]_[DATASET]_[TYPE]_RULE.
3. **Column Mapping**: 
   - For table level rules ('Record Count' or 'Row Count', 'Stale Count', 'Stale Context'), use respective 'RECORD_COUNT', 'STALE_COUNT', 'STALE_CONTEXT' as the column_name.
   - For column-specific checks (Mean, Sum, Mean Variance, Median Variance), use the explicit column name mentioned.
4. **Data Normalization**:
   - Default `baseline_source` to "CONFIG" if unspecified.
   - Use `null` for missing values (e.g., if a threshold isn't provided).
   - Ensure `baseline_value` and `threshold_value` are numbers, not strings.

### Schema Template:
{
  "rule_name": "string",
  "db_name": "string",
  "dataset_name": "string",
  "repository_name": "string or null",
  "attributes": [
    {
      "column_name": "string",
      "rule_type": "string",
      "baseline_source": "string",
      "rule_details": { "baseline_value": number, "threshold_value": number }
    }
  ]
}
"""

rule_extraction_agent = Agent(
    name="rule_extraction_agent",
    model="gemini-3-flash-preview",
    instruction=f"{SYSTEM_INSTRUCTION}\n\n### Examples:\n{DQ_EXAMPLES}",
    output_key="raw_rule_details"
)