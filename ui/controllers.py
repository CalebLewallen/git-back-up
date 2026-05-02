from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from litestar import Controller, Request, Response
from litestar.handlers import get, post
from litestar.response import Template
from litestar.params import Body
from litestar.enums import RequestEncodingType
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from database.tables import GitRepo, SyncJob, JobStatus, User, Session, GitRepoBranch, Credentials
from database.repositories.git_repo_repo import GitRepoRepository, SyncJobRepository, WebhookRepository
from database.repositories.user_repo import UserRepository, SessionRepository
from core.security import verify_password, hash_password

class UIController(Controller):
    path = "/"

    @get("/settings")
    async def settings_page(self) -> Template:
        return Template(template_name="pages/settings.html", context={"active_page": "settings"})

    @post("/settings/password")
    async def change_password(
        self,
        request: Request,
        db_session: AsyncSession,
        data: dict = Body(media_type=RequestEncodingType.URL_ENCODED)
    ) -> Response:
        user_repo = UserRepository(session=db_session)
        user = request.user
        
        old_password = data.get("old_password")
        new_password = data.get("new_password")
        
        if not verify_password(old_password, user.salt_uuid, user.password_hash):
            return Template(
                template_name="pages/settings.html",
                context={
                    "error": "Current password is incorrect",
                    "active_page": "settings"
                }
            )
            
        new_salt = uuid4()
        user.password_hash = hash_password(new_password, new_salt)
        user.salt_uuid = new_salt
        
        await user_repo.update(user)
        await db_session.commit()
        
        return Template(
            template_name="pages/settings.html",
            context={
                "message": "Password updated successfully",
                "active_page": "settings"
            }
        )

    @get("/repositories")
    async def repo_list_page(self, db_session: AsyncSession) -> Template:
        repo_repo = GitRepoRepository(session=db_session)
        repos = await repo_repo.list()
        
        # Simple stats calculation
        stats = {"healthy": 0, "failed": 0}
        enriched_repos = []
        
        for r in repos:
            # Get latest job status for each repo
            stmt = select(SyncJob).where(SyncJob.git_repo_id == r.id).order_by(SyncJob.completed_at.desc()).limit(1)
            result = await db_session.execute(stmt)
            last_job = result.scalar_one_or_none()
            
            status = last_job.status if last_job else "PENDING"
            if status == JobStatus.SUCCESS: stats["healthy"] += 1
            elif status == JobStatus.FAILED: stats["failed"] += 1
            
            enriched_repos.append({
                "id": str(r.id),
                "repo_name": r.repo_name,
                "source_remote_repo": r.source_remote_repo,
                "target_remote_repo": r.target_remote_repo,
                "status": status
            })

        return Template(
            template_name="pages/repos.html",
            context={
                "repos": enriched_repos,
                "stats": stats,
                "active_page": "repos"
            }
        )

    @get("/repositories/{repo_id:uuid}")
    async def repo_detail_page(self, db_session: AsyncSession, repo_id: UUID) -> Template:
        repo_repo = GitRepoRepository(session=db_session)
        repo = await repo_repo.get(repo_id)
        
        # Get sync history
        stmt = select(SyncJob).where(SyncJob.git_repo_id == repo_id).order_by(SyncJob.started_at.desc()).limit(20)
        result = await db_session.execute(stmt)
        jobs = result.scalars().all()
        
        latest_job = jobs[0] if jobs else None
        
        return Template(
            template_name="pages/repo_detail.html",
            context={
                "repo": repo,
                "jobs": jobs,
                "latest_job": latest_job,
                "active_page": "repos"
            }
        )

    @get("/repositories/new")
    async def repo_create_page(self) -> Template:
        return Template(
            template_name="pages/repo_edit.html",
            context={"repo": None, "active_page": "repos"}
        )

    @get("/repositories/{repo_id:uuid}/edit")
    async def repo_edit_page(self, db_session: AsyncSession, repo_id: UUID) -> Template:
        stmt = (
            select(GitRepo)
            .options(
                selectinload(GitRepo.credentials),
                selectinload(GitRepo.branches)
            )
            .where(GitRepo.id == repo_id)
        )
        result = await db_session.execute(stmt)
        repo = result.scalars().unique().one()
        return Template(
            template_name="pages/repo_edit.html",
            context={"repo": repo, "active_page": "repos"}
        )

    @get("/jobs")
    async def job_list_page(self, db_session: AsyncSession) -> Template:
        stmt = select(SyncJob, GitRepo.repo_name).join(GitRepo).order_by(SyncJob.started_at.desc()).limit(50)
        result = await db_session.execute(stmt)
        jobs = []
        for job, repo_name in result:
            jobs.append({
                "id": str(job.id),
                "status": job.status,
                "repo_name": repo_name,
                "started_at": job.started_at
            })
        return Template(template_name="pages/dashboard.html", context={"recent_jobs": jobs, "stats": {"total_repos": 0, "success_24h": 0, "failed": 0}, "active_page": "jobs"})

    @get("/jobs/{job_id:uuid}")
    async def job_detail_page(self, db_session: AsyncSession, job_id: UUID) -> Template:
        stmt = select(SyncJob, GitRepo).join(GitRepo).where(SyncJob.id == job_id)
        result = await db_session.execute(stmt)
        row = result.one_or_none()
        if not row:
            return Template(template_name="pages/dashboard.html", context={}) # Handle 404
        
        job, repo = row
        return Template(
            template_name="pages/job_detail.html",
            context={
                "job": job,
                "repo": repo,
                "active_page": "jobs"
            }
        )

    @get("/webhooks")
    async def webhook_page(self, db_session: AsyncSession) -> Template:
        repo = WebhookRepository(session=db_session)
        webhooks = await repo.list()
        return Template(
            template_name="pages/webhooks.html",
            context={
                "webhooks": webhooks,
                "active_page": "webhooks"
            }
        )

    @get("/")
    async def dashboard_page(self, db_session: AsyncSession) -> Template:
        # Calculate dashboard stats
        repo_count_stmt = select(func.count()).select_from(GitRepo)
        repo_count = await db_session.execute(repo_count_stmt)
        total_repos = repo_count.scalar() or 0
        
        yesterday = datetime.now() - timedelta(days=1)
        success_stmt = select(func.count()).select_from(SyncJob).where(SyncJob.status == JobStatus.SUCCESS, SyncJob.completed_at >= yesterday)
        success_count = await db_session.execute(success_stmt)
        
        failed_stmt = select(func.count()).select_from(SyncJob).where(SyncJob.status == JobStatus.FAILED)
        failed_count = await db_session.execute(failed_stmt)

        # Recent jobs with repo names
        recent_jobs_stmt = select(SyncJob, GitRepo.repo_name).join(GitRepo).order_by(SyncJob.started_at.desc()).limit(10)
        result = await db_session.execute(recent_jobs_stmt)
        recent_jobs = []
        for job, repo_name in result:
            recent_jobs.append({
                "status": job.status,
                "repo_name": repo_name,
                "timestamp": job.started_at.strftime("%Y-%m-%d %H:%M") if job.started_at else "Pending"
            })

        stats = {
            "total_repos": total_repos,
            "success_24h": success_count.scalar() or 0,
            "failed": failed_count.scalar() or 0
        }

        return Template(
            template_name="pages/dashboard.html", 
            context={
                "stats": stats, 
                "recent_jobs": recent_jobs,
                "active_page": "dashboard"
            }
        )
