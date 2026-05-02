from uuid import UUID
from typing import List, Optional
from litestar import Controller
from litestar.handlers import get
from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import SyncJobRead
from database.repositories.git_repo_repo import SyncJobRepository

class JobController(Controller):
    path = "/api/jobs"

    @get()
    async def list_jobs(self, db_session: AsyncSession, repo_id: Optional[UUID] = None) -> List[SyncJobRead]:
        repo = SyncJobRepository(session=db_session)
        if repo_id:
            jobs = await repo.list(git_repo_id=repo_id)
        else:
            jobs = await repo.list()
        return [SyncJobRead.model_validate(job) for job in jobs]

    @get("/{job_id:uuid}")
    async def get_job(self, db_session: AsyncSession, job_id: UUID) -> SyncJobRead:
        repo = SyncJobRepository(session=db_session)
        job = await repo.get(job_id)
        return SyncJobRead.model_validate(job)
