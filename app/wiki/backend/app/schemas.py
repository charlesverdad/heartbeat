from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr
from uuid import UUID
from datetime import datetime

class RoleBase(BaseModel):
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

class FolderBase(BaseModel):
    name: str
    parent_id: Optional[UUID] = None

class Folder(FolderBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)

class PageBase(BaseModel):
    title: str
    content: str
    folder_id: Optional[UUID] = None

class PageCreate(PageBase):
    pass

class PageUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    folder_id: Optional[UUID] = None

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
