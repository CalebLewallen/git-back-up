from pydantic import BaseModel, AnyHttpUrl
from uuid import UUID
from typing import Optional
from database.tables.git_repo_tables import TriggerOn

class WebhookCreate(BaseModel):
    url: str
    is_active: bool = True
    trigger_on: TriggerOn = TriggerOn.ALL_FAILURES

class WebhookRead(BaseModel):
    id: UUID
    url: str
    is_active: bool
    trigger_on: TriggerOn

    class Config:
        from_attributes = True
