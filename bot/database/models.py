from sqlalchemy import (
    String, ForeignKey, Boolean, 
    DateTime, BigInteger, Integer
    )
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from uuid import uuid4

from .base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(255), index=True)
    locale: Mapped[str] = mapped_column(String(10),default="ru")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="user")
    subscriptions: Mapped[list["Subscription"]
                          ] = relationship(back_populates="user")
    employees: Mapped[list["Employee"]] = relationship(back_populates="owner")
    payments: Mapped[list["Payment"]] = relationship(back_populates="user")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", name='fk_user_id'), index=True)
    title: Mapped[str] = mapped_column(String(100))
    key_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="api_keys")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", name='fk_user_id'), index=True)
    # trial, monthly, quarterly, yearly
    plan: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(), default=datetime.now(), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime())

    user: Mapped["User"] = relationship(back_populates="subscriptions")
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="subscription")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    owner: Mapped["User"] = relationship(back_populates="employees")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), index=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id"), nullable=True)

    amount: Mapped[int] = mapped_column(Integer)  # В копейках
    # 'pending', 'succeeded', 'failed', etc
    status: Mapped[str] = mapped_column(String(50))
    payment_id: Mapped[str] = mapped_column(String(255),
        unique=True, index=True)  # ID от ЮKassa
    description: Mapped[str] = mapped_column(String(255), nullable=True)

    paid_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)

    user: Mapped["User"] = relationship(back_populates="payments")
    subscription: Mapped["Subscription"] = relationship(
        back_populates="payments")


if __name__ == '__main__':
    print(f'{__name__} Запущен самостоятельно')
else:
    print(f'{__name__} Запущен как модуль')
