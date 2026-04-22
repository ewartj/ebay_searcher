"""
AWS Lambda entry point for the weekly market research job.

Execution flow:
  1. Download prices.db from S3 into /tmp
  2. Run genre_tracker  — records this week's eBay median prices per author/series
  3. Run weekly_digest  — asks Claude to summarise trends + Reddit signals, sends to Telegram
  4. Upload prices.db back to S3

Triggered every Sunday via EventBridge (see deploy/terraform/main.tf).
"""
import logging

import boto3
from botocore.exceptions import ClientError

import config
from main import setup_logging
from scripts.genre_tracker import run_genre_tracker
from scripts.weekly_digest import run_weekly_digest


def lambda_handler(event: dict, context: object) -> dict:
    setup_logging()
    log = logging.getLogger("warhammer_scout")

    if not config.S3_BUCKET:
        log.error("S3_BUCKET is not set — cannot persist database. Aborting.")
        return {"statusCode": 500, "body": "S3_BUCKET not configured"}

    s3 = boto3.client("s3")

    # --- Download DB from S3 ---
    try:
        s3.download_file(config.S3_BUCKET, config.S3_DB_KEY, config.DB_PATH)
        log.info("Downloaded DB from s3://%s/%s", config.S3_BUCKET, config.S3_DB_KEY)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "NoSuchKey":
            log.info("No existing DB on S3 — starting fresh")
        else:
            log.error("Failed to download DB from S3: %s", e)
            return {"statusCode": 500, "body": "S3 download failed"}

    # --- Run weekly job ---
    try:
        tracker_result = run_genre_tracker()
        digest_result = run_weekly_digest()
    except Exception:
        log.exception("Unhandled exception in weekly job")
        return {"statusCode": 500, "body": "Weekly job raised an unexpected error"}

    if tracker_result != 0 or digest_result != 0:
        log.error("Weekly job returned non-zero (tracker=%s digest=%s) — DB not uploaded", tracker_result, digest_result)
        return {"statusCode": 500, "body": "Weekly job failed"}

    # --- Upload DB back to S3 ---
    try:
        s3.upload_file(config.DB_PATH, config.S3_BUCKET, config.S3_DB_KEY)
        log.info("Uploaded DB to s3://%s/%s", config.S3_BUCKET, config.S3_DB_KEY)
    except ClientError as e:
        log.error("Failed to upload DB to S3: %s", e)
        return {"statusCode": 500, "body": "S3 upload failed"}

    return {"statusCode": 200, "body": "ok"}
