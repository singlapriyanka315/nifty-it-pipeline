"""Step 3: semantic search over headlines with ChromaDB.

Postgres is the source of truth; Chroma only stores the embedding + the news id,
so search results are looked up in Postgres afterwards.
"""

import chromadb

from config import CHROMA_PATH


class NewsIndex:
    def __init__(self, path=CHROMA_PATH):
        self.col = chromadb.PersistentClient(path=path).get_or_create_collection("news")

    def add(self, company, articles):
        if not articles:
            return
        self.col.upsert(
            ids=[a["id"] for a in articles],
            documents=[a["title"] for a in articles],  # embeddings are made locally by Chroma
            metadatas=[{"company": company} for _ in articles],
        )

    def search(self, company, query, k=5):
        """Return news ids most similar to the query, for one company."""
        available = len(self.col.get(where={"company": company})["ids"])
        if available == 0:
            return []
        res = self.col.query(query_texts=[query], n_results=min(k, available), where={"company": company})
        return res["ids"][0]
