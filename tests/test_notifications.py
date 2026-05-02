import pytest
import hmac
import hashlib
import json
from unittest.mock import AsyncMock, patch
from database.tables.git_repo_tables import Webhook, TriggerOn, JobStatus
from services.notifications import NotificationService
from core.config import settings

@pytest.mark.asyncio
async def test_send_webhook_success(mocker):
    # Mock settings
    settings.WEBHOOK_SECRET = "test-secret"
    
    webhook = Webhook(url="https://example.com/webhook", is_active=True, trigger_on=TriggerOn.ALL_EVENTS)
    payload = {"status": JobStatus.SUCCESS, "repo_id": "123"}
    
    mock_response = mocker.Mock()
    mock_response.raise_for_status = mocker.Mock()
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        
        service = NotificationService()
        await service.send_webhook(webhook, payload)
        
        # Verify signature
        body = json.dumps(payload)
        expected_sig = hmac.new(
            b"test-secret",
            body.encode(),
            hashlib.sha256
        ).hexdigest()
        
        args, kwargs = mock_post.call_args
        assert kwargs["headers"]["X-GitBackup-Signature"] == expected_sig
        assert kwargs["content"] == body

@pytest.mark.asyncio
async def test_send_webhook_inactive():
    webhook = Webhook(url="https://example.com/webhook", is_active=False)
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        service = NotificationService()
        await service.send_webhook(webhook, {})
        mock_post.assert_not_called()

@pytest.mark.asyncio
async def test_send_webhook_trigger_mismatch():
    webhook = Webhook(url="https://example.com/webhook", is_active=True, trigger_on=TriggerOn.ALL_FAILURES)
    payload = {"status": JobStatus.SUCCESS}
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        service = NotificationService()
        await service.send_webhook(webhook, payload)
        mock_post.assert_not_called()
