from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional
from database.tables.git_repo_tables import JobStatus, JobType

class SyncJobRead(BaseModel):
    id: UUID
    git_repo_id: UUID
    status: JobStatus
    job_type: JobType
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    stdout_log: Optional[str] = None
    stderr_log: Optional[str] = None

    class Config:
        from_attributes = True
