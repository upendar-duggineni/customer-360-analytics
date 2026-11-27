"""Compact corner chat launcher for the active business workspace."""
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
    """Render a Gemini-powered chat popover aligned to the dashboard's top-right."""
    state_key = f"business_ai_history_{workspace_id}"
    st.session_state.setdefault(state_key, [])

    with st.popover("💬 Ask AI", use_container_width=True):
        st.markdown("### Customer 360 Assistant")
        st.caption("Your workspace data analyst · Read-only analytics")

        if not get_api_key():
            st.info("Add your Gemini API key to enable the assistant.")
            st.code("GEMINI_API_KEY=your_gemini_api_key\nAI_PROVIDER=gemini\nGEMINI_MODEL=gemini-3.8-flash\nGEMINI_FALLBACK_MODEL=gemini-3.1-flash-lite-preview", language="bash")
            st.caption("Add these to your local .env file. Never paste your key into chat or commit it to GitHub.")
            return

        st.caption(f"Provider: Gemini · Model: {os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')}")
        st.caption(f"Backup model: {os.getenv('GEMINI_FALLBACK_MODEL', 'gemini-3.1-flash-lite-preview')}")
        if st.button("Clear conversation", key=f"clear_ai_{workspace_id}", use_container_width=True):
            st.session_state[state_key] = []
            st.rerun()

        history = st.session_state[state_key]
        if not history:
            st.markdown("**Try asking:**")
            for index, suggestion in enumerate(SUGGESTED_QUESTIONS):
                if st.button(suggestion, key=f"ai_suggestion_{workspace_id}_{index}", use_container_width=True):
                    st.session_state[f"business_ai_pending_{workspace_id}"] = suggestion
                    st.rerun()

        with st.container(height=360, border=True):
            for message in history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

        pending_key = f"business_ai_pending_{workspace_id}"
        with st.form(f"business_ai_form_{workspace_id}", clear_on_submit=True):
            prompt = st.text_input("Ask about customers, orders, revenue, products or payments", key=f"business_ai_prompt_{workspace_id}")
            submitted = st.form_submit_button("Send", type="primary", use_container_width=True)

        pending = st.session_state.pop(pending_key, None)
        question = pending or (prompt.strip() if submitted else "")
        if question:
            previous_history = list(st.session_state[state_key])
            st.session_state[state_key].append({"role": "user", "content": question})
            try:
                response = answer_question(question, tables, history=previous_history)
            except Exception as exc:
                response = f"I couldn't complete that request: {exc}"
            st.session_state[state_key].append({"role": "assistant", "content": response})
            st.session_state[state_key] = st.session_state[state_key][-12:]
            st.rerun()
