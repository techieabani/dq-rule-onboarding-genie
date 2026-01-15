import streamlit as st
import uuid
import requests

st.set_page_config(page_title="DQ Rule Onboarding Bot", page_icon="🤖")
st.title("Data Quality Rule Onboarding Assistant 🤖")

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

if prompt := st.chat_input("Ex: Onboard a mean check for 'revenue' in 'sales' table with baseline value 10 and threshold 100"):
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
            with requests.post("http://localhost:8085/onboard-rule", json={"message": prompt, "session_id": st.session_state.adk_session_id}, stream=True, timeout=60) as response:
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
                else:
                    st.error(f"API Error: {response.status_code}")
        except requests.exceptions.RequestException as e:
            st.error(f"Network Error: {e}")
        except Exception as e:
            st.error(f"Error connecting to Agent API: {e}")
