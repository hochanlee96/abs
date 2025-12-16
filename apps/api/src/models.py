from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, String, DateTime, func

class Base(DeclarativeBase):
    pass

class Account(Base):
    __tablename__ = "accounts"

    account_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    google_sub: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[str] = mapped_column(DateTime(3), server_default=func.current_timestamp())
    updated_at: Mapped[str] = mapped_column(DateTime(3), server_default=func.current_timestamp(), onupdate=func.current_timestamp())