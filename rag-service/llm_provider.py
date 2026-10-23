import os
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

def get_llm():
    provider = os.getenv("LLM_PROVIDER", "groq").lower()
    if provider == "ollama":
        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3.2:latest"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0,
        )
    if provider == "groq":
        return ChatGroq(
            model=os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b"),
            temperature=0,
            max_tokens=700,
        )
    raise ValueError(f"Unsupported provider: {provider}")
