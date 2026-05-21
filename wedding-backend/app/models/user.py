from sqlalchemy import String, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
import enum


class TeamEnum(str, enum.Enum):
    sales = "sales"
    planning = "planning"
    design = "design"
    management = "management"


class UserStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    role_id: Mapped[int] = mapped_column(nullable=False)
    team: Mapped[TeamEnum] = mapped_column(SAEnum(TeamEnum), nullable=False)
    status: Mapped[UserStatus] = mapped_column(SAEnum(UserStatus), default=UserStatus.active)


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    permissions: Mapped[str] = mapped_column(nullable=False)  # JSON string
