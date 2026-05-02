from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from database.repositories.git_repo_repo import GitRepoRepository, CredentialsRepository, SyncJobRepository, GitRepoBranchRepository
from database.tables.git_repo_tables import GitRepo, Credentials, SyncJob, JobType, GitRepoBranch
from core.security import encrypt_secret
from workers.tasks import sync_repo_task

class RepoService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo_repo = GitRepoRepository(session=session)
        self.cred_repo = CredentialsRepository(session=session)
        self.job_repo = SyncJobRepository(session=session)
        self.branch_repo = GitRepoBranchRepository(session=session)

    async def create_repo(self, data: dict) -> GitRepo:
        creds_data = data.pop("credentials", [])
        branches_data = data.pop("branches", [])
        
        repo = await self.repo_repo.add(GitRepo(**data))
        
        for cred in creds_data:
            cred["encrypted_secret"] = encrypt_secret(cred.pop("secret"))
            cred["git_repo_id"] = repo.id
            await self.cred_repo.add(Credentials(**cred))
            
        for branch_name in branches_data:
            await self.branch_repo.add(GitRepoBranch(git_repo_id=repo.id, branch_name=branch_name))
            
        await self.session.commit()
        return repo

    async def update_repo(self, repo_id: UUID, data: dict) -> GitRepo:
        creds_data = data.pop("credentials", [])
        branches_data = data.pop("branches", [])
        
        repo = await self.repo_repo.get(repo_id)
        for key, value in data.items():
            setattr(repo, key, value)
        
        repo = await self.repo_repo.update(repo)
        
        # Refresh credentials (delete and recreate)
        existing_creds = await self.cred_repo.list(git_repo_id=repo_id)
        existing_creds_map = {c.service_type: c for c in existing_creds}
        
        for cred in existing_creds:
            await self.cred_repo.delete(cred.id)
            
        for cred_data in creds_data:
            service_type = cred_data["service_type"]
            secret = cred_data.pop("secret", None)
            
            if not secret or not secret.strip():
                # Try to use old secret
                old_cred = existing_creds_map.get(service_type)
                if old_cred:
                    cred_data["encrypted_secret"] = old_cred.encrypted_secret
                else:
                    # No old secret and no new secret provided, skip or handle error?
                    # For now, if it was already in the form, it might be expected to have one.
                    continue
            else:
                cred_data["encrypted_secret"] = encrypt_secret(secret)
                
            cred_data["git_repo_id"] = repo.id
            await self.cred_repo.add(Credentials(**cred_data))
            
        # Refresh branches
        existing_branches = await self.branch_repo.list(git_repo_id=repo_id)
        for branch in existing_branches:
            await self.branch_repo.delete(branch.id)
            
        for branch_name in branches_data:
            await self.branch_repo.add(GitRepoBranch(git_repo_id=repo.id, branch_name=branch_name))
            
        await self.session.commit()
        return repo

    async def trigger_sync(self, repo_id: UUID) -> SyncJob:
        job = await self.job_repo.add(SyncJob(git_repo_id=repo_id, job_type=JobType.MANUAL))
        await self.session.commit()
        
        # Defer task to procrastinate
        await sync_repo_task.defer_async(repo_id_str=str(repo_id), job_id_str=str(job.id))
        
        return job
