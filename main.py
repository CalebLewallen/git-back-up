import asyncio
import logging
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

logger = logging.getLogger(__name__)

# Keep a reference to the worker task to prevent garbage collection
# https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
_worker_task: asyncio.Task | None = None

async def on_startup() -> None:
    global _worker_task
    async with engine.begin() as conn:
        await conn.run_sync(UUIDAuditBase.metadata.create_all)
    await procrastinate_app.open_async()
    # Apply procrastinate schema (ignore if already exists)
    try:
        await procrastinate_app.schema_manager.apply_schema_async()
    except Exception:
        # Schema likely already exists
        pass
    # Start the worker in the background and keep a reference
    logger.info("Starting embedded procrastinate worker...")
    _worker_task = asyncio.create_task(procrastinate_app.run_worker_async())
    _worker_task.add_done_callback(lambda t: logger.info(f"Worker task finished with status: {t.exception() or 'Success'}"))

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
