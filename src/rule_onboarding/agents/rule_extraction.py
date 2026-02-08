import os
from pathlib import Path
import yaml
from google.adk.agents import Agent
from src.rule_onboarding.utils.logger import setup_logger

#--- LOGGER SETUP ---
logger = setup_logger("DQ_RULE_EXTRACTION_AGENT")

# The directory where the Instruction for the rule extraction agent configuration file is stored
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config" / "rule_extraction_agent_config.yaml"

# Load the external configuration
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)["rule_extraction_gemini_agent"]

# Initialize the agent using the externalized text
rule_extraction_gemini_agent = Agent(
    name=config["name"],
    model=config["model"],
    instruction=f"{config['system_instruction']}\n\n### Examples:\n{config['examples']}",
    output_key="raw_rule_details"
)