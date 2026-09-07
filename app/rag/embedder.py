from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.openai_api_key)


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    把每个代码块的内容转成向量，附加到原始数据上返回。
    """
    texts = [chunk["content"] for chunk in chunks]

    response = client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
    )

    for i, chunk in enumerate(chunks):
        chunk["embedding"] = response.data[i].embedding

    return chunks