from typing import Generic, TypeVar, Type
from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import select, insert, update, delete
from sqlalchemy.exc import IntegrityError, NoResultFound, MultipleResultsFound

T = TypeVar("T", bound="DeclarativeBase")


class AbstractRepository(ABC):

    @abstractmethod
    async def delete_one():
        raise NotImplementedError

    @abstractmethod
    async def get_one():
        raise NotImplementedError

    @abstractmethod
    async def add_one():
        raise NotImplementedError

    @abstractmethod
    async def update_one():
        raise NotImplementedError

    @abstractmethod
    async def get_all():
        raise NotImplementedError


class SQLAlchemyRepository(AbstractRepository, Generic[T]):
    def __init__(self, session: AsyncSession, model: Type[T]):
        self.session = session
        self.model = model

    async def get_one(self, id: int) -> T | None:
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_one(self, data: dict) -> T:
        stmt = insert(self.model).values(**data).returning(self.model)
        try:
            result = await self.session.execute(stmt)
        except IntegrityError as e:
            raise ValueError(f"Error adding {self.model.__name__}: {e}")
        return result.scalar_one()

    async def update_one(self, id: int, data: dict) -> T:
        stmt = update(self.model).where(self.model.id ==
                                        id).values(**data).returning(self.model)
        result = await self.session.execute(stmt)
        try:
            return result.scalar_one()
        except NoResultFound:
            raise ValueError(f"No {self.model.__name__} found with id={id}")
        except MultipleResultsFound:
            raise ValueError(
                f"Multiple {self.model.__name__} records found with id={id}")

    async def delete_one(self, id: int) -> bool:
        stmt = delete(self.model).where(
            self.model.id == id).returning(self.model)
        result = await self.session.execute(stmt)
        try:
            return result.scalar_one_or_none() is not None
        except NoResultFound:
            raise ValueError(f"No {self.model.__name__} found with id={id}")

    async def get_all(self) -> list[T]:
        stmt = select(self.model)
        result = await self.session.execute(stmt)
        return result.scalars().all()
