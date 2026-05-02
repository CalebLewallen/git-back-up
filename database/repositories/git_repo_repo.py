from litestar.plugins.sqlalchemy import repository
from database.tables import GitRepo, GitRepoBranch, Credentials, SyncJob, Webhook

class GitRepoRepository(repository.SQLAlchemyAsyncRepository[GitRepo]):
    model_type = GitRepo

class GitRepoBranchRepository(repository.SQLAlchemyAsyncRepository[GitRepoBranch]):
    model_type = GitRepoBranch

class CredentialsRepository(repository.SQLAlchemyAsyncRepository[Credentials]):
    model_type = Credentials

class SyncJobRepository(repository.SQLAlchemyAsyncRepository[SyncJob]):
    model_type = SyncJob

class WebhookRepository(repository.SQLAlchemyAsyncRepository[Webhook]):
    model_type = Webhook
