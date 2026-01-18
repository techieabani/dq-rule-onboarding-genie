import streamlit as st
import uuid
import requests

# --- API URLs ---
RULE_ONBOARDING_BACKEND_API_URL = "http://localhost:8083/onboard-rule"

st.set_page_config(page_title="DQ Rule Onboarding Genie", page_icon="🤖")
st.title("DQ Rule Onboarding Genie 🤖")

if st.sidebar.button("Clear Conversation History"):
    # Clear Streamlit's local state
    st.session_state.messages = []
    # Generate a NEW session_id so the backend treats it as a fresh start
    st.session_state.adk_session_id = str(uuid.uuid4())
    st.rerun()
    
# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Generate a unique ID for this browser tab session if it doesn't exist
if "adk_session_id" not in st.session_state:
    st.session_state.adk_session_id = str(uuid.uuid4())

# Display chat history from previous turns
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ex: Onboard a mean check for column 'revenue' in 'sales' table with baseline source as CONFIG, baseline value 10 and threshold 100"):
    # Update UI with User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)
        
    # Assistant Response Container
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        
        try:
            # Use requests with stream=True to get streaming response
            with requests.post(RULE_ONBOARDING_BACKEND_API_URL, json={"message": prompt, "session_id": st.session_state.adk_session_id}, stream=True, timeout=60) as response:
                if response.status_code == 200:
                    for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                        if chunk:
                            # If using SSE, chunk = chunk.replace("data: ", "")
                            full_response += chunk
                            response_placeholder.markdown(full_response + " ")
                    #Final clean render
                    response_placeholder.markdown(full_response)
                    # Add assistant response to history
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    if "baseline value must be 1.0" in full_response:
                        if st.session_state.messages and "Validation Error" in st.session_state.messages[-1]["content"]:
                            st.warning("Would you like me to fix this for you?")
                            if st.button("Update Baseline to 1.0 and Retry"):
                                # We send a "hidden" corrective prompt to the same session
                                correction_prompt = "Actually, please use 1.0 as the baseline value for that rule."
                
                                # We trigger a rerun with the new prompt
                                # In a real app, you'd wrap the API call in a function to reuse it here
                                st.session_state.messages.append({"role": "user", "content": correction_prompt})
                            st.rerun()
                else:
                    st.error(f"API Error: {response.status_code}")
        except requests.exceptions.RequestException as e:
            st.error(f"Network Error: {e}")
        except Exception as e:
            st.error(f"Error connecting to Agent API: {e}")
