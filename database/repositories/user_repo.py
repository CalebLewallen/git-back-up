from litestar.plugins.sqlalchemy import repository
from database.tables import User, Session

class UserRepository(repository.SQLAlchemyAsyncRepository[User]):
    model_type = User

class SessionRepository(repository.SQLAlchemyAsyncRepository[Session]):
    model_type = Session
