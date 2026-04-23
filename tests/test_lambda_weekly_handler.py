"""Tests for lambda_weekly_handler.py — S3 sync paths and return-value handling."""
import pytest

pytest.importorskip("boto3", reason="boto3 not installed; run: uv sync --group lambda")

from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

import config
import lambda_weekly_handler


def _s3_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "test"}}, "operation")


@pytest.fixture(autouse=True)
def _silence_logging():
    with patch("lambda_weekly_handler.setup_logging"):
        yield


class TestLambdaWeeklyHandlerS3:
    def test_missing_s3_bucket_aborts(self):
        with patch.object(config, "S3_BUCKET", ""):
            result = lambda_weekly_handler.lambda_handler({}, None)
        assert result["statusCode"] == 500
        assert "S3_BUCKET" in result["body"]

    @pytest.mark.parametrize("code", ["NoSuchKey", "404"])
    def test_first_run_missing_object_proceeds_and_uploads(self, code):
        s3 = MagicMock()
        s3.download_file.side_effect = _s3_error(code)
        with patch.object(config, "S3_BUCKET", "my-bucket"), \
             patch("boto3.client", return_value=s3), \
             patch.object(lambda_weekly_handler, "run_genre_tracker", return_value=0), \
             patch.object(lambda_weekly_handler, "run_weekly_digest", return_value=0):
            result = lambda_weekly_handler.lambda_handler({}, None)
        assert result["statusCode"] == 200
        s3.upload_file.assert_called_once()

    def test_s3_download_error_returns_500_and_skips_job(self):
        s3 = MagicMock()
        s3.download_file.side_effect = _s3_error("AccessDenied")
        with patch.object(config, "S3_BUCKET", "my-bucket"), \
             patch("boto3.client", return_value=s3), \
             patch.object(lambda_weekly_handler, "run_genre_tracker") as mock_tracker:
            result = lambda_weekly_handler.lambda_handler({}, None)
        assert result["statusCode"] == 500
        assert result["body"] == "S3 download failed"
        mock_tracker.assert_not_called()

    def test_tracker_failure_returns_500_and_skips_upload(self):
        s3 = MagicMock()
        with patch.object(config, "S3_BUCKET", "my-bucket"), \
             patch("boto3.client", return_value=s3), \
             patch.object(lambda_weekly_handler, "run_genre_tracker", return_value=1), \
             patch.object(lambda_weekly_handler, "run_weekly_digest", return_value=0):
            result = lambda_weekly_handler.lambda_handler({}, None)
        assert result["statusCode"] == 500
        s3.upload_file.assert_not_called()

    def test_digest_failure_returns_500_and_skips_upload(self):
        s3 = MagicMock()
        with patch.object(config, "S3_BUCKET", "my-bucket"), \
             patch("boto3.client", return_value=s3), \
             patch.object(lambda_weekly_handler, "run_genre_tracker", return_value=0), \
             patch.object(lambda_weekly_handler, "run_weekly_digest", return_value=1):
            result = lambda_weekly_handler.lambda_handler({}, None)
        assert result["statusCode"] == 500
        s3.upload_file.assert_not_called()

    def test_both_succeed_uploads_and_returns_200(self):
        s3 = MagicMock()
        with patch.object(config, "S3_BUCKET", "my-bucket"), \
             patch("boto3.client", return_value=s3), \
             patch.object(lambda_weekly_handler, "run_genre_tracker", return_value=0), \
             patch.object(lambda_weekly_handler, "run_weekly_digest", return_value=0):
            result = lambda_weekly_handler.lambda_handler({}, None)
        assert result["statusCode"] == 200
        s3.upload_file.assert_called_once()

    def test_s3_upload_error_returns_500(self):
        s3 = MagicMock()
        s3.upload_file.side_effect = _s3_error("NoSuchBucket")
        with patch.object(config, "S3_BUCKET", "my-bucket"), \
             patch("boto3.client", return_value=s3), \
             patch.object(lambda_weekly_handler, "run_genre_tracker", return_value=0), \
             patch.object(lambda_weekly_handler, "run_weekly_digest", return_value=0):
            result = lambda_weekly_handler.lambda_handler({}, None)
        assert result["statusCode"] == 500
        assert result["body"] == "S3 upload failed"

    def test_exception_in_job_returns_500_and_skips_upload(self):
        s3 = MagicMock()
        with patch.object(config, "S3_BUCKET", "my-bucket"), \
             patch("boto3.client", return_value=s3), \
             patch.object(lambda_weekly_handler, "run_genre_tracker", side_effect=RuntimeError("boom")):
            result = lambda_weekly_handler.lambda_handler({}, None)
        assert result["statusCode"] == 500
        assert "unexpected error" in result["body"]
        s3.upload_file.assert_not_called()
