import os
import chromadb
import httpx

# Initialize ChromaDB (ephemeral /tmp on Vercel, local otherwise)
db_path = "/tmp/chromadb_data" if os.getenv("VERCEL") else "./chromadb_data"
chroma_client = chromadb.PersistentClient(path=db_path)
collection = chroma_client.get_or_create_collection(
    name="user_longterm_memory",
    metadata={"hnsw:space": "cosine"}
)

def get_embedding(text: str) -> list:
    api_url = "https://api-inference.huggingface.co/pipeline/feature-extraction/sentence-transformers/all-MiniLM-L6-v2"
    token = os.getenv("HF_TOKEN")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        response = httpx.post(api_url, headers=headers, json={"inputs": text}, timeout=10.0)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"HF API Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Embedding generation failed: {e}")
        # Return a dummy 384-dimensional vector if the API fails, to prevent app crashing
        return [0.0] * 384


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