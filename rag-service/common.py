import os
from pathlib import Path
from threading import Lock
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector
load_dotenv(Path(__file__).with_name('.env'))

# PGVector registers SQLAlchemy models during initialization. Share one instance
# per process and serialize first access from concurrent FastAPI requests.
_store = None
_store_lock = Lock()

def vector_store():
    global _store
    with _store_lock:
        if _store is None:
            _store = PGVector(
                embeddings=HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2'),
                collection_name=os.getenv('COLLECTION_NAME','payment_code_chunks'),
                connection=os.getenv('DATABASE_URL','postgresql+psycopg://rag:rag@localhost:5432/payment_rag'),
                use_jsonb=True)
        return _store
