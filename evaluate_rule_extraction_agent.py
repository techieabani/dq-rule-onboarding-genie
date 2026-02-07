import json
import os
import time
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, classification_report
from src.rule_onboarding.finetune.wrapper import rule_extraction_model_wrapper

from src.rule_onboarding.utils.logger import setup_logger

#--- LOGGER SETUP ---
logger = setup_logger("EVALUATE_RULE_EXTRACTION_AGENT")

test_cases = [
    {"input": "Check the stale context for the metadata table in the system schema, repository SysRepo, baseline 1.", "expected": "{\"rule_name\": \"DQ_SYSTEM_METADATA_STALE_CONTEXT_RULE\", \"db_name\": \"system\", \"dataset_name\": \"metadata\", \"repository_name\": \"SysRepo\", \"attributes\": [{\"column_name\": \"STALE_CONTEXT\", \"rule_type\": \"STALE_CONTEXT\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": 1, \"threshold_value\": null}}]}"},
    {"input": "Configure a record count rule for the s3://app-logs/errors/trace.parquet dataset, baseline source PREVIOUS.", "expected": "{\"rule_name\": \"DQ_AWS_S3_TRACE_RECORD_COUNT_RULE\", \"db_name\": \"parquet\", \"dataset_name\": \"s3://app-logs/errors/trace.parquet\", \"repository_name\": null, \"attributes\": [{\"column_name\": \"RECORD_COUNT\", \"rule_type\": \"RECORD_COUNT\", \"baseline_source\": \"PREVIOUS\", \"rule_details\": {\"baseline_value\": null, \"threshold_value\": null}}]}"},
    {"input": "Onboard a mean check on the age column for the users table using repository UserRepo.", "expected": "{\"rule_name\": \"DQ_USERS_MEAN_RULE\", \"db_name\": null, \"dataset_name\": \"users\", \"repository_name\": \"UserRepo\", \"attributes\": [{\"column_name\": \"age\", \"rule_type\": \"MEAN\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": null, \"threshold_value\": null}}]}"},
    {"input": "Check the stale count for the active_users table in the analytics schema, baseline 50, threshold 500, baseline source CONFIG.", "expected": "{\"rule_name\": \"DQ_ANALYTICS_ACTIVE_USERS_STALE_COUNT_RULE\", \"db_name\": \"analytics\", \"dataset_name\": \"active_users\", \"repository_name\": null, \"attributes\": [{\"column_name\": \"STALE_COUNT\", \"rule_type\": \"STALE_COUNT\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": 50, \"threshold_value\": 500}}]}"},
    {"input": "Set a sum check for the tax_amount column on the invoices table (finance schema) with baseline 100. Repo: TaxRepo.", "expected": "{\"rule_name\": \"DQ_FINANCE_INVOICES_SUM_RULE\", \"db_name\": \"finance\", \"dataset_name\": \"invoices\", \"repository_name\": \"TaxRepo\", \"attributes\": [{\"column_name\": \"tax_amount\", \"rule_type\": \"SUM\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": 100, \"threshold_value\": null}}]}"},
    {"input": "Onboard a record count check for the subscribers table.", "expected": "{\"rule_name\": \"DQ_SUBSCRIBERS_RECORD_COUNT_RULE\", \"db_name\": null, \"dataset_name\": \"subscribers\", \"repository_name\": null, \"attributes\": [{\"column_name\": \"RECORD_COUNT\", \"rule_type\": \"RECORD_COUNT\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": null, \"threshold_value\": null}}]}"},
    {"input": "Configure a rule to check the mean of the credit_score column in the applicants table of the banking schema. Repo: FinRepo.", "expected": "{\"rule_name\": \"DQ_BANKING_APPLICANTS_MEAN_RULE\", \"db_name\": \"banking\", \"dataset_name\": \"applicants\", \"repository_name\": \"FinRepo\", \"attributes\": [{\"column_name\": \"credit_score\", \"rule_type\": \"MEAN\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": null, \"threshold_value\": null}}]}"},
    {"input": "Ensure the stale context in the external_partners table of the vendor schema is monitored with baseline source PREVIOUS.", "expected": "{\"rule_name\": \"DQ_VENDOR_EXTERNAL_PARTNERS_STALE_CONTEXT_RULE\", \"db_name\": \"vendor\", \"dataset_name\": \"external_partners\", \"repository_name\": null, \"attributes\": [{\"column_name\": \"STALE_CONTEXT\", \"rule_type\": \"STALE_CONTEXT\", \"baseline_source\": \"PREVIOUS\", \"rule_details\": {\"baseline_value\": null, \"threshold_value\": null}}]}"},
    {"input": "Onboard a median variance check on the load_time column in the web_performance table. Baseline 2.5, threshold 10.", "expected": "{\"rule_name\": \"DQ_WEB_PERFORMANCE_MEDIAN_VARIANCE_RULE\", \"db_name\": null, \"dataset_name\": \"web_performance\", \"repository_name\": null, \"attributes\": [{\"column_name\": \"load_time\", \"rule_type\": \"MEDIAN_VARIANCE\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": 2.5, \"threshold_value\": 10}}]}"},
    {"input": "Configure a rule named PROD_STOCKS_NULL_CHECK for null count on product_id in stocks table, schema inventory. Repository: GlobalRepo.", "expected": "{\"rule_name\": \"PROD_STOCKS_NULL_CHECK\", \"db_name\": \"inventory\", \"dataset_name\": \"stocks\", \"repository_name\": \"GlobalRepo\", \"attributes\": [{\"column_name\": \"product_id\", \"rule_type\": \"NULL_COUNT\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": null, \"threshold_value\": null}}]}"},
    {"input": "Onboard a stale count check for the s3://raw-data/telemetry/device_01.json file with baseline 1 and threshold 50.", "expected": "{\"rule_name\": \"DQ_AWS_S3_DEVICE_01_STALE_COUNT_RULE\", \"db_name\": \"JSON\", \"dataset_name\": \"s3://raw-data/telemetry/device_01.json\", \"repository_name\": null, \"attributes\": [{\"column_name\": \"STALE_COUNT\", \"rule_type\": \"STALE_COUNT\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": 1, \"threshold_value\": 50}}]}"},
    {"input": "Create a rule for sum check on weight column of shipments table in freight schema. Baseline 1000, threshold 20000.", "expected": "{\"rule_name\": \"DQ_FREIGHT_SHIPMENTS_SUM_RULE\", \"db_name\": \"freight\", \"dataset_name\": \"shipments\", \"repository_name\": null, \"attributes\": [{\"column_name\": \"weight\", \"rule_type\": \"SUM\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": 1000, \"threshold_value\": 20000}}]}"},
    {"input": "Onboard a rule for record count on the tickets table in the support schema. Baseline source is PREVIOUS.", "expected": "{\"rule_name\": \"DQ_SUPPORT_TICKETS_RECORD_COUNT_RULE\", \"db_name\": \"support\", \"dataset_name\": \"tickets\", \"repository_name\": null, \"attributes\": [{\"column_name\": \"RECORD_COUNT\", \"rule_type\": \"RECORD_COUNT\", \"baseline_source\": \"PREVIOUS\", \"rule_details\": {\"baseline_value\": null, \"threshold_value\": null}}]}"},
    {"input": "Configure a stale context check for the analytics table. Baseline 12, Threshold 24.", "expected": "{\"rule_name\": \"DQ_ANALYTICS_STALE_CONTEXT_RULE\", \"db_name\": null, \"dataset_name\": \"analytics\", \"repository_name\": null, \"attributes\": [{\"column_name\": \"STALE_CONTEXT\", \"rule_type\": \"STALE_CONTEXT\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": 12, \"threshold_value\": 24}}]}"},
    {"input": "Perform a NULL_COUNT check on the phone_number column of the customers table. Baseline value 0, Threshold value 5.", "expected": "{\"rule_name\": \"DQ_CUSTOMERS_NULL_COUNT_RULE\", \"db_name\": null, \"dataset_name\": \"customers\", \"repository_name\": null, \"attributes\": [{\"column_name\": \"phone_number\", \"rule_type\": \"NULL_COUNT\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": 0, \"threshold_value\": 5}}]}"},
    {"input": "Create a sum check on the total_cost column of the orders table in the enterprise schema, repository ERP_System.", "expected": "{\"rule_name\": \"DQ_ENTERPRISE_ORDERS_SUM_RULE\", \"db_name\": \"enterprise\", \"dataset_name\": \"orders\", \"repository_name\": \"ERP_System\", \"attributes\": [{\"column_name\": \"total_cost\", \"rule_type\": \"SUM\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": null, \"threshold_value\": null}}]}"},
    {"input": "Onboard a record_count rule for s3://audit-logs/2023/system_events.csv with baseline 5000.", "expected": "{\"rule_name\": \"DQ_AWS_S3_SYSTEM_EVENTS_RECORD_COUNT_RULE\", \"db_name\": \"CSV\", \"dataset_name\": \"s3://audit-logs/2023/system_events.csv\", \"repository_name\": null, \"attributes\": [{\"column_name\": \"RECORD_COUNT\", \"rule_type\": \"RECORD_COUNT\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": 5000, \"threshold_value\": null}}]}"},
    {"input": "Onboard a median variance check on the price column for s3://retail-data/products/catalog.json. Use repository RetailRepo, baseline 45, threshold 200.", "expected": "{\"rule_name\": \"DQ_AWS_S3_CATALOG_MEDIAN_VARIANCE_RULE\", \"db_name\": \"JSON\", \"dataset_name\": \"s3://retail-data/products/catalog.json\", \"repository_name\": \"RetailRepo\", \"attributes\": [{\"column_name\": \"price\", \"rule_type\": \"MEDIAN_VARIANCE\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": 45, \"threshold_value\": 200}}]}"},
    {"input": "Ensure the sum of the quantity column in the inventory table (warehouse schema) is between 500 and 5000, baseline source CONFIG.", "expected": "{\"rule_name\": \"DQ_WAREHOUSE_INVENTORY_SUM_RULE\", \"db_name\": \"warehouse\", \"dataset_name\": \"inventory\", \"repository_name\": null, \"attributes\": [{\"column_name\": \"quantity\", \"rule_type\": \"SUM\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": 500, \"threshold_value\": 5000}}]}"},
    {"input": "Create a rule to check the standard deviation of the rating column in the reviews table of the ecomm schema.", "expected": "{\"rule_name\": \"DQ_ECOMM_REVIEWS_STD_DEV_RULE\", \"db_name\": \"ecomm\", \"dataset_name\": \"reviews\", \"repository_name\": null, \"attributes\": [{\"column_name\": \"rating\", \"rule_type\": \"STD_DEV\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": null, \"threshold_value\": null}}]}"},
    {"input": "Onboard a record count check for the dataset s3://production-bucket/logs/daily_activity.parquet with a baseline value of 1000 and threshold 5000.", "expected": "{\"rule_name\": \"DQ_AWS_S3_DAILY_ACTIVITY_RECORD_COUNT_RULE\", \"db_name\": \"parquet\", \"dataset_name\": \"s3://production-bucket/logs/daily_activity.parquet\", \"repository_name\": null, \"attributes\": [{\"column_name\": \"RECORD_COUNT\", \"rule_type\": \"RECORD_COUNT\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": 1000, \"threshold_value\": 5000}}]}"},
    {"input": "Onboard a rule named MKT_LEADS_UNIQUE_COUNT for the email column in the leads table within the marketing schema. Use baseline source PREVIOUS, baseline 100, and threshold 50. Repo: MarketingRepo.", "expected": "{\"rule_name\": \"MKT_LEADS_UNIQUE_COUNT\", \"db_name\": \"marketing\", \"dataset_name\": \"leads\", \"repository_name\": \"MarketingRepo\", \"attributes\": [{\"column_name\": \"email\", \"rule_type\": \"UNIQUE_COUNT\", \"baseline_source\": \"PREVIOUS\", \"rule_details\": {\"baseline_value\": 100, \"threshold_value\": 50}}]}"},
    {"input": "Check the minimum value for the transaction_amount column in the payments table of the finance schema, using a baseline of 0.01 and a threshold of 10000.", "expected": "{\"rule_name\": \"DQ_FINANCE_PAYMENTS_MIN_RULE\", \"db_name\": \"finance\", \"dataset_name\": \"payments\", \"repository_name\": null, \"attributes\": [{\"column_name\": \"transaction_amount\", \"rule_type\": \"MIN\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": 0.01, \"threshold_value\": 10000}}]}"},
    {"input": "Configure a STALE_COUNT check for s3://warehouse/inventory/stocks.csv using repository DataLakeRepo. Baseline is 0, threshold 10.", "expected": "{\"rule_name\": \"DQ_AWS_S3_STOCKS_STALE_COUNT_RULE\", \"db_name\": \"CSV\", \"dataset_name\": \"s3://warehouse/inventory/stocks.csv\", \"repository_name\": \"DataLakeRepo\", \"attributes\": [{\"column_name\": \"STALE_COUNT\", \"rule_type\": \"STALE_COUNT\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": 0, \"threshold_value\": 10}}]}"},
    {"input": "Add a STALE_CONTEXT check for s3://staging/exports/users_v1.parquet, baseline source PREVIOUS, baseline value 5.", "expected": "{\"rule_name\": \"DQ_AWS_S3_USERS_V1_STALE_CONTEXT_RULE\", \"db_name\": \"parquet\", \"dataset_name\": \"s3://staging/exports/users_v1.parquet\", \"repository_name\": null, \"attributes\": [{\"column_name\": \"STALE_CONTEXT\", \"rule_type\": \"STALE_CONTEXT\", \"baseline_source\": \"PREVIOUS\", \"rule_details\": {\"baseline_value\": 5, \"threshold_value\": null}}]}"},
    {"input": "Set up a record count check for the shipping table in the logistics schema with a threshold value of 10000.", "expected": "{\"rule_name\": \"DQ_LOGISTICS_SHIPPING_RECORD_COUNT_RULE\", \"db_name\": \"logistics\", \"dataset_name\": \"shipping\", \"repository_name\": null, \"attributes\": [{\"column_name\": \"RECORD_COUNT\", \"rule_type\": \"RECORD_COUNT\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": null, \"threshold_value\": 10000}}]}"},
    {"input": "Onboard a null count rule for the user_id column in the sessions table.", "expected": "{\"rule_name\": \"DQ_SESSIONS_NULL_COUNT_RULE\", \"db_name\": null, \"dataset_name\": \"sessions\", \"repository_name\": null, \"attributes\": [{\"column_name\": \"user_id\", \"rule_type\": \"NULL_COUNT\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": null, \"threshold_value\": null}}]}"},
    {"input": "Check the mean value of the humidity column for the sensors dataset, repository IOT_Repo.", "expected": "{\"rule_name\": \"DQ_SENSORS_MEAN_RULE\", \"db_name\": null, \"dataset_name\": \"sensors\", \"repository_name\": \"IOT_Repo\", \"attributes\": [{\"column_name\": \"humidity\", \"rule_type\": \"MEAN\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": null, \"threshold_value\": null}}]}"},
    {"input": "Onboard a median variance check on the delivery_days column of the shipping table.", "expected": "{\"rule_name\": \"DQ_SHIPPING_MEDIAN_VARIANCE_RULE\", \"db_name\": null, \"dataset_name\": \"shipping\", \"repository_name\": null, \"attributes\": [{\"column_name\": \"delivery_days\", \"rule_type\": \"MEDIAN_VARIANCE\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": null, \"threshold_value\": null}}]}"},
    {"input": "Add a sum check on the total_sales column of the region_data table in the marketing schema.", "expected": "{\"rule_name\": \"DQ_MARKETING_REGION_DATA_SUM_RULE\", \"db_name\": \"marketing\", \"dataset_name\": \"region_data\", \"repository_name\": null, \"attributes\": [{\"column_name\": \"total_sales\", \"rule_type\": \"SUM\", \"baseline_source\": \"CONFIG\", \"rule_details\": {\"baseline_value\": null, \"threshold_value\": null}}]}"}
]

def plot_dq_confusion_matrix(y_true, y_pred, labels):
    """
    Plots a confusion matrix for Data Quality Rule Types.
    y_true: List of correct rule types (e.g., ['MEAN', 'SUM'])
    y_pred: List of model predicted rule types
    labels: Distinct list of all possible rule types
    """
    # 1. Calculate the matrix
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    
    # 2. Convert to DataFrame for easier plotting with labels
    df_cm = pd.DataFrame(cm, index=labels, columns=labels)
    
    # 3. Create the plot
    plt.figure(figsize=(10, 7))
    sns.set(font_scale=1.2) # Make text readable
    
    # annot=True shows the numbers in each cell
    # fmt='d' ensures they are displayed as integers
    sns.heatmap(df_cm, annot=True, fmt='d', cmap='Blues', 
                cbar_kws={'label': 'Number of Rules'})
    
    plt.title("Confusion Matrix: DQ Rule Type Extraction", fontsize=16, pad=20)
    plt.ylabel("Actual Rule Type", fontsize=14)
    plt.xlabel("Model Predicted Type", fontsize=14)
    plt.xticks(rotation=45)
    plt.yticks(rotation=0)
    plt.tight_layout()
    
    # Save for thesis document
    plt.savefig("dq_confusion_matrix.png", dpi=300)
    plt.show()


def evaluate_rule_extraction_agent():
    results = []
    # Sample evaluation results from the Golden Dataset
    y_rule_type_expected = []
    y_rule_type_predicted = []
    for case in test_cases:
        start_time = time.time()
        actual_output = rule_extraction_model_wrapper.generate(case['input'])
        latency = time.time() - start_time
        print(f"actual_output:{actual_output}")
        print(f'latency:{latency}')
        y_rule_type_predicted.append(actual_output.get("rule_type"))
        
        expected = case['expected']
        print(f"expected:{expected}")
        if isinstance(expected, str):
            expected = json.loads(expected)
        y_rule_type_expected.append(expected.get("rule_type"))
        # For a simple EM (Exact Match) score:
        is_exact_match = (actual_output == expected)
        print(f"is_exact_match:{is_exact_match}")
        # To calculate a granular score (Property Match):
        matches = 0
        total_keys = 0
        
        # Check top level keys
        for key in ["rule_name", "db_name", "dataset_name", "rule_type"]:
             if key in expected:
                 total_keys += 1
                 if actual_output.get(key) == expected.get(key):
                     matches += 1
        
        score = (matches / total_keys) * 100 if total_keys > 0 else 0
        print(f"score:{score}")
        results.append({
            "prompt": case['input'],
            "score": score,
            "latency": latency,
            "success": is_exact_match # More rigorous than property score
        })

    df = pd.DataFrame(results)
    print(f"\nOverall Exact Match Accuracy: {df['success'].mean() * 100}%")
    print(f"Avg Latency: {df['latency'].mean():.2f}s")
    df.to_csv("evaluation_report_1.csv", index=False)
    
    # The DQ Rule model is trained on
    dq_labels = ["MEAN","RECORD_COUNT","SUM","NULL_COUNT","MEDIAN_VARIANCE","STALE_COUNT","STALE_CONTEXT","STD_DEV","MIN","MAX","UNIQUE_COUNT"]
   
    plot_dq_confusion_matrix(y_rule_type_expected, y_rule_type_predicted, dq_labels)
    
    # Print the full stats report too
    print("\nDetailed Classification Report:")
    print(classification_report(y_rule_type_expected, y_rule_type_predicted, target_names=dq_labels))
if __name__ == "__main__":
    evaluate_rule_extraction_agent()