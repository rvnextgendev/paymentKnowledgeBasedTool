import os
from pathlib import Path
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))
API = os.getenv("API_URL", "http://localhost:8000")
st.set_page_config(page_title="Payment RAG AI", page_icon="💳", layout="wide")
st.title("💳 Payment RAG AI")
st.caption("Developer knowledge assistant • LangChain • LangGraph • pgvector • Groq / Ollama")
with st.sidebar:
    st.header("Configuration")
    st.write("Backend:", API)
    st.write("Provider:", os.getenv("LLM_PROVIDER", "groq"))
    st.info("Change LLM_PROVIDER in .env and restart FastAPI to switch models.")
    try:
        response = requests.get(f"{API}/openapi.json", timeout=3)
        if response.ok:
            st.success("API reachable")
        else:
            st.warning("API unavailable")
    except requests.RequestException:
        st.warning("Start FastAPI first")

chat, review, knowledge = st.tabs(["💬 Developer Chat", "🔍 Code Review", "📚 Knowledge Base"])
with chat:
    question = st.text_area("Ask about payment code", "What happens if zero-value payments are allowed?")
    if st.button("Ask AI", type="primary"):
        try:
            with st.spinner("Retrieving code and asking AI..."):
                r=requests.post(f"{API}/ask",json={"question":question},timeout=180)
                r.raise_for_status()
                data=r.json()
            st.markdown(data["answer"])
            with st.expander("Retrieved sources"):
                for source in data.get("sources", []): st.code(source)
        except requests.RequestException as exc: st.error(str(exc))
with review:
    diff = st.text_area("Paste Git diff", "- if (request.Amount <= 0)\n+ if (request.Amount < 0)", height=150)
    if st.button("Analyze change", type="primary"):
        try:
            with st.spinner("Reviewing change..."):
                r=requests.post(f"{API}/review",json={"diff":diff},timeout=180)
                r.raise_for_status()
                data=r.json()
            st.markdown(data["review"])
            with st.expander("Retrieved sources"):
                for source in data.get("sources", []): st.code(source)
        except requests.RequestException as exc: st.error(str(exc))
with knowledge:
    st.subheader("Indexed inputs")
    st.write("Sample .NET payment source, business rules, and change history.")
    st.code("cd rag-service\npython ingest.py",language="bash")
    st.info("Run ingestion after updating code or documents. The current demo rebuilds its index.")
    st.write("GitHub PR review runs separately through the included Actions workflow.")
