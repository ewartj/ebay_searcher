"""
AWS Lambda entry point for Warhammer Scout.

Execution flow:
  1. Download prices.db from S3 into /tmp  (skipped on first ever run)
  2. Run the full scan via run_scan()
  3. Upload prices.db back to S3          (only on success, preserves last good state)

Environment variables required (set in Lambda console or via Terraform/CDK):
  All variables from .env.example, plus S3_BUCKET.
  Do NOT set a .env file in Lambda — use Lambda environment variables directly.
"""
import logging

import boto3
from botocore.exceptions import ClientError

import config
from main import run_scan, setup_logging


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
        if code in ("NoSuchKey", "404"):
            log.info("No existing DB on S3 — starting fresh")
        else:
            log.error("Failed to download DB from S3: %s", e)
            return {"statusCode": 500, "body": "S3 download failed"}

    # --- Run the scan ---
    try:
        result = run_scan(dry_run=False)
    except Exception:
        log.exception("Unhandled exception in run_scan")
        return {"statusCode": 500, "body": "Scan raised an unexpected error"}

    # --- Upload DB back to S3 (only on success) ---
    if result == 0:
        try:
            s3.upload_file(config.DB_PATH, config.S3_BUCKET, config.S3_DB_KEY)
            log.info("Uploaded DB to s3://%s/%s", config.S3_BUCKET, config.S3_DB_KEY)
        except ClientError as e:
            log.error("Failed to upload DB to S3: %s", e)
            return {"statusCode": 500, "body": "S3 upload failed"}
    else:
        log.warning("Scan returned non-zero exit — DB not uploaded to preserve last good state")

    return {"statusCode": 200 if result == 0 else 500, "body": "ok" if result == 0 else "scan failed"}
