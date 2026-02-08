import json
import os
import time
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import asyncio
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types
from src.rule_onboarding.agents.rule_extraction import rule_extraction_gemini_agent
from sklearn.metrics import classification_report, confusion_matrix,precision_recall_curve, auc

from src.rule_onboarding.utils.logger import setup_logger

#--- LOGGER SETUP ---
logger = setup_logger("RULE_EXTRACTION_AGENT_EVALUATION_COMPARISON_GEMINI3_VS_GEMMA2")

# This looks for a .env file in the current directory or parents
load_dotenv() 

# ADK can find the key
api_key = os.getenv("GOOGLE_API_KEY")


# --- EVALUATION DATA ---
sample_eval_data = [
    {
        "input": "Check the stale context for the metadata table in the system schema, repository SysRepo, baseline 1.", 
        "expected": {
            "rule_name": "DQ_SYSTEM_METADATA_STALE_CONTEXT_RULE", 
            "db_name": "system", 
            "dataset_name": "metadata", 
            "repository_name": "SysRepo", 
            "attributes": [{
                "column_name": "STALE_CONTEXT", 
                "rule_type": "STALE_CONTEXT", 
                "baseline_source": "CONFIG", 
                "rule_details": {"baseline_value": 1, "threshold_value": None}
            }]
        }
    },
    {
        "input": "Configure a record count rule for the s3://app-logs/errors/trace.parquet dataset, baseline source PREVIOUS.", 
        "expected": {
            "rule_name": "DQ_AWS_S3_TRACE_RECORD_COUNT_RULE", 
            "db_name": "parquet", 
            "dataset_name": "s3://app-logs/errors/trace.parquet", 
            "repository_name": None, 
            "attributes": [{
                "column_name": "RECORD_COUNT", 
                "rule_type": "RECORD_COUNT", 
                "baseline_source": "PREVIOUS", 
                "rule_details": {"baseline_value": None, "threshold_value": None}
            }]
        }
    },
    {
        "input": "Onboard a mean check on the age column for the users table using repository UserRepo.", 
        "expected": {
            "rule_name": "DQ_USERS_MEAN_RULE", 
            "db_name": None, 
            "dataset_name": "users", 
            "repository_name": "UserRepo", 
            "attributes": [{
                "column_name": "age", 
                "rule_type": "MEAN", 
                "baseline_source": "CONFIG", 
                "rule_details": {"baseline_value": None, "threshold_value": None}
            }]
        }
    },
    {
        "input": "Onboard a median variance check on the delivery_days column of the shipping table.", 
        "expected": {
            "rule_name": "DQ_SHIPPING_MEDIAN_VARIANCE_RULE", 
            "db_name": None, 
            "dataset_name": "shipping", 
            "repository_name": None, 
            "attributes": [{
                "column_name": "delivery_days", 
                "rule_type": "MEDIAN_VARIANCE", 
                "baseline_source": "CONFIG", 
                "rule_details": {"baseline_value": None, "threshold_value": None}
            }]
        }
    },
    {
        "input": "Add a sum check on the total_sales column of the region_data table in the marketing schema.", 
        "expected": {
            "rule_name": "DQ_MARKETING_REGION_DATA_SUM_RULE", 
            "db_name": "marketing", 
            "dataset_name": "region_data", 
            "repository_name": None, 
            "attributes": [{
                "column_name": "total_sales", 
                "rule_type": "SUM", 
                "baseline_source": "CONFIG", 
                "rule_details": {"baseline_value": None, "threshold_value": None}
            }]
        }
    }
]


# Note: y_true are the actual binary labels (1 = correct rule extraction)
# y_scores are the confidence/probability scores from your model's output
def plot_pr_curves(y_true, gemini_scores, gemma_scores):
    # Calculate curves
    p_gemini, r_gemini, _ = precision_recall_curve(y_true, gemini_scores)
    p_gemma, r_gemma, _ = precision_recall_curve(y_true, gemma_scores)
    
    # Calculate Area Under Curve (AUC)
    auc_gemini = auc(r_gemini, p_gemini)
    auc_gemma = auc(r_gemma, p_gemma)

    # Plotting
    plt.figure(figsize=(10, 7))
    plt.plot(r_gemini, p_gemini, label=f'Gemini-3-Flash (AUC = {auc_gemini:.2f})', color='blue', lw=2)
    plt.plot(r_gemma, p_gemma, label=f'Fine-tuned Gemma-2-2B (AUC = {auc_gemma:.2f})', color='orange', lw=2)

    plt.xlabel('Recall', fontsize=12)
    plt.ylabel('Precision', fontsize=12)
    plt.title('Precision-Recall Curve: Rule Extraction Performance', fontsize=14)
    plt.legend(loc='lower left')
    plt.grid(True, linestyle='--', alpha=0.6)
    
    plt.savefig('pr_curve_comparison.png')
    plt.show()

def calculate_metrics(actual, expected):
    """Calculates granular match scores."""
    if not actual: return 0, 0, 0
    # Rule Type Match (Precision/Recall baseline)
    type_match = 1 if actual.get('attributes', [{}])[0].get('rule_type') == expected.get('attributes', [{}])[0].get('rule_type') else 0
    # Exact Match (Full JSON Parity)
    exact_match = 1 if actual == expected else 0
    return type_match, exact_match

# --- HELPER TO RUN ASYNC IN SYNC SCRIPT ---
async def get_gemini_response(prompt):
    """
    Programmatically runs the Gemini Agent using Google ADK.
    """
    APP_NAME = "agents"
    USER_ID = "2023ad05035"
    # Initialize Runner (Linked to the existing agent instance)
    runner = InMemoryRunner(agent=rule_extraction_gemini_agent, app_name=APP_NAME)
    
    # 2. Setup Session
    session = await runner.session_service.create_session(
        app_name=APP_NAME, 
        user_id=USER_ID
    )

    # 3. Create User Message
    user_message = types.Content(
        role='user', 
        parts=[types.Part.from_text(text=prompt)]
    )

    # 4. Execute and Capture Output
    final_output = None
    # We iterate through the event stream to get the final message
    for event in runner.run(user_id=USER_ID, session_id=session.id, new_message=user_message):
        if event.content and event.content.parts:
            # The agent populates state based on 'output_key' in the config
            # Alternatively, we can grab the raw text response
            final_output = event.content.parts[0].text

    # 5. Parse JSON safely
    try:
        # Some models wrap JSON in markdown blocks (```json ... ```)
        clean_json = final_output.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        logger.error(f"Failed to parse Gemini JSON: {e}")
        return {}
    
async def run_evaluation():
    comparison_results = []

    for eval_data in sample_eval_data:
    
        # --- GEMINI RUN ---
        
        start = time.time()
        gemini_json = await get_gemini_response(eval_data['input'])
        gemini_lat = time.time() - start
        logger.info(f"Gemini-3-Flash response: {gemini_json}")
        gem_type, gem_exact = calculate_metrics(gemini_json, eval_data['expected'])
        
        comparison_results.append({"Model": "Gemini-3-Flash", "Latency": gemini_lat, "Type_Match": gem_type, "Exact_Match": gem_exact})

        # --- GEMMA RUN ---
        
        from src.rule_onboarding.finetune.wrapper import rule_extraction_model_wrapper
        start = time.time()
        gemma_json = await asyncio.to_thread(
                rule_extraction_model_wrapper.generate, 
                eval_data['input'])
        gemma_lat = time.time() - start
        logger.info(f"Fine-tuned Gemma-2B response: {gemma_json}")
        gma_type, gma_exact = calculate_metrics(gemma_json, eval_data['expected'])
        
        comparison_results.append({"Model": "Fine-Tuned Gemma-2B", "Latency": gemma_lat, "Type_Match": gma_type, "Exact_Match": gma_exact})

    # --- PLOTTING ---
    df = pd.DataFrame(comparison_results)
    
    # Basic Bar Charts (Accuracy & Latency)
    plt.figure(figsize=(14, 6))
    plt.subplot(1, 2, 1)
    sns.barplot(x='Model', y='Exact_Match', data=df, palette='viridis', errorbar=None).set_title("Accuracy (Exact Match %)")
    
    plt.subplot(1, 2, 2)
    sns.barplot(x='Model', y='Latency', data=df, palette='magma', errorbar=None).set_title("Latency (Seconds - Lower is Better)")
    plt.tight_layout()
    plt.savefig("gemini_vs_gemma_accuracy_latency.png")

    logger.info("Report generated: gemini_vs_gemma_accuracy_latency.png")
    
    # Precision-Recall Curve Simulation
    # The collected Type_Match as y_true
    # Since we don't have raw log-probs, we use the binary match result
    gemini_data = df[df['Model'] == 'Gemini-3-Flash']
    gemma_data = df[df['Model'] == 'Fine-Tuned Gemma-2B']

    plot_pr_curves(
        y_true=gemini_data['Type_Match'].values, 
        gemini_scores=gemini_data['Exact_Match'].values, # Using Exact Match as a proxy for 'confidence'
        gemma_scores=gemma_data['Exact_Match'].values
    )

if __name__ == "__main__":
    asyncio.run(run_evaluation())