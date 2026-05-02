import procrastinate
import tempfile
import os
import logging
import traceback
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional, List, Tuple
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from database.repositories.git_repo_repo import GitRepoRepository, SyncJobRepository, CredentialsRepository, WebhookRepository, GitRepoBranchRepository
from database.tables.git_repo_tables import JobStatus, Webhook, AuthType, MirrorMode, ServiceType
from services.git_cli import git_service
from services.notifications import notification_service
from core.config import settings
from core.security import decrypt_secret, mask_secrets

# Initialize procrastinate app
app = procrastinate.App(connector=procrastinate.PsycopgConnector(conninfo=settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")))

logger = logging.getLogger(__name__)

async def get_repo_auth(repo_id: UUID, service_type: str, cred_repo: CredentialsRepository) -> Tuple[Optional[str], Optional[str]]:
    creds = await cred_repo.list(git_repo_id=repo_id, service_type=service_type)
    if not creds:
        return None, None
    
    cred = creds[0]
    secret = decrypt_secret(cred.encrypted_secret)
    
    if cred.auth_type == AuthType.HTTP_TOKEN:
        return secret, None
    elif cred.auth_type == AuthType.SSH_KEY:
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write(secret)
            ssh_key_path = f.name
        os.chmod(ssh_key_path, 0o600)
        return None, ssh_key_path
    return None, None

def validate_git_url(url: str):
    # Prevent argument injection by ensuring URL doesn't start with -
    if url.strip().startswith("-"):
        raise ValueError("Invalid git URL: starts with '-'")

@app.task
async def send_notifications_task(job_id_str: str):
    job_id = UUID(job_id_str)
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    async with async_session() as session:
        job_repo = SyncJobRepository(session=session)
        repo_repo = GitRepoRepository(session=session)
        webhook_repo = WebhookRepository(session=session)
        
        job = await job_repo.get(job_id)
        repo = await repo_repo.get(job.git_repo_id)
        webhooks = await webhook_repo.list()
        
        payload = {
            "job_id": str(job_id),
            "repo_id": str(repo.id),
            "repo_name": repo.repo_name,
            "status": job.status,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }
        
        for webhook in webhooks:
            await notification_service.send_webhook(webhook, payload)
            
    await engine.dispose()

@app.task
async def sync_repo_task(repo_id_str: str, job_id_str: str):
    repo_id = UUID(repo_id_str)
    job_id = UUID(job_id_str)
    
    logger.info(f"Starting sync job {job_id} for repo {repo_id}")
    
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
        
        logger.info(f"Syncing repo: {repo.repo_name}")
        
        job.status = JobStatus.IN_PROGRESS
        job.started_at = datetime.now()
        await session.commit()
        
        try:
            # 1. Auth Setup
            logger.info("Setting up authentication...")
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
                logger.info("Fetching selective branches...")
                branch_objs = await branch_repo.list(git_repo_id=repo_id)
                branches = [b.branch_name for b in branch_objs]
                # Validate branches
                for b in branches:
                    if b.startswith("-"):
                        raise ValueError(f"Invalid branch name: {b}")

            # 3. Mirror
            logger.info(f"Running git mirror command (source: {repo.source_remote_repo}, target: {repo.target_remote_repo})...")
            result = git_service.mirror_repo(
                source_url=source_url,
                target_url=target_url,
                repo_id=str(repo_id),
                branches=branches,
                force_push=(repo.push_mode == "FORCE"),
                source_ssh_key=source_ssh,
                target_ssh_key=target_ssh
            )
            
            logger.info(f"Git mirror finished with return code {result.returncode}")
            
            job.stdout_log = mask_secrets(result.stdout or "", secrets_to_mask)
            
            stderr = result.stderr or ""
            if result.returncode != 0 and not stderr:
                stderr = f"Sync failed with return code {result.returncode}. No error output captured."
            
            job.stderr_log = mask_secrets(stderr, secrets_to_mask)
            job.status = JobStatus.SUCCESS if result.returncode == 0 else JobStatus.FAILED
            
            if result.returncode != 0:
                logger.error(f"Sync failed: {stderr}")
            
        except Exception as e:
            logger.error(f"Error during sync job: {e}")
            logger.error(traceback.format_exc())
            job.status = JobStatus.FAILED
            job.stderr_log = mask_secrets(f"Internal Error:\n{str(e)}\n\n{traceback.format_exc()}", secrets_to_mask)
        
        job.completed_at = datetime.now()
        try:
            await session.commit()
            logger.info(f"Job {job_id} completed and status saved.")
        except Exception as commit_exc:
            logger.error(f"Failed to commit job status to database: {commit_exc}")
        
        # Cleanup SSH keys
        for key in ssh_keys:
            if os.path.exists(key):
                try:
                    os.remove(key)
                except OSError:
                    pass
        
        await send_notifications_task.defer_async(job_id_str=str(job_id))
    
    await engine.dispose()
