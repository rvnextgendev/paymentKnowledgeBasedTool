import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres import PGVector
load_dotenv(Path(__file__).with_name('.env'))

def vector_store():
    return PGVector(
        embeddings=HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2'),
        collection_name=os.getenv('COLLECTION_NAME','payment_code_chunks'),
        connection=os.getenv('DATABASE_URL','postgresql+psycopg://rag:rag@localhost:5432/payment_rag'),
        use_jsonb=True)
