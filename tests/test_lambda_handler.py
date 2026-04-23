"""Tests for lambda_handler.py — S3 sync paths and error handling."""
import pytest

pytest.importorskip("boto3", reason="boto3 not installed; run: uv sync --group lambda")

from unittest.mock import MagicMock, patch

from botocore.exceptions import ClientError

import config
import lambda_handler


def _s3_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "test"}}, "operation")


@pytest.fixture(autouse=True)
def _silence_logging():
    with patch("lambda_handler.setup_logging"):
        yield


class TestLambdaHandlerS3:
    def test_missing_s3_bucket_aborts(self):
        with patch.object(config, "S3_BUCKET", ""):
            result = lambda_handler.lambda_handler({}, None)
        assert result["statusCode"] == 500
        assert "S3_BUCKET" in result["body"]

    @pytest.mark.parametrize("code", ["NoSuchKey", "404"])
    def test_first_run_missing_object_proceeds_and_uploads(self, code):
        s3 = MagicMock()
        s3.download_file.side_effect = _s3_error(code)
        with patch.object(config, "S3_BUCKET", "my-bucket"), \
             patch("boto3.client", return_value=s3), \
             patch.object(lambda_handler, "run_scan", return_value=0):
            result = lambda_handler.lambda_handler({}, None)
        assert result["statusCode"] == 200
        s3.upload_file.assert_called_once()

    def test_s3_download_other_error_returns_500_generic_message(self):
        s3 = MagicMock()
        s3.download_file.side_effect = _s3_error("AccessDenied")
        with patch.object(config, "S3_BUCKET", "my-bucket"), \
             patch("boto3.client", return_value=s3), \
             patch.object(lambda_handler, "run_scan") as mock_scan:
            result = lambda_handler.lambda_handler({}, None)
        assert result["statusCode"] == 500
        assert result["body"] == "S3 download failed"
        # botocore error detail must not leak into the response
        assert "AccessDenied" not in result["body"]
        mock_scan.assert_not_called()

    def test_scan_success_uploads_db_and_returns_200(self):
        s3 = MagicMock()
        with patch.object(config, "S3_BUCKET", "my-bucket"), \
             patch("boto3.client", return_value=s3), \
             patch.object(lambda_handler, "run_scan", return_value=0):
            result = lambda_handler.lambda_handler({}, None)
        assert result["statusCode"] == 200
        s3.upload_file.assert_called_once_with(
            config.DB_PATH, "my-bucket", config.S3_DB_KEY
        )

    def test_scan_failure_skips_upload_and_returns_500(self):
        s3 = MagicMock()
        with patch.object(config, "S3_BUCKET", "my-bucket"), \
             patch("boto3.client", return_value=s3), \
             patch.object(lambda_handler, "run_scan", return_value=1):
            result = lambda_handler.lambda_handler({}, None)
        assert result["statusCode"] == 500
        s3.upload_file.assert_not_called()

    def test_s3_upload_error_returns_500_generic_message(self):
        s3 = MagicMock()
        s3.upload_file.side_effect = _s3_error("NoSuchBucket")
        with patch.object(config, "S3_BUCKET", "my-bucket"), \
             patch("boto3.client", return_value=s3), \
             patch.object(lambda_handler, "run_scan", return_value=0):
            result = lambda_handler.lambda_handler({}, None)
        assert result["statusCode"] == 500
        assert result["body"] == "S3 upload failed"
        assert "NoSuchBucket" not in result["body"]

    def test_run_scan_exception_returns_500_and_skips_upload(self):
        s3 = MagicMock()
        with patch.object(config, "S3_BUCKET", "my-bucket"), \
             patch("boto3.client", return_value=s3), \
             patch.object(lambda_handler, "run_scan", side_effect=RuntimeError("boom")):
            result = lambda_handler.lambda_handler({}, None)
        assert result["statusCode"] == 500
        assert "unexpected error" in result["body"]
        s3.upload_file.assert_not_called()
