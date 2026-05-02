import secrets
from datetime import datetime, timedelta
from uuid import uuid4
from litestar import Controller, Response, Request
from litestar.handlers import get, post
from litestar.response import Template, Redirect
from litestar.enums import RequestEncodingType
from litestar.params import Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.tables import User, Session
from database.repositories.user_repo import UserRepository, SessionRepository
from core.security import hash_password, verify_password

class AuthController(Controller):
    path = ""

    @get("/login")
    async def login_page(self, db_session: AsyncSession) -> Response:
        user_repo = UserRepository(session=db_session)
        count = await user_repo.count()
        if count == 0:
            return Redirect(path="/register")
        return Template(template_name="pages/login.html")

    @post("/login", cache_control=None)
    async def login(
        self,
        db_session: AsyncSession,
        data: dict = Body(media_type=RequestEncodingType.URL_ENCODED)
    ) -> Response:
        user_repo = UserRepository(session=db_session)
        session_repo = SessionRepository(session=db_session)
        
        count = await user_repo.count()
        if count == 0:
            return Redirect(path="/register")

        username = data.get("username")
        password = data.get("password")
        
        user = await user_repo.get_one_or_none(username=username)
        if not user or not verify_password(password, user.salt_uuid, user.password_hash):
            return Template(
                template_name="pages/login.html",
                context={"error": "Invalid username or password"}
            )

        token = secrets.token_urlsafe(32)
        session = await session_repo.add(Session(
            token=token,
            user_id=user.id,
            expires_at=datetime.now() + timedelta(hours=24)
        ))
        await db_session.commit()

        response = Redirect(path="/")
        response.set_cookie(key="session_token", value=token, httponly=True)
        return response

    @get("/register")
    async def register_page(self, db_session: AsyncSession) -> Response:
        user_repo = UserRepository(session=db_session)
        count = await user_repo.count()
        if count > 0:
            return Redirect(path="/login")
        return Template(template_name="pages/register.html")

    @post("/register", cache_control=None)
    async def register(
        self,
        db_session: AsyncSession,
        data: dict = Body(media_type=RequestEncodingType.URL_ENCODED)
    ) -> Response:
        user_repo = UserRepository(session=db_session)
        session_repo = SessionRepository(session=db_session)
        
        count = await user_repo.count()
        if count > 0:
            return Redirect(path="/login")

        username = data.get("username")
        password = data.get("password")
        
        salt_uuid = uuid4()
        password_hash = hash_password(password, salt_uuid)
        
        user = await user_repo.add(User(
            username=username,
            password_hash=password_hash,
            salt_uuid=salt_uuid
        ))
        
        token = secrets.token_urlsafe(32)
        await session_repo.add(Session(
            token=token,
            user_id=user.id,
            expires_at=datetime.now() + timedelta(hours=24)
        ))
        await db_session.commit()

        response = Redirect(path="/")
        response.set_cookie(key="session_token", value=token, httponly=True)
        return response

    @get("/logout")
    async def logout(self, request: Request, db_session: AsyncSession) -> Response:
        session_repo = SessionRepository(session=db_session)
        token = request.cookies.get("session_token")
        if token:
            session = await session_repo.get_one_or_none(token=token)
            if session:
                await session_repo.delete(session.id)
                await db_session.commit()
        
        response = Redirect(path="/login")
        response.delete_cookie(key="session_token")
        return response
