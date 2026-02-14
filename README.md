# dq-rule-onboarding-genie
An Agentic AI application for automatic data quality rules generation and onboarding from a NLP prompt.
This project integrates a Model Backend, an MCP Server for tool-based agent interactions, and a Streamlit UI for Conversation AI chatbot.

This project uses uv for lightning-fast dependency management.

# Step 1. Install uv

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Step 2. Project Setup

# Once uv is installed, clone the repo, navigate to the project directory and initialize your environment:

# Clone and enter the repo
git clone https://github.com/techieabani/dq-rule-onboarding-genie.git

cd dq-rule-onboarding-genie

# Create a virtual environment (.venv)
uv venv

# Activate the environment
# Windows:
.venv\Scripts\activate

# macOS/Linux:
source .venv/bin/activate

# Sync dependencies from pyproject.toml
uv sync

# Step 3. Configure Environment

# Place appropriate GOOGLE_API_KEY & HF_TOKEN inside .env file which is inside project root directory.

GOOGLE_API_KEY=your_gemini_api_key_here
HF_TOKEN=your_hugging_face_token_here

# Step 4: Start Dependent Services

# Before launching the Genie, you must start the DQ-RULE-CONFIG-API which handles the actual onboarding logic (Persisting Rule in the Target DB).

# Clone the API repository: techieabani/dq-rule-config-api (https://github.com/techieabani/dq-rule-config-api).

# Follow the Step 1 & 2 setup instructions in a separate terminal tab.

# Start that service:
uv run python main.py

# Step 5. Launch the DQ-Rule-Onboarding-Genie Application

# Start the full stack (MCP Server, Backend API, and Streamlit UI):

uv run python main.py
