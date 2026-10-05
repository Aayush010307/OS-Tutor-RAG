"""Qdrant vector store in local (embedded) mode: persisted on disk, no server, Docker or account.

This is the only module that talks to Qdrant. The index is derived data; canonical chunks stay in
data/chunks/chunks.jsonl.
"""
import uuid

from qdrant_client import QdrantClient, models

POINT_NAMESPACE = uuid.NAMESPACE_URL


def point_id(chunk_id):
    """Deterministic Qdrant point id for a chunk id (Qdrant ids must be ints or UUIDs)."""
    return str(uuid.uuid5(POINT_NAMESPACE, f"os-tutor-rag:{chunk_id}"))


class QdrantStore:
    def __init__(self, path):
        # ponytail: local mode does exact brute-force search in numpy, fine for thousands of points;
        # switch to a Qdrant server (same client API, url= instead of path=) past ~20k points.
        self.path = str(path)
        self.client = QdrantClient(path=self.path)

    def exists(self, name):
        return self.client.collection_exists(name)

    def recreate(self, name, dim):
        if self.exists(name):
            self.client.delete_collection(name)
        self.client.create_collection(name, vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE))

    def upsert(self, name, ids, vectors, payloads, batch=128):
        for i in range(0, len(ids), batch):
            self.client.upsert(name, points=[models.PointStruct(id=pid, vector=vec.tolist(), payload=pl)
                                             for pid, vec, pl in zip(ids[i:i + batch], vectors[i:i + batch], payloads[i:i + batch])])

    def count(self, name):
        return self.client.count(name, exact=True).count

    def config(self, name):
        params = self.client.get_collection(name).config.params.vectors
        return {"dim": params.size, "distance": params.distance.value}

    def search(self, name, vector, top_k, filters=None):
        """filters: {field: value or [values]}; all fields must match, a list matches any of its values."""
        hits = self.client.query_points(name, query=vector.tolist(), limit=top_k, query_filter=_to_filter(filters),
                                        with_payload=True).points
        return [(h.id, h.score, h.payload) for h in hits]

    def all_points(self, name):
        points, offset = [], None
        while True:
            batch, offset = self.client.scroll(name, limit=256, offset=offset, with_payload=True, with_vectors=True)
            points += batch
            if offset is None:
                return points

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _to_filter(filters):
    if not filters:
        return None
    must = []
    for key, value in filters.items():
        if isinstance(value, (list, tuple)):
            must.append(models.FieldCondition(key=key, match=models.MatchAny(any=list(value))))
        else:
            must.append(models.FieldCondition(key=key, match=models.MatchValue(value=value)))
    return models.Filter(must=must)
