from __future__ import annotations

from pathlib import Path
import hashlib
import math
import re

from langchain_core.documents import Document


COLLECTION_NAME = "educs_knowledge"
EMBEDDING_DIM = 384
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHROMA_PATH = PROJECT_ROOT / "data" / "chroma"


def retrieve_knowledge(query: str, knowledge_dir: str | Path, top_k: int = 3) -> list[dict]:
    docs = split_documents(load_knowledge_documents(knowledge_dir))
    chroma_hits = _retrieve_with_chroma(query, docs, top_k)
    if chroma_hits is not None:
        return chroma_hits

    scored = [
        {
            "source": str(doc.metadata["source"]),
            "chunk_id": str(doc.metadata["chunk_id"]),
            "text": doc.page_content,
            "score": _score(query, doc.page_content),
            "retriever": "keyword_fallback",
        }
        for doc in docs
    ]
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]


def load_knowledge_documents(knowledge_dir: str | Path) -> list[Document]:
    root = Path(knowledge_dir)
    documents = []
    for path in sorted(root.glob("*.md")):
        documents.append(
            Document(
                page_content=path.read_text(encoding="utf-8"),
                metadata={"source": path.name},
            )
        )
    return documents


def split_documents(documents: list[Document]) -> list[Document]:
    chunks = []
    for doc in documents:
        parts = _split_markdown(doc.page_content)
        for idx, part in enumerate(parts):
            chunks.append(
                Document(
                    page_content=part,
                    metadata={**doc.metadata, "chunk_id": idx},
                )
            )
    return chunks


def embed_text(text: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIM
    tokens = _tokens(text)
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIM
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _retrieve_with_chroma(query: str, docs: list[Document], top_k: int) -> list[dict] | None:
    if not docs:
        return []

    try:
        import chromadb
    except Exception:
        return None

    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(name=COLLECTION_NAME)
    ids = [f"{doc.metadata['source']}:{doc.metadata['chunk_id']}" for doc in docs]

    collection.upsert(
        ids=ids,
        documents=[doc.page_content for doc in docs],
        metadatas=[doc.metadata for doc in docs],
        embeddings=[embed_text(doc.page_content) for doc in docs],
    )

    result = collection.query(query_embeddings=[embed_text(query)], n_results=min(top_k, len(docs)))
    hits = []
    for idx, doc_text in enumerate(result.get("documents", [[]])[0]):
        metadata = result.get("metadatas", [[]])[0][idx]
        distance = result.get("distances", [[]])[0][idx]
        hits.append(
            {
                "source": str(metadata["source"]),
                "chunk_id": str(metadata["chunk_id"]),
                "text": doc_text,
                "score": round(1 / (1 + float(distance)), 4),
                "retriever": "chroma_hash_embedding",
            }
        )
    return rerank_by_keyword(query, hits)


def rerank_by_keyword(query: str, hits: list[dict]) -> list[dict]:
    reranked = []
    for hit in hits:
        keyword_score = _score(query, hit["text"])
        merged = {**hit}
        merged["keyword_score"] = round(keyword_score, 4)
        merged["final_score"] = round(hit["score"] * 0.75 + keyword_score * 0.25, 4)
        reranked.append(merged)
    return sorted(reranked, key=lambda item: item["final_score"], reverse=True)


def _split_markdown(text: str) -> list[str]:
    sections = re.split(r"\n(?=#)", text)
    chunks = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        if len(section) <= 700:
            chunks.append(section)
            continue
        paragraphs = [part.strip() for part in section.split("\n\n") if part.strip()]
        current = ""
        for paragraph in paragraphs:
            if len(current) + len(paragraph) > 700 and current:
                chunks.append(current.strip())
                current = paragraph
            else:
                current = f"{current}\n\n{paragraph}".strip()
        if current:
            chunks.append(current.strip())
    return chunks


def _score(query: str, text: str) -> float:
    query_tokens = _tokens(query)
    text_tokens = _tokens(text)
    if not query_tokens or not text_tokens:
        return 0.0
    overlap = len(query_tokens.intersection(text_tokens))
    return overlap / max(len(query_tokens), 1)


def _tokens(text: str) -> set[str]:
    lowered = text.lower()
    english = set(re.findall(r"[a-z0-9_]+", lowered))
    chinese = set(re.findall(r"[\u4e00-\u9fff]", lowered))
    return english.union(chinese)
