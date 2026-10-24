"""Collection-scoped PostgreSQL lexical search fused with pgvector results."""
import logging
import os
import re

import psycopg
from langchain_core.documents import Document
from common import vector_store

logger = logging.getLogger(__name__)
TEXT_VECTOR = "to_tsvector('simple', coalesce(e.cmetadata->>'search_text', e.document, ''))"


def normalize(text):
    """Keep identifiers intact and also expose their component words."""
    split = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', text)
    split = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', split)
    return text + ' ' + split.replace('_', ' ')


def connection():
    url = os.getenv('DATABASE_URL', 'postgresql+psycopg://rag:rag@localhost:5432/payment_rag')
    return psycopg.connect(url.replace('postgresql+psycopg://', 'postgresql://', 1))


def ensure_keyword_index():
    # Index the same rows as vector search: deletes and rebuilds stay synchronized.
    with connection() as conn:
        conn.execute("""CREATE INDEX IF NOT EXISTS payment_chunks_fts_idx
            ON langchain_pg_embedding USING GIN
            (to_tsvector('simple', coalesce(cmetadata->>'search_text', document, '')))""")


def exact_terms(query):
    """Explicit phrases and code-like identifiers receive literal-match priority."""
    phrases = re.findall(r'"([^"\n]+)"|`([^`\n]+)`', query)
    terms = [a or b for a, b in phrases]
    terms.extend(t for t in re.findall(r'\b[A-Za-z][A-Za-z0-9_.-]*\b', query)
                 if '_' in t or re.search(r'[a-z][A-Z]|[A-Z]{2,}|\d', t))
    if len(query.split()) == 1 and query.strip():
        terms.append(query.strip())
    return list(dict.fromkeys(t.lower() for t in terms if t.strip()))[:40]


def literal_matches(text, terms):
    return sum(bool(re.search(r'(?<!\w)' + re.escape(t) + r'(?!\w)', text, re.I)) for t in terms)


def keyword_search(query, k):
    tokens = list(dict.fromkeys(re.findall(r'[a-z0-9_]+', normalize(query).lower())))[:160]
    if not tokens:
        return []
    # OR lets prose questions find relevant chunks without requiring every word.
    tsquery = ' | '.join(tokens)
    terms = exact_terms(query)
    patterns = [r'\m' + re.escape(t) + r'\M' for t in terms]
    sql = f"""SELECT e.id, e.document, e.cmetadata,
        (SELECT count(*) FROM unnest(%s::text[]) AS p(pattern)
         WHERE e.document ~* p.pattern) AS exact_hits,
        ts_rank_cd({TEXT_VECTOR}, to_tsquery('simple', %s)) AS rank
        FROM langchain_pg_embedding e
        JOIN langchain_pg_collection c ON c.uuid = e.collection_id
        WHERE c.name = %s AND
          ({TEXT_VECTOR} @@ to_tsquery('simple', %s)
           OR EXISTS (SELECT 1 FROM unnest(%s::text[]) AS p(pattern)
                      WHERE e.document ~* p.pattern))
        ORDER BY exact_hits DESC, rank DESC, e.id LIMIT %s"""
    with connection() as conn:
        rows = conn.execute(sql, (patterns, tsquery,
            os.getenv('COLLECTION_NAME', 'payment_code_chunks'), tsquery, patterns, k)).fetchall()
    return [Document(id=row[0], page_content=row[1], metadata=row[2] or {}) for row in rows]


def fuse(vector_docs, keyword_docs, query, k):
    scores, docs = {}, {}
    for results in (vector_docs, keyword_docs):
        seen = set()
        for rank, doc in enumerate(results, 1):
            key = doc.metadata.get('chunk_id') or doc.id or (
                doc.metadata.get('source'), doc.metadata.get('start_index'), doc.page_content)
            if key in seen:
                continue
            seen.add(key)
            docs[key] = doc
            scores[key] = scores.get(key, 0) + 1 / (60 + rank)
    terms = exact_terms(query)
    ordered = sorted(docs, key=lambda key: (
        -literal_matches(docs[key].page_content, terms), -scores[key], str(key)))
    return [docs[key] for key in ordered[:k]]


def positive_setting(name, default):
    value = int(os.getenv(name, str(default)))
    if not 1 <= value <= 200:
        raise ValueError(f'{name} must be between 1 and 200')
    return value


def retrieve(query):
    mode = os.getenv('SEARCH_MODE', 'hybrid').lower()
    if mode not in {'hybrid', 'vector', 'keyword'}:
        raise ValueError('SEARCH_MODE must be hybrid, vector, or keyword')
    final_k = positive_setting('FINAL_TOP_K', 5)
    if not query.strip():
        return []
    vectors, keywords, errors = [], [], []
    if mode != 'keyword':
        try:
            vectors = vector_store().similarity_search(query, k=positive_setting('VECTOR_TOP_K', 20))
        except Exception as exc:
            errors.append(exc)
            logger.warning('Vector search unavailable; attempting keyword search', exc_info=True)
    if mode != 'vector':
        try:
            keywords = keyword_search(query, positive_setting('KEYWORD_TOP_K', 20))
        except Exception as exc:
            errors.append(exc)
            logger.warning('Keyword search unavailable; using vector results if available', exc_info=True)
    if errors and not vectors and not keywords:
        raise RuntimeError('Retrieval failed; check database availability and run ingest.py') from errors[0]
    return fuse(vectors, keywords, query, final_k)
