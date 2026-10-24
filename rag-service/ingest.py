from pathlib import Path
import hashlib
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from common import vector_store
from retrieval import normalize, ensure_keyword_index
ROOT=Path(__file__).resolve().parent.parent
EXT={'.cs','.md','.json','.yaml','.yml'}
SKIP={'.git','.venv','bin','obj','node_modules'}

def main():
    documents=[]
    for directory in (ROOT/'sample-payment-api', ROOT/'knowledge'):
        for path in directory.rglob('*'):
            if not path.is_file() or path.suffix.lower() not in EXT or any(part in SKIP for part in path.parts) or path.stat().st_size>2_000_000:
                continue
            try: content=path.read_text(encoding='utf-8')
            except (UnicodeError,OSError): continue
            if content.strip(): documents.append(Document(page_content=content,metadata={'source':str(path.relative_to(ROOT))}))
    chunks=RecursiveCharacterTextSplitter(chunk_size=1200,chunk_overlap=200,add_start_index=True).split_documents(documents)
    ids=[hashlib.sha256(f"{d.metadata['source']}:{d.metadata.get('start_index',0)}:{d.page_content}".encode()).hexdigest() for d in chunks]
    for chunk, chunk_id in zip(chunks, ids):
        chunk.metadata['chunk_id'] = chunk_id
        chunk.metadata['search_text'] = normalize(chunk.page_content + ' ' + chunk.metadata['source'])
    store=vector_store()
    # Demo-only full rebuild: do not run concurrently with live queries.
    store.delete_collection()
    store.create_collection()
    for offset in range(0,len(chunks),64): store.add_documents(chunks[offset:offset+64],ids=ids[offset:offset+64])
    ensure_keyword_index()
    print(f'Indexed {len(chunks)} chunks for vector and keyword search')
if __name__=='__main__': main()
