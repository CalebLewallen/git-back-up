import asyncio
from litestar import Litestar, Request, Response
from litestar.static_files import StaticFilesConfig
from litestar.middleware import DefineMiddleware
from litestar.response import Redirect
from litestar.exceptions import NotAuthorizedException
from database.engine import sqlalchemy_plugin, engine
from workers.tasks import app as procrastinate_app
import workers.scheduler
from domain.repos.controllers import RepoController
from domain.jobs.controllers import JobController
from domain.webhooks.controllers import WebhookController
from ui.controllers import UIController
from ui.auth_controllers import AuthController
from middleware.auth import SessionAuthMiddleware
from database.tables import UUIDAuditBase

from litestar.template.config import TemplateConfig
from litestar.contrib.jinja import JinjaTemplateEngine

async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(UUIDAuditBase.metadata.create_all)
    await procrastinate_app.open_async()
    # Start the worker in the background
    asyncio.create_task(procrastinate_app.run_worker_async())

async def on_shutdown() -> None:
    await procrastinate_app.close_async()

def auth_exception_handler(request: Request, exc: NotAuthorizedException) -> Response:
    return Redirect(path="/login")

app = Litestar(
    route_handlers=[AuthController, UIController, RepoController, JobController, WebhookController],
    plugins=[sqlalchemy_plugin],
    middleware=[
        DefineMiddleware(
            SessionAuthMiddleware, 
            exclude=["/login", "/register", "/static", "/schema"]
        )
    ],
    exception_handlers={
        NotAuthorizedException: auth_exception_handler
    },
    on_startup=[on_startup],
    on_shutdown=[on_shutdown],
    template_config=TemplateConfig(
        directory="templates",
        engine=JinjaTemplateEngine,
    ),
    static_files_config=[
        StaticFilesConfig(directories=["static"], path="/static", name="static"),
    ],
    debug=True
)
