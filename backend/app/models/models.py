from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    plan = Column(
        Enum("free", "personal", "pro", "agency", name="plan_type"),
        default="free",
        nullable=False,
    )
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    email_logs = relationship("EmailLog", back_populates="user", cascade="all, delete-orphan")
    dm_logs = relationship("DmLog", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    status = Column(
        Enum("active", "paused", "completed", name="project_status"),
        default="active",
        nullable=False,
    )
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user = relationship("User", back_populates="projects")
    keywords = relationship("Keyword", back_populates="project", cascade="all, delete-orphan")
    prospects = relationship("Prospect", back_populates="project", cascade="all, delete-orphan")


class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    keyword = Column(String(200), nullable=False)
    source = Column(
        Enum("naver", "google", "instagram", "naver_shopping", "naver_map", name="keyword_source"),
        nullable=False,
    )
    created_at = Column(DateTime, default=utcnow, nullable=False)

    project = relationship("Project", back_populates="keywords")


class Prospect(Base):
    __tablename__ = "prospects"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    instagram = Column(String(100), nullable=True)
    website = Column(String(500), nullable=True)
    source = Column(String(50), nullable=True)
    category = Column(String(100), nullable=True)
    status = Column(
        Enum(
            "collected", "approved", "rejected", "email_sent", "dm_sent",
            name="prospect_status",
        ),
        default="collected",
        nullable=False,
    )
    collected_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    project = relationship("Project", back_populates="prospects")
    email_logs = relationship("EmailLog", back_populates="prospect", cascade="all, delete-orphan")
    dm_logs = relationship("DmLog", back_populates="prospect", cascade="all, delete-orphan")


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sent_at = Column(DateTime, default=utcnow, nullable=False)
    status = Column(
        Enum("success", "failed", name="send_status"),
        nullable=False,
    )
    error_message = Column(Text, nullable=True)

    prospect = relationship("Prospect", back_populates="email_logs")
    user = relationship("User", back_populates="email_logs")


class DmLog(Base):
    __tablename__ = "dm_logs"

    id = Column(Integer, primary_key=True, index=True)
    prospect_id = Column(Integer, ForeignKey("prospects.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sent_at = Column(DateTime, default=utcnow, nullable=False)
    status = Column(
        Enum("success", "failed", name="dm_send_status"),
        nullable=False,
    )
    error_message = Column(Text, nullable=True)

    prospect = relationship("Prospect", back_populates="dm_logs")
    user = relationship("User", back_populates="dm_logs")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    gmail_email = Column(String(255), nullable=True)
    gmail_app_password_encrypted = Column(String(500), nullable=True)
    email_template = Column(Text, nullable=True)
    dm_template = Column(Text, nullable=True)
    daily_email_limit = Column(Integer, default=80, nullable=False)
    daily_dm_limit = Column(Integer, default=15, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", name="uq_user_settings_user_id"),)

    user = relationship("User", back_populates="settings")
