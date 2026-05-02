from datetime import datetime, timedelta, timezone
from litestar import Controller, Get
from litestar.response import Template
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database.tables.git_repo_tables import GitRepo, SyncJob, JobStatus
from database.repositories.git_repo_repo import GitRepoRepository

class UIController(Controller):
    path = "/"

    @Get("/repositories")
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

    @Get("/repositories/{repo_id:uuid}")
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

    @Get("/repositories/new")
    async def repo_create_page(self) -> Template:
        return Template(
            template_name="pages/repo_edit.html",
            context={"repo": None, "active_page": "repos"}
        )

    @Get("/repositories/{repo_id:uuid}/edit")
    async def repo_edit_page(self, db_session: AsyncSession, repo_id: UUID) -> Template:
        repo_repo = GitRepoRepository(session=db_session)
        repo = await repo_repo.get(repo_id)
        return Template(
            template_name="pages/repo_edit.html",
            context={"repo": repo, "active_page": "repos"}
        )

    @Get("/jobs")
    async def job_list_page(self, db_session: AsyncSession) -> Template:
        # Re-use repo_list logic or dedicated job list if needed
        # For simplicity, we'll create a quick job list
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

    @Get("/jobs/{job_id:uuid}")
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

    @Get("/webhooks")
    async def webhook_page(self, db_session: AsyncSession) -> Template:
        from database.repositories.git_repo_repo import WebhookRepository
        repo = WebhookRepository(session=db_session)
        webhooks = await repo.list()
        return Template(
            template_name="pages/webhooks.html",
            context={
                "webhooks": webhooks,
                "active_page": "webhooks"
            }
        )

    @Get("/")
    async def dashboard_page(self, db_session: AsyncSession) -> Template:
        # Calculate dashboard stats
        repo_count_stmt = select(func.count()).select_from(GitRepo)
        repo_count = await db_session.execute(repo_count_stmt)
        total_repos = repo_count.scalar() or 0
        
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
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
