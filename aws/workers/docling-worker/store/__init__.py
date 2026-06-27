from .opensearch_store import OpenSearchStore


def get_store() -> OpenSearchStore:
    return OpenSearchStore()
