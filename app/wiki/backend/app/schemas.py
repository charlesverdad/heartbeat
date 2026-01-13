"""Pydantic schemas for the Wiki API."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import EmailStr


class RoleBase(BaseModel):
    """Base schema for roles."""
    id: str
    name: str

class Role(RoleBase):
    model_config = ConfigDict(from_attributes=True)

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role_id: str

class User(UserBase):
    id: UUID
    last_login: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class Setting(BaseModel):
    key: str
    value: str
    model_config = ConfigDict(from_attributes=True)

class SettingUpdate(BaseModel):
    value: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role_id: Optional[str] = None

class FolderBase(BaseModel):
    name: str
    parent_id: Optional[UUID] = None
    is_public: bool = False

class Folder(FolderBase):
    id: UUID
    order: int
    model_config = ConfigDict(from_attributes=True)

class PageBase(BaseModel):
    title: str
    content: str
    folder_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    order: int = 0
    is_public: bool = False
    banner_url: Optional[str] = None

class PageCreate(PageBase):
    pass

class PageUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    folder_id: Optional[UUID] = None
    parent_id: Optional[UUID] = None
    order: Optional[int] = None
    
class Page(PageBase):
    id: UUID
    author_id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PermissionBase(BaseModel):
    subject_type: str
    subject_id: str
    object_type: str
    object_id: UUID
    level: str

class Permission(PermissionBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)
