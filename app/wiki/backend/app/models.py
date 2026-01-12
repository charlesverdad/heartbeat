"""SQLAlchemy models for the Wiki application."""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import String, ForeignKey, Text, DateTime, Index, Uuid, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Role(Base):
    """Represents a user role (e.g., admin, member, public)."""

    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # admin, member, public
    name: Mapped[str] = mapped_column(String)
    
    users: Mapped[List["User"]] = relationship(back_populates="role")

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String)
    password_hash: Mapped[Optional[str]] = mapped_column(String)
    role_id: Mapped[str] = mapped_column(String, ForeignKey("roles.id"))
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    role: Mapped["Role"] = relationship(back_populates="users")
    pages: Mapped[List["Page"]] = relationship(back_populates="author")

class Folder(Base):
    """Folder model for organizing pages."""
    __tablename__ = "folders"
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(Uuid, ForeignKey("folders.id"), nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0)
    
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
    author_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"))
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
