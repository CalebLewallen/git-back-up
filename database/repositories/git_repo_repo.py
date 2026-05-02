from litestar.plugins.sqlalchemy import repository

from ..tables import GitRepo

class GitRepoRepository(repository.SQLAlchemyAsyncRepository[GitRepo]):
    model_type = GitRepo