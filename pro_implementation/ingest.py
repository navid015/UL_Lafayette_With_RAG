from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from chromadb import PersistentClient
import hashlib
import os

load_dotenv(override=True)

DB_NAME = str(Path(__file__).parent.parent / "preprocessed_db")
COLLECTION_NAME = "docs"
EMBEDDING_MODEL = "text-embedding-3-large"
KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "knowledge-base"

# Lighter/faster local chunking for Spaces
CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set.")

openai_client = OpenAI(api_key=api_key)


def fetch_documents():
    documents = []

    if not KNOWLEDGE_BASE_PATH.exists():
        raise FileNotFoundError(f"Knowledge base folder not found: {KNOWLEDGE_BASE_PATH}")

    for folder in KNOWLEDGE_BASE_PATH.iterdir():
        if not folder.is_dir():
            continue

        doc_type = folder.name
        for file in folder.rglob("*.md"):
            with open(file, "r", encoding="utf-8") as f:
                documents.append(
                    {
                        "type": doc_type,
                        "source": file.as_posix(),
                        "text": f.read(),
                    }
                )

    print(f"Loaded {len(documents)} documents")
    return documents


def split_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    text = text.strip()
    if not text:
        return []

    chunks = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= text_len:
            break

        start = max(end - overlap, start + 1)

    return chunks


def create_chunks(documents):
    chunks = []

    for document in documents:
        text_chunks = split_text(document["text"])

        for i, chunk_text in enumerate(text_chunks):
            page_content = f"Source: {document['source']}\nType: {document['type']}\n\n{chunk_text}"
            metadata = {
                "source": document["source"],
                "type": document["type"],
                "chunk_index": i,
            }
            chunks.append({"page_content": page_content, "metadata": metadata})

    print(f"Created {len(chunks)} chunks")
    return chunks


def batched(iterable, batch_size):
    for i in range(0, len(iterable), batch_size):
        yield iterable[i:i + batch_size]


def create_embeddings(chunks):
    db_path = Path(DB_NAME)
    db_path.mkdir(parents=True, exist_ok=True)

    chroma = PersistentClient(path=DB_NAME)

    existing_names = [c.name for c in chroma.list_collections()]
    if COLLECTION_NAME in existing_names:
        chroma.delete_collection(COLLECTION_NAME)

    collection = chroma.get_or_create_collection(COLLECTION_NAME)

    texts = [chunk["page_content"] for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]

    all_ids = []
    all_embeddings = []
    all_documents = []
    all_metadatas = []

    batch_size = 100

    for batch_index, batch in enumerate(batched(list(range(len(texts))), batch_size)):
        batch_texts = [texts[i] for i in batch]
        batch_metas = [metadatas[i] for i in batch]

        emb_response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch_texts,
        )

        batch_embeddings = [item.embedding for item in emb_response.data]
        batch_ids = [
            hashlib.md5(f"{batch_metas[idx]['source']}::{batch_metas[idx]['chunk_index']}".encode()).hexdigest()
            for idx in range(len(batch_metas))
        ]

        all_ids.extend(batch_ids)
        all_embeddings.extend(batch_embeddings)
        all_documents.extend(batch_texts)
        all_metadatas.extend(batch_metas)

        print(f"Embedded batch {batch_index + 1}")

    collection.add(
        ids=all_ids,
        embeddings=all_embeddings,
        documents=all_documents,
        metadatas=all_metadatas,
    )

    print(f"Vectorstore created with {collection.count()} documents")


def build_preprocessed_db():
    documents = fetch_documents()
    chunks = create_chunks(documents)
    create_embeddings(chunks)
    print("Ingestion complete")


if __name__ == "__main__":
    build_preprocessed_db()