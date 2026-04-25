from openai import OpenAI
from dotenv import load_dotenv
from chromadb import PersistentClient
from pydantic import BaseModel, Field
from pathlib import Path
from tenacity import retry, wait_exponential, stop_after_attempt
import os

from pro_implementation.ingest import build_preprocessed_db

load_dotenv(override=True)

MODEL = "gpt-4.1-nano"
DB_NAME = str(Path(__file__).parent.parent / "preprocessed_db")
COLLECTION_NAME = "docs"
EMBEDDING_MODEL = "text-embedding-3-large"

RETRIEVAL_K = 8
FINAL_K = 5

wait = wait_exponential(multiplier=1, min=1, max=6)

SYSTEM_PROMPT = """
You are a knowledgeable, friendly assistant representing the company Insurellm.
You are chatting with a user about Insurellm.

Answer only from the provided context when possible.
If the answer is not in the context, say you do not know based on the knowledge base.
Be accurate, relevant, and concise.

Context:
{context}
""".strip()


class Result(BaseModel):
    page_content: str
    metadata: dict


class RankOrder(BaseModel):
    order: list[int] = Field(
        description="The order of relevance of chunks, from most relevant to least relevant, by chunk id number"
    )


api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY is not set.")

openai_client = OpenAI(api_key=api_key)

db_path = Path(DB_NAME)

# Build once if missing
if not db_path.exists():
    print(f"{DB_NAME} not found. Building preprocessed DB...")
    build_preprocessed_db()

chroma = PersistentClient(path=DB_NAME)
collection = chroma.get_or_create_collection(COLLECTION_NAME)

if collection.count() == 0:
    print(f"Collection '{COLLECTION_NAME}' is empty. Building preprocessed DB...")
    build_preprocessed_db()
    chroma = PersistentClient(path=DB_NAME)
    collection = chroma.get_or_create_collection(COLLECTION_NAME)


@retry(wait=wait, stop=stop_after_attempt(3), reraise=True)
def rewrite_query(question, history=None):
    if history is None:
        history = []

    prompt = f"""
You are rewriting a user question for semantic retrieval.
Conversation history:
{history}

Current question:
{question}

Return only one short retrieval query.
""".strip()

    response = openai_client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": prompt}],
        temperature=0,
    )
    return response.choices[0].message.content.strip()


@retry(wait=wait, stop=stop_after_attempt(3), reraise=True)
def rerank(question, chunks):
    if not chunks:
        return []

    chunk_text = ""
    for idx, chunk in enumerate(chunks, start=1):
        chunk_text += f"# CHUNK ID: {idx}\n{chunk.page_content}\n\n"

    prompt = f"""
You are a document reranker.

Question:
{question}

Chunks:
{chunk_text}

Return only a Python-style list of chunk ids ordered from most relevant to least relevant.
Example: [3, 1, 2]
""".strip()

    response = openai_client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": prompt}],
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()

    try:
        order = eval(raw, {"__builtins__": {}})
        if not isinstance(order, list):
            raise ValueError("Reranker response is not a list.")
        return [chunks[i - 1] for i in order if isinstance(i, int) and 1 <= i <= len(chunks)]
    except Exception:
        return chunks


def merge_chunks(chunks1, chunks2):
    merged = []
    seen = set()

    for chunk in chunks1 + chunks2:
        key = chunk.page_content
        if key not in seen:
            seen.add(key)
            merged.append(chunk)

    return merged


def fetch_context_unranked(question):
    query_embedding = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[question],
    ).data[0].embedding

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=RETRIEVAL_K,
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    chunks = []
    for doc, metadata in zip(documents, metadatas):
        chunks.append(Result(page_content=doc, metadata=metadata or {}))

    return chunks


def fetch_context(original_question, history=None):
    if history is None:
        history = []

    rewritten_question = rewrite_query(original_question, history)
    chunks1 = fetch_context_unranked(original_question)
    chunks2 = fetch_context_unranked(rewritten_question)
    merged = merge_chunks(chunks1, chunks2)

    if not merged:
        return []

    reranked = rerank(original_question, merged)
    return reranked[:FINAL_K]


def make_rag_messages(question, history, chunks):
    context = "\n\n".join(
        f"Extract from {chunk.metadata.get('source', 'unknown source')}:\n{chunk.page_content}"
        for chunk in chunks
    )

    system_prompt = SYSTEM_PROMPT.format(context=context)

    return (
        [{"role": "system", "content": system_prompt}]
        + history
        + [{"role": "user", "content": question}]
    )


@retry(wait=wait, stop=stop_after_attempt(3), reraise=True)
def answer_question(question: str, history=None) -> tuple[str, list]:
    if history is None:
        history = []

    chunks = fetch_context(question, history)

    if not chunks:
        return (
            "I could not find relevant information in the knowledge base.",
            []
        )

    messages = make_rag_messages(question, history, chunks)

    response = openai_client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.2,
    )

    answer = response.choices[0].message.content.strip()
    return answer, chunks