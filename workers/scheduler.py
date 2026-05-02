from datetime import datetime, timedelta, timezone
from typing import Any
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from database.tables.git_repo_tables import SyncJob, JobStatus, JobType
from database.repositories.git_repo_repo import GitRepoRepository, SyncJobRepository
from workers.tasks import app, sync_repo_task
from core.config import settings

@app.periodic(cron="0 * * * *") # Run every hour
@app.task
async def schedule_syncs(worker: Any):
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as session:
        repo_repo = GitRepoRepository(session=session)
        job_repo = SyncJobRepository(session=session)
        
        # 1. Get all repos
        repos = await repo_repo.list()
        
        for repo in repos:
            # 2. Find last successful job for this repo
            stmt = select(SyncJob).where(
                SyncJob.git_repo_id == repo.id,
                SyncJob.status == JobStatus.SUCCESS
            ).order_by(SyncJob.completed_at.desc()).limit(1)
            
            result = await session.execute(stmt)
            last_job = result.scalar_one_or_none()
            
            should_sync = False
            if not last_job or last_job.completed_at is None:
                should_sync = True
            else:
                elapsed = datetime.now(timezone.utc) - last_job.completed_at
                if elapsed >= timedelta(hours=repo.replication_interval_hours):
                    should_sync = True
            
            if should_sync:
                # 3. Create a PENDING job
                job = await job_repo.add(SyncJob(
                    git_repo_id=repo.id,
                    job_type=JobType.SCHEDULED,
                    status=JobStatus.PENDING
                ))
                await session.commit()
                
                # 4. Defer task
                await sync_repo_task.defer_async(repo_id_str=str(repo.id), job_id_str=str(job.id))
                
    await engine.dispose()
