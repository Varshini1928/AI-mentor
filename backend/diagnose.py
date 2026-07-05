import os
import sys
from dotenv import load_dotenv

load_dotenv(".env")
print("1. .env loaded", flush=True)

print("2. QDRANT_URL =", os.environ.get("QDRANT_URL"), flush=True)

from qdrant_client import QdrantClient
print("3. qdrant_client imported", flush=True)

client = QdrantClient(
    url=os.environ.get("QDRANT_URL"),
    api_key=os.environ.get("QDRANT_API_KEY"),
    timeout=60,
)
print("4. QdrantClient created", flush=True)

collections = client.get_collections()
print("5. get_collections() succeeded:", collections, flush=True)

from sentence_transformers import SentenceTransformer
print("6. sentence_transformers imported", flush=True)

embedder = SentenceTransformer("all-MiniLM-L6-v2")
print("7. SentenceTransformer model loaded", flush=True)

vec = embedder.encode(["hello world"]).tolist()
print("8. Encoded a test sentence, vector length:", len(vec[0]), flush=True)

print("ALL STEPS PASSED", flush=True)