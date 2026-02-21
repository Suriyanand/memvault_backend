import os
import chromadb
from sentence_transformers import SentenceTransformer

# Initialize ChromaDB (local, free)
chroma_client = chromadb.PersistentClient(path="./chromadb_data")
collection = chroma_client.get_or_create_collection(
    name="user_longterm_memory",
    metadata={"hnsw:space": "cosine"}
)

# Free embeddings model
embedder = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text: str) -> list:
    return embedder.encode(text).tolist()

async def save_longterm_memory(user_id: str, facts: dict):
    """Save extracted user facts to vector DB"""
    for key, value in facts.items():
        if not value:
            continue
        
        fact_text = f"{key}: {value}"
        embedding = get_embedding(fact_text)
        doc_id = f"{user_id}_{key}_{hash(str(value))}"
        
        collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[fact_text],
            metadatas=[{"user_id": user_id, "fact_type": key}]
        )

async def search_longterm_memory(user_id: str, query: str, top_k: int = 3) -> list:
    """Semantic search for relevant user facts"""
    query_embedding = get_embedding(query)
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={"user_id": user_id}
    )
    
    if results and results["documents"]:
        return results["documents"][0]
    return []

async def delete_user_memory(user_id: str):
    """Delete all memories for a user"""
    results = collection.get(where={"user_id": user_id})
    if results["ids"]:
        collection.delete(ids=results["ids"])