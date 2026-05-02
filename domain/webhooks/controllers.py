from uuid import UUID
from typing import List
from litestar import Controller
from litestar.handlers import get, post, delete
from sqlalchemy.ext.asyncio import AsyncSession
from .schemas import WebhookCreate, WebhookRead
from database.repositories.git_repo_repo import WebhookRepository
from database.tables.git_repo_tables import Webhook

class WebhookController(Controller):
    path = "/api/webhooks"

    @get()
    async def list_webhooks(self, db_session: AsyncSession) -> List[WebhookRead]:
        repo = WebhookRepository(session=db_session)
        webhooks = await repo.list()
        return [WebhookRead.model_validate(w) for w in webhooks]

    @post()
    async def create_webhook(self, db_session: AsyncSession, data: WebhookCreate) -> WebhookRead:
        repo = WebhookRepository(session=db_session)
        webhook = await repo.add(Webhook(**data.model_dump()))
        await db_session.commit()
        return WebhookRead.model_validate(webhook)

    @delete("/{webhook_id:uuid}")
    async def delete_webhook(self, db_session: AsyncSession, webhook_id: UUID) -> None:
        repo = WebhookRepository(session=db_session)
        await repo.delete(webhook_id)
        await db_session.commit()
