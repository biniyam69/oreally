import streamlit as st
import requests
import json
from src.chat import chat

st.title("Planning Assistant")
if "messages" not in st.session_state:
    st.session_state.messages = []
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Accept user input
if prompt := st.chat_input("What is up?"):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    input_data = {"input_text": prompt}
    res = chat(input=input_data)
    with st.chat_message("assistant"):
        st.markdown(res)
        
    st.session_state.messages.append({"role": "assistant", "content": res})

