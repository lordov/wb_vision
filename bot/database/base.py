from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime


class Base(DeclarativeBase):
    created: Mapped[datetime] = mapped_column(DateTime(), default=datetime.now)
    updated: Mapped[datetime] = mapped_column(
        DateTime(), default=datetime.now, onupdate=datetime.now)
