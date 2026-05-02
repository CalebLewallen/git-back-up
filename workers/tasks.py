import procrastinate
import tempfile
import os
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from database.repositories.git_repo_repo import GitRepoRepository, SyncJobRepository, CredentialsRepository, WebhookRepository, GitRepoBranchRepository
from database.tables.git_repo_tables import JobStatus, Webhook, AuthType, MirrorMode
from services.git_cli import git_service
from services.notifications import notification_service
from core.config import settings
from core.security import decrypt_secret, mask_secrets

# ... (keep existing imports)

def validate_git_url(url: str):
    # Prevent argument injection by ensuring URL doesn't start with -
    if url.strip().startswith("-"):
        raise ValueError("Invalid git URL: starts with '-'")

@app.task
async def sync_repo_task(repo_id_str: str, job_id_str: str):
    repo_id = UUID(repo_id_str)
    job_id = UUID(job_id_str)
    
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    ssh_keys = []
    secrets_to_mask = []
    
    async with async_session() as session:
        repo_repo = GitRepoRepository(session=session)
        job_repo = SyncJobRepository(session=session)
        cred_repo = CredentialsRepository(session=session)
        branch_repo = GitRepoBranchRepository(session=session)
        
        repo = await repo_repo.get(repo_id)
        job = await job_repo.get(job_id)
        
        job.status = JobStatus.IN_PROGRESS
        job.started_at = datetime.now(timezone.utc)
        await session.commit()
        
        try:
            # 1. Auth Setup
            source_token, source_ssh = await get_repo_auth(repo_id, "SOURCE", cred_repo)
            target_token, target_ssh = await get_repo_auth(repo_id, "TARGET", cred_repo)
            
            if source_ssh: ssh_keys.append(source_ssh)
            if target_ssh: ssh_keys.append(target_ssh)
            if source_token: secrets_to_mask.append(source_token)
            if target_token: secrets_to_mask.append(target_token)
            
            source_url = repo.source_remote_repo
            validate_git_url(source_url)
            if source_token:
                if "://" in source_url:
                    proto, rest = source_url.split("://", 1)
                    source_url = f"{proto}://{source_token}@{rest}"

            target_url = repo.target_remote_repo
            validate_git_url(target_url)
            if target_token:
                if "://" in target_url:
                    proto, rest = target_url.split("://", 1)
                    target_url = f"{proto}://{target_token}@{rest}"

            # 2. Branches
            branches = None
            if repo.mirror_mode == MirrorMode.SELECT_BRANCHES:
                branch_objs = await branch_repo.list(git_repo_id=repo_id)
                branches = [b.branch_name for b in branch_objs]
                # Validate branches
                for b in branches:
                    if b.startswith("-"):
                        raise ValueError(f"Invalid branch name: {b}")

            # 3. Mirror
            result = git_service.mirror_repo(
                source_url=source_url,
                target_url=target_url,
                repo_id=str(repo_id),
                branches=branches,
                force_push=(repo.push_mode == "FORCE"),
                source_ssh_key=source_ssh,
                target_ssh_key=target_ssh
            )
            
            job.stdout_log = mask_secrets(result.stdout, secrets_to_mask)
            job.stderr_log = mask_secrets(result.stderr, secrets_to_mask)
            job.status = JobStatus.SUCCESS if result.returncode == 0 else JobStatus.FAILED
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.stderr_log = mask_secrets(str(e), secrets_to_mask)
        
        job.completed_at = datetime.now(timezone.utc)
        await session.commit()
        
        # Cleanup SSH keys
        for key in ssh_keys:
            if os.path.exists(key):
                os.remove(key)
        
        await send_notifications_task.defer_async(job_id_str=str(job_id))
    
    await engine.dispose()
