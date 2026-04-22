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
  architectures = ["arm64"]
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
