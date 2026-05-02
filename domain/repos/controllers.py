from uuid import UUID
from typing import List
from litestar import Controller
from litestar.handlers import get, post
from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import RepoCreate, RepoRead
from .services import RepoService
from database.repositories.git_repo_repo import GitRepoRepository

class RepoController(Controller):
    path = "/api/repos"

    @get()
    async def list_repos(self, db_session: AsyncSession) -> List[RepoRead]:
        repo_repo = GitRepoRepository(session=db_session)
        repos = await repo_repo.list()
        return [RepoRead.model_validate(repo) for repo in repos]

    @post()
    async def create_repo(self, db_session: AsyncSession, data: RepoCreate) -> RepoRead:
        service = RepoService(session=db_session)
        repo = await service.create_repo(data.model_dump())
        return RepoRead.model_validate(repo)

    @post("/{repo_id:uuid}/sync")
    async def trigger_sync(self, db_session: AsyncSession, repo_id: UUID) -> dict:
        service = RepoService(session=db_session)
        job = await service.trigger_sync(repo_id)
        return {"job_id": str(job.id), "status": job.status}
