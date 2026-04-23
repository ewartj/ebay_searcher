"""Tests for lambda_alert_handler.py — SNS record parsing and Telegram forwarding."""
import json
from unittest.mock import MagicMock, patch

import pytest
import httpx

import lambda_alert_handler


def _sns_event(alarm_name: str, state: str, reason: str = "test reason") -> dict:
    message = json.dumps({
        "AlarmName": alarm_name,
        "NewStateValue": state,
        "NewStateReason": reason,
    })
    return {"Records": [{"Sns": {"Message": message}}]}


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "test-chat")
    # Reload module-level constants after env is patched
    import importlib
    importlib.reload(lambda_alert_handler)


class TestAlertHandler:
    def test_alarm_state_sends_red_icon(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        with patch("lambda_alert_handler.httpx.post", return_value=mock_response) as mock_post:
            lambda_alert_handler.lambda_handler(_sns_event("my-alarm", "ALARM"), None)
        text = mock_post.call_args.kwargs["json"]["text"]
        assert "🔴" in text
        assert "my-alarm" in text

    def test_ok_state_sends_green_icon(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        with patch("lambda_alert_handler.httpx.post", return_value=mock_response) as mock_post:
            lambda_alert_handler.lambda_handler(_sns_event("my-alarm", "OK"), None)
        text = mock_post.call_args.kwargs["json"]["text"]
        assert "✅" in text

    def test_returns_200(self):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        with patch("lambda_alert_handler.httpx.post", return_value=mock_response):
            result = lambda_alert_handler.lambda_handler(_sns_event("my-alarm", "ALARM"), None)
        assert result["statusCode"] == 200

    def test_malformed_record_does_not_crash(self):
        event = {"Records": [{"Sns": {"Message": "not-json"}}]}
        result = lambda_alert_handler.lambda_handler(event, None)
        assert result["statusCode"] == 200

    def test_missing_records_does_not_crash(self):
        result = lambda_alert_handler.lambda_handler({}, None)
        assert result["statusCode"] == 200

    def test_telegram_http_error_returns_500(self):
        with patch("lambda_alert_handler.httpx.post", side_effect=httpx.HTTPError("fail")):
            result = lambda_alert_handler.lambda_handler(_sns_event("my-alarm", "ALARM"), None)
        assert result["statusCode"] == 500

    def test_multiple_records_sends_multiple_messages(self):
        event = {
            "Records": [
                {"Sns": {"Message": json.dumps({"AlarmName": "alarm-1", "NewStateValue": "ALARM", "NewStateReason": "r"})}},
                {"Sns": {"Message": json.dumps({"AlarmName": "alarm-2", "NewStateValue": "ALARM", "NewStateReason": "r"})}},
            ]
        }
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        with patch("lambda_alert_handler.httpx.post", return_value=mock_response) as mock_post:
            lambda_alert_handler.lambda_handler(event, None)
        assert mock_post.call_count == 2

    def test_first_record_failure_does_not_skip_second(self):
        event = {
            "Records": [
                {"Sns": {"Message": json.dumps({"AlarmName": "alarm-1", "NewStateValue": "ALARM", "NewStateReason": "r"})}},
                {"Sns": {"Message": json.dumps({"AlarmName": "alarm-2", "NewStateValue": "ALARM", "NewStateReason": "r"})}},
            ]
        }
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        with patch("lambda_alert_handler.httpx.post", side_effect=[httpx.HTTPError("fail"), mock_response]) as mock_post:
            result = lambda_alert_handler.lambda_handler(event, None)
        assert mock_post.call_count == 2
        assert result["statusCode"] == 500
