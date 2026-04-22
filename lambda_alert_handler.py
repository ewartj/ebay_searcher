"""
Receives CloudWatch alarm notifications via SNS and forwards them to Telegram.
Triggered by the warhammer-scout-alerts SNS topic.
"""
import json
import logging
import os

import httpx

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def lambda_handler(event: dict, context: object) -> dict:
    for record in event.get("Records", []):
        try:
            message = json.loads(record["Sns"]["Message"])
        except (KeyError, json.JSONDecodeError):
            log.warning("Could not parse SNS record: %s", record)
            continue

        alarm_name = message.get("AlarmName", "Unknown alarm")
        state = message.get("NewStateValue", "UNKNOWN")
        reason = message.get("NewStateReason", "")

        icon = "🔴" if state == "ALARM" else "✅"
        text = f"{icon} Warhammer Scout — {alarm_name}\n\n{state}: {reason}"

        try:
            httpx.post(
                f"https://api.telegram.org/bot{_BOT_TOKEN}/sendMessage",
                json={"chat_id": _CHAT_ID, "text": text},
                timeout=10,
            ).raise_for_status()
        except httpx.HTTPError as e:
            log.error("Failed to send Telegram alert: %s", e)

    return {"statusCode": 200}
