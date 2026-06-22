from abc import ABC, abstractmethod

class VectorStore(ABC):
    @abstractmethod
    def upsert_chunks(self, chunks: list[dict]) -> None: ...
