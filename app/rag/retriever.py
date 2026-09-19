from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from app.core.config import settings
from app.rag.embedder import embed_chunks

COLLECTION_NAME = "pr_chunks"
VECTOR_SIZE = 1536

qdrant = QdrantClient(location=settings.qdrant_url)
#trigger test


def store_chunks(chunks: list[dict]) -> None:
    existing = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION_NAME in existing:
        qdrant.delete_collection(COLLECTION_NAME)

    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )

    points = []
    for i, chunk in enumerate(chunks):
        points.append(
            PointStruct(
                id=i,
                vector=chunk["embedding"],
                payload={"filename": chunk["filename"], "content": chunk["content"]},
            )
        )

    qdrant.upsert(collection_name=COLLECTION_NAME, points=points)


def search_chunks(query: str, top_k: int = 5) -> list[dict]:
    query_chunks = embed_chunks([{"filename": "", "content": query}])
    query_vector = query_chunks[0]["embedding"]

    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=top_k,
    ).points

    return [
        {
            "filename": r.payload["filename"],
            "content": r.payload["content"],
            "score": r.score,
        }
        for r in results
    ]