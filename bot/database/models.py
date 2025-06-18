from sqlalchemy import (
    Numeric, String, ForeignKey, Boolean,
    DateTime, BigInteger, Integer, UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime


class Base(DeclarativeBase):
    created: Mapped[datetime] = mapped_column(DateTime(), default=datetime.now)
    updated: Mapped[datetime] = mapped_column(
        DateTime(), default=datetime.now, onupdate=datetime.now)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(255), index=True)
    locale: Mapped[str] = mapped_column(String(10), default="ru")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="user")
    subscriptions: Mapped[list["Subscription"]
                          ] = relationship(back_populates="user")
    employees: Mapped[list["Employee"]] = relationship(back_populates="owner")
    employee_invites: Mapped[list["EmployeeInvite"]
                             ] = relationship(back_populates="owner")
    payments: Mapped[list["Payment"]] = relationship(back_populates="user")
    orders: Mapped[list["OrdersWB"]] = relationship(back_populates="user")
    task_statuses: Mapped[list["TaskStatus"]
                          ] = relationship(back_populates="user")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", name='fk_user_id'), index=True)
    title: Mapped[str] = mapped_column(String(100), default="API Key")
    key_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship(back_populates="api_keys")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True)
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

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    username: Mapped[str] = mapped_column(
        String(255), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    owner: Mapped["User"] = relationship(back_populates="employees")


class EmployeeInvite(Base):
    __tablename__ = "employee_invites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)

    owner: Mapped["User"] = relationship(back_populates="employee_invites")


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


class OrdersWB(Base):
    __tablename__ = 'wb_orders'

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True)
    last_change_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True)
    supplier_article: Mapped[str] = mapped_column(String(75), nullable=False)
    tech_size: Mapped[str] = mapped_column(String(50), nullable=False)
    barcode: Mapped[str] = mapped_column(String(255), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False)
    finished_price: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=True)
    discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False)
    spp: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=True)
    warehouse_name: Mapped[str] = mapped_column(String(50), nullable=False)
    region_name: Mapped[str] = mapped_column(String(200), nullable=False)
    oblast_okrug_name: Mapped[str] = mapped_column(String(200), nullable=True)
    country_name: Mapped[str] = mapped_column(String(200), nullable=True)
    income_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    nm_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    brand: Mapped[str] = mapped_column(String(50), nullable=False)
    is_cancel: Mapped[bool] = mapped_column(Boolean, nullable=False)
    cancel_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    g_number: Mapped[str] = mapped_column(String(60), nullable=False)
    sticker: Mapped[str] = mapped_column(String(255), nullable=False)
    srid: Mapped[str] = mapped_column(String(255), nullable=True)
    price_with_disc: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=True)
    is_supply: Mapped[bool] = mapped_column(
        Boolean, nullable=True, comment="Договор поставки")
    is_realization: Mapped[bool] = mapped_column(
        Boolean, nullable=True, comment="Договор реализации")
    warehouse_type: Mapped[str] = mapped_column(
        String(60), nullable=True, comment="Тип склада")

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    user: Mapped["User"] = relationship(back_populates="orders")

    __table_args__ = (UniqueConstraint(
        'date', 'user_id', 'srid', 'nm_id', 'is_cancel', 'tech_size',
        name='unique_order'),)


class SalesWB(Base):
    __tablename__ = 'wb_sales'

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True)
    last_change_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True)
    warehouse_name: Mapped[str] = mapped_column(String(255), nullable=False)
    country_name: Mapped[str] = mapped_column(String(255), nullable=True)
    oblast_okrug_name: Mapped[str] = mapped_column(String(255), nullable=True)
    region_name: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier_article: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True)
    nm_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True,)
    barcode: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str] = mapped_column(String(255), nullable=False)
    tech_size: Mapped[str] = mapped_column(String(50), nullable=False)
    income_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    is_supply: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_realization: Mapped[bool] = mapped_column(Boolean, nullable=False)
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False)
    discount_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False)
    spp: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=True)
    for_pay: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    finished_price: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=True)
    price_with_disc: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False)
    payment_sale_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    sale_id: Mapped[str] = mapped_column(String(255), nullable=True)
    sticker: Mapped[str] = mapped_column(String(255), nullable=False)
    g_number: Mapped[str] = mapped_column(String(255), nullable=False)
    srid: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    warehouse_type: Mapped[str] = mapped_column(String(255), nullable=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    __table_args__ = (UniqueConstraint(
        'date', 'user_id', 'srid', 'nm_id', 'tech_size',
        name='unique_sale'),)


class StocksWB(Base):
    __tablename__ = 'wb_stocks'

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    import_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True)
    last_сhange_date: Mapped[datetime] = mapped_column(DateTime, index=True)
    supplier_article: Mapped[str] = mapped_column(
        String(75), nullable=False, index=True)
    tech_size: Mapped[str] = mapped_column(String(30), nullable=True)
    barcode: Mapped[str] = mapped_column(String(30))
    nm_id: Mapped[int] = mapped_column(BigInteger, index=True)
    category: Mapped[str] = mapped_column(String(50))
    subject: Mapped[str] = mapped_column(String(50))
    brand: Mapped[str] = mapped_column(String(50))
    quantity: Mapped[int] = mapped_column(Integer)
    quantity_full: Mapped[int] = mapped_column(Integer)
    is_supply: Mapped[bool] = mapped_column(Boolean, nullable=True)
    is_realization: Mapped[bool] = mapped_column(Boolean, nullable=True)
    in_way_to_client: Mapped[int] = mapped_column(Integer)
    in_way_from_client: Mapped[int] = mapped_column(Integer)
    warehouse_name: Mapped[str] = mapped_column(String(50))
    sc_code: Mapped[str] = mapped_column(String(50), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(5, 2))

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    __table_args__ = (UniqueConstraint(
        'import_date', 'user_id', 'warehouse_name', 'nm_id',
        name='unique_stocks'),)


class TaskStatus(Base):
    __tablename__ = 'task_status'

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    task_name: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        # running, completed, failed
        String(20), nullable=False, default="running")
    task_id: Mapped[str] = mapped_column(
        String(255), nullable=True, index=True)  # ID задачи от брокера
    completed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True)
    error_message: Mapped[str] = mapped_column(
        String(500), nullable=True)

    user: Mapped["User"] = relationship(back_populates="task_statuses")


if __name__ == '__main__':
    print(f'{__name__} Запущен самостоятельно')
else:
    print(f'{__name__} Запущен как модуль')
