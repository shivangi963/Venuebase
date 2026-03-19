import os
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer



_embedder = None

def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


#  VECTOR STORE CLASS

class FAISSVectorStore:
    def __init__(self):
        self.index = None         
        self.chunks: list[dict] = []   
        self.dimension: int = 384  # all-MiniLM-L6-v2 output dim

    # BUILD 

    def build(self, chunks: list[dict]) -> None:
        if not chunks:
            raise ValueError("Cannot build vector store from an empty chunk list.")

        embedder = get_embedder()
        texts = [c["text"] for c in chunks]

        print(f"  Embedding {len(texts)} chunks...")
        embeddings = embedder.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True, 
        ).astype("float32")

        self.dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(self.dimension)  # cosine
        self.index.add(embeddings)
        self.chunks = chunks
        print(f"  FAISS index built: {self.index.ntotal} vectors, dim={self.dimension}")

    # QUERY

    def query(self, question: str, top_k: int = 4) -> list[dict]:       
        if self.index is None or self.index.ntotal == 0:
            raise RuntimeError(
                "Vector store is empty. Call build() before querying."
            )

        embedder = get_embedder()
        q_embedding = embedder.encode(
            [question],
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")

        scores, indices = self.index.search(q_embedding, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:          # FAISS returns -1 for missing slots
                continue
            chunk = dict(self.chunks[idx])   # copy so we don't mutate original
            chunk["score"] = float(score)
            results.append(chunk)

        return results

    #  PERSISTENCE 
    def save(self, path: str) -> None:
        """Saves index + metadata to disk."""
        faiss.write_index(self.index, path + ".faiss")
        with open(path + ".meta", "wb") as f:
            pickle.dump(self.chunks, f)

    def load(self, path: str) -> None:
        """Loads index + metadata from disk."""
        self.index = faiss.read_index(path + ".faiss")
        with open(path + ".meta", "rb") as f:
            self.chunks = pickle.load(f)
        self.dimension = self.index.d