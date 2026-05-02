from datetime import datetime, timedelta
from litestar.middleware import AbstractAuthenticationMiddleware, AuthenticationResult
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from database.tables import Session, User
from database.engine import session_factory

class SessionAuthMiddleware(AbstractAuthenticationMiddleware):
    async def authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult:
        token = connection.cookies.get("session_token")
        if not token:
            raise NotAuthorizedException("No session token provided")

        async with session_factory() as db_session:
            stmt = (
                select(Session)
                .options(joinedload(Session.user))
                .where(Session.token == token)
            )
            result = await db_session.execute(stmt)
            session_obj = result.scalar_one_or_none()

            if not session_obj or session_obj.expires_at < datetime.now():
                if session_obj:
                    await db_session.delete(session_obj)
                    await db_session.commit()
                raise NotAuthorizedException("Invalid or expired session")

            # Rolling expiry: extend session by 24 hours
            session_obj.expires_at = datetime.now() + timedelta(hours=24)
            await db_session.commit()

            return AuthenticationResult(user=session_obj.user, auth=session_obj)
