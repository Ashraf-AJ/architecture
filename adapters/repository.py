from abc import ABC, abstractmethod
from typing import List
from domain import model


class RepositoryBase(ABC):
    @abstractmethod
    def add(self, batch: model.Batch) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, reference: str) -> model.Batch:
        raise NotImplementedError


class SqlAlchemyRepository(RepositoryBase):
    def __init__(self, session):
        self.session = session

    def add(self, batch: model.Batch) -> None:
        self.session.add(batch)

    def get(self, reference: str) -> model.Batch:
        return (
            self.session.query(model.Batch)
            .filter_by(reference=reference)
            .first()
        )

    def list(self) -> List[model.Batch]:
        return self.session.query(model.Batch).all()
