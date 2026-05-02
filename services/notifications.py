import httpx
import logging
import hmac
import hashlib
import json
from typing import Any, Dict
from database.tables.git_repo_tables import Webhook, TriggerOn, JobStatus
from core.config import settings

logger = logging.getLogger(__name__)

class NotificationService:
    async def send_webhook(self, webhook: Webhook, payload: Dict[str, Any]) -> None:
        if not webhook.is_active:
            return

        # Check triggers
        status = payload.get("status")
        if webhook.trigger_on == TriggerOn.ALL_FAILURES and status != JobStatus.FAILED:
            return

        body = json.dumps(payload)
        signature = hmac.new(
            settings.WEBHOOK_SECRET.encode(),
            body.encode(),
            hashlib.sha256
        ).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-GitBackup-Signature": signature
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    webhook.url, 
                    content=body, 
                    headers=headers, 
                    timeout=10.0
                )
                response.raise_for_status()
            except Exception as e:
                logger.error(f"Failed to send webhook to {webhook.url}: {e}")

notification_service = NotificationService()
