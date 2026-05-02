from pydantic import BaseModel, HttpUrl
from uuid import UUID
from datetime import datetime
from typing import List, Optional
from database.tables.git_repo_tables import MirrorMode, PushMode, ServiceType, AuthType

class CredentialCreate(BaseModel):
    service_type: ServiceType
    auth_type: AuthType
    secret: Optional[str] = None
    username: Optional[str] = None

class CredentialRead(BaseModel):
    id: UUID
    service_type: ServiceType
    auth_type: AuthType
    username: Optional[str] = None

    class Config:
        from_attributes = True

class RepoCreate(BaseModel):
    repo_name: str
    source_remote_repo: str
    target_remote_repo: str
    source_ssh_port: int = 22
    target_ssh_port: int = 22
    replication_interval_hours: int = 24
    mirror_mode: MirrorMode = MirrorMode.ALL_BRANCHES
    push_mode: PushMode = PushMode.SAFE
    credentials: List[CredentialCreate] = []
    branches: List[str] = []

class RepoRead(BaseModel):
    id: UUID
    repo_name: str
    source_remote_repo: str
    target_remote_repo: str
    source_ssh_port: int
    target_ssh_port: int
    replication_interval_hours: int
    mirror_mode: MirrorMode
    push_mode: PushMode
    
    class Config:
        from_attributes = True
