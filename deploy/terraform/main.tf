terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# ── ECR ────────────────────────────────────────────────────────────────────────

resource "aws_ecr_repository" "app" {
  name                 = "warhammer-scout"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep only the 3 most recent images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 3
      }
      action = { type = "expire" }
    }]
  })
}

# ── S3 ─────────────────────────────────────────────────────────────────────────

resource "aws_s3_bucket" "db" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket_versioning" "db" {
  bucket = aws_s3_bucket.db.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "db" {
  bucket                  = aws_s3_bucket.db.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ── IAM ────────────────────────────────────────────────────────────────────────

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  name               = "warhammer-scout-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

resource "aws_iam_role_policy_attachment" "basic_execution" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "s3_db" {
  statement {
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.db.arn}/${var.s3_db_key}"]
  }

  # s3:ListBucket must be on the bucket ARN (not the object ARN).
  # Without it, AWS returns 403 AccessDenied instead of NoSuchKey when the
  # object is absent — the first-run fresh-start branch in lambda_handler.py
  # would never be reached.
  statement {
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.db.arn]
  }
}

resource "aws_iam_role_policy" "s3_db" {
  name   = "s3-db-access"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.s3_db.json
}

# ── Lambda ─────────────────────────────────────────────────────────────────────

resource "aws_lambda_function" "app" {
  function_name = "warhammer-scout"
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.app.repository_url}:latest"
  architectures = ["x86_64"]
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory

  environment {
    variables = {
      EBAY_CLIENT_ID             = var.ebay_client_id
      EBAY_CLIENT_SECRET         = var.ebay_client_secret
      ANTHROPIC_API_KEY          = var.anthropic_api_key
      TELEGRAM_BOT_TOKEN         = var.telegram_bot_token
      TELEGRAM_CHAT_ID           = var.telegram_chat_id
      TELEGRAM_DIGEST_BOT_TOKEN  = var.telegram_digest_bot_token
      TELEGRAM_DIGEST_CHAT_ID    = var.telegram_digest_chat_id
      TELEGRAM_FANTASY_BOT_TOKEN = var.telegram_fantasy_bot_token
      TELEGRAM_FANTASY_CHAT_ID   = var.telegram_fantasy_chat_id
      S3_BUCKET                  = var.bucket_name
      S3_DB_KEY                  = var.s3_db_key
    }
  }

  # image_uri is managed by deploy.sh (docker push + update-function-code),
  # not by Terraform — ignore drift so `terraform apply` doesn't revert it.
  lifecycle {
    ignore_changes = [image_uri]
  }
}

# ── Lambda (weekly market research) ───────────────────────────────────────────

resource "aws_lambda_function" "weekly" {
  function_name = "warhammer-scout-weekly"
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.app.repository_url}:latest"
  architectures = ["x86_64"]
  timeout       = 300
  memory_size   = var.lambda_memory

  image_config {
    command = ["lambda_weekly_handler.lambda_handler"]
  }

  environment {
    variables = {
      EBAY_CLIENT_ID             = var.ebay_client_id
      EBAY_CLIENT_SECRET         = var.ebay_client_secret
      ANTHROPIC_API_KEY          = var.anthropic_api_key
      TELEGRAM_BOT_TOKEN         = var.telegram_bot_token
      TELEGRAM_CHAT_ID           = var.telegram_chat_id
      TELEGRAM_DIGEST_BOT_TOKEN  = var.telegram_digest_bot_token
      TELEGRAM_DIGEST_CHAT_ID    = var.telegram_digest_chat_id
      TELEGRAM_FANTASY_BOT_TOKEN = var.telegram_fantasy_bot_token
      TELEGRAM_FANTASY_CHAT_ID   = var.telegram_fantasy_chat_id
      S3_BUCKET                  = var.bucket_name
      S3_DB_KEY                  = var.s3_db_key
    }
  }

  lifecycle {
    ignore_changes = [image_uri]
  }
}

# ── EventBridge (daily trigger) ────────────────────────────────────────────────

resource "aws_cloudwatch_event_rule" "daily" {
  name                = "warhammer-scout-daily"
  description         = "Trigger warhammer-scout Lambda on a daily schedule"
  schedule_expression = var.schedule_expression
}

resource "aws_cloudwatch_event_target" "lambda" {
  rule      = aws_cloudwatch_event_rule.daily.name
  target_id = "warhammer-scout"
  arn       = aws_lambda_function.app.arn
}

resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.app.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily.arn
}

# ── EventBridge (weekly trigger) ───────────────────────────────────────────────

resource "aws_cloudwatch_event_rule" "weekly" {
  name                = "warhammer-scout-weekly"
  description         = "Trigger warhammer-scout-weekly Lambda every Sunday"
  schedule_expression = var.weekly_schedule_expression
}

resource "aws_cloudwatch_event_target" "weekly_lambda" {
  rule      = aws_cloudwatch_event_rule.weekly.name
  target_id = "warhammer-scout-weekly"
  arn       = aws_lambda_function.weekly.arn
}

resource "aws_lambda_permission" "eventbridge_weekly" {
  statement_id  = "AllowEventBridgeInvokeWeekly"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.weekly.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.weekly.arn
}

# ── CloudWatch Alarms ──────────────────────────────────────────────────────────

resource "aws_sns_topic" "alerts" {
  name = "warhammer-scout-alerts"
}

resource "aws_lambda_function" "alert" {
  function_name = "warhammer-scout-alerts"
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.app.repository_url}:latest"
  architectures = ["x86_64"]
  timeout       = 30
  memory_size   = 128

  image_config {
    command = ["lambda_alert_handler.lambda_handler"]
  }

  environment {
    variables = {
      TELEGRAM_BOT_TOKEN = var.telegram_bot_token
      TELEGRAM_CHAT_ID   = var.telegram_chat_id
    }
  }

  lifecycle {
    ignore_changes = [image_uri]
  }
}

resource "aws_lambda_permission" "sns_alert" {
  statement_id  = "AllowSNSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.alert.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.alerts.arn
}

resource "aws_sns_topic_subscription" "lambda" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.alert.arn
}

resource "aws_cloudwatch_metric_alarm" "daily_errors" {
  alarm_name          = "warhammer-scout-daily-errors"
  alarm_description   = "Daily scan Lambda returned an error"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = aws_lambda_function.app.function_name }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "weekly_errors" {
  alarm_name          = "warhammer-scout-weekly-errors"
  alarm_description   = "Weekly digest Lambda returned an error"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = aws_lambda_function.weekly.function_name }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "daily_not_run" {
  alarm_name          = "warhammer-scout-daily-not-invoked"
  alarm_description   = "Daily scan Lambda was not invoked in the last 48 hours — EventBridge may be broken"
  namespace           = "AWS/Lambda"
  metric_name         = "Invocations"
  dimensions          = { FunctionName = aws_lambda_function.app.function_name }
  statistic           = "Sum"
  period              = 86400
  evaluation_periods  = 2
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
