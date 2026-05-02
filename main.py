from litestar import Litestar
from litestar.static_files import StaticFilesConfig
from database.engine import sqlalchemy_plugin
from workers.tasks import app as procrastinate_app
import workers.scheduler
from domain.repos.controllers import RepoController
from domain.jobs.controllers import JobController
from domain.webhooks.controllers import WebhookController
from ui.controllers import UIController

from litestar.template.config import TemplateConfig
from litestar.contrib.jinja import JinjaTemplateEngine

async def on_startup() -> None:
    await procrastinate_app.open_async()

async def on_shutdown() -> None:
    await procrastinate_app.close_async()

app = Litestar(
    route_handlers=[UIController, RepoController, JobController, WebhookController],
    plugins=[sqlalchemy_plugin],
    on_startup=[on_startup],
    on_shutdown=[on_shutdown],
    template_config=TemplateConfig(
        directory="templates",
        engine=JinjaTemplateEngine,
    ),
    static_files_config=[
        StaticFilesConfig(directories=["static"], path="/static", name="static"),
    ],
)
