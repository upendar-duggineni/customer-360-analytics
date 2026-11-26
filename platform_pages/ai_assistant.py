"""Streamlit chat interface for the active business workspace."""
from __future__ import annotations

import os

import streamlit as st

from src.ai_assistant.assistant import answer_question, get_api_key


SUGGESTED_QUESTIONS = [
    "Give me an overview of my business performance.",
    "Which customers generated the highest observed revenue?",
    "Show my monthly order and revenue trends.",
    "Which product categories perform best?",
    "How are customers paying?",
]


def render_ai_assistant(tables: dict, workspace_id: str) -> None:
    """Render a chat whose history is isolated to the active workspace session."""
    st.subheader("AI Business Analyst")
    st.caption("Ask questions about the datasets saved in this workspace. Calculations come from read-only Python analytics tools.")
    if not get_api_key():
        st.info("Connect an OpenAI API key to enable the assistant. Set OPENAI_API_KEY in your local .env file or add it to Streamlit secrets. Your key is never requested in the chat.")
        with st.expander("Configure OpenAI"):
            st.code('OPENAI_API_KEY="your-api-key"\nOPENAI_MODEL="gpt-5.5"', language="bash")
            st.caption("Restart Streamlit after changing your local .env file. Never commit the key to GitHub.")
        return

    state_key = f"business_ai_history_{workspace_id}"
    st.session_state.setdefault(state_key, [])
    left, right = st.columns([5, 1])
    left.caption(f"Model: {os.getenv('OPENAI_MODEL', 'gpt-5.5')} · Workspace-scoped · Read-only")
    if right.button("Clear chat", key=f"clear_ai_{workspace_id}"):
        st.session_state[state_key] = []
        st.rerun()

    for message in st.session_state[state_key]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ask about customers, orders, revenue, products or payments", key=f"business_ai_input_{workspace_id}")
    if prompt:
        history = list(st.session_state[state_key])
        st.session_state[state_key].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Checking your workspace analytics..."):
                try:
                    response = answer_question(prompt, tables, history=history)
                except Exception as exc:
                    response = f"I couldn't complete that request: {exc}"
                st.markdown(response)
        st.session_state[state_key].append({"role": "assistant", "content": response})
        st.session_state[state_key] = st.session_state[state_key][-12:]
