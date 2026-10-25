"""SQLAlchemy models for the Wiki application."""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, ForeignKey, Text, DateTime, Index, Uuid, Integer, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Role(Base):
    """Represents a user role/group (e.g., admin, member, media-team)."""

    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # admin, member, media-team
    name: Mapped[str] = mapped_column(String, unique=True)  # Display name
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)  # True for built-in roles
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    user_roles: Mapped[List["UserRole"]] = relationship(back_populates="role", cascade="all, delete-orphan")
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])

class UserRole(Base):
    """Junction table for many-to-many User-Role relationship."""
    
    __tablename__ = "user_roles"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    role_id: Mapped[str] = mapped_column(String, ForeignKey("roles.id"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (UniqueConstraint('user_id', 'role_id', name='_user_role_uc'),)
    
    user: Mapped["User"] = relationship(back_populates="user_roles")
    role: Mapped["Role"] = relationship(back_populates="user_roles")

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String)
    password_hash: Mapped[Optional[str]] = mapped_column(String)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    user_roles: Mapped[List["UserRole"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    pages: Mapped[List["Page"]] = relationship(back_populates="author")

class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String)

class Folder(Base):
    """Folder model for organizing pages."""
    __tablename__ = "folders"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("folders.id"), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    order: Mapped[int] = mapped_column(Integer, default=0)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    parent: Mapped[Optional["Folder"]] = relationship("Folder", remote_side=[id], backref="children")
    pages: Mapped[List["Page"]] = relationship(back_populates="folder")

class Page(Base):
    __tablename__ = "pages"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    folder_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("folders.id"), nullable=True)
    title: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    banner_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("pages.id"), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    author_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    folder: Mapped[Optional["Folder"]] = relationship(back_populates="pages")
    parent: Mapped[Optional["Page"]] = relationship("Page", remote_side=[id], backref="children")
    author: Mapped["User"] = relationship(back_populates="pages")

class Permission(Base):
    __tablename__ = "permissions"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    subject_type: Mapped[str] = mapped_column(String)  # USER or ROLE
    subject_id: Mapped[str] = mapped_column(String)    # UUID string or role id
    object_type: Mapped[str] = mapped_column(String)   # FOLDER or PAGE
    object_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    level: Mapped[str] = mapped_column(String)         # MANAGE, EDIT, VIEW

