variable "region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-2"
}

variable "bucket_name" {
  description = "S3 bucket name for SQLite persistence"
  type        = string
}

variable "s3_db_key" {
  description = "S3 object key for the SQLite database file"
  type        = string
  default     = "warhammer-scout/prices.db"
}

variable "ebay_client_id" {
  description = "eBay API client ID"
  type        = string
  sensitive   = true
}

variable "ebay_client_secret" {
  description = "eBay API client secret"
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key"
  type        = string
  sensitive   = true
}

variable "telegram_bot_token" {
  description = "Telegram bot token (Warhammer alerts)"
  type        = string
  sensitive   = true
}

variable "telegram_chat_id" {
  description = "Telegram chat ID (Warhammer alerts)"
  type        = string
  sensitive   = true
}

variable "telegram_digest_bot_token" {
  description = "Telegram bot token (weekly digest)"
  type        = string
  sensitive   = true
}

variable "telegram_digest_chat_id" {
  description = "Telegram chat ID (weekly digest)"
  type        = string
  sensitive   = true
}

variable "telegram_fantasy_bot_token" {
  description = "Telegram bot token (fantasy/sci-fi alerts) — leave empty to disable"
  type        = string
  sensitive   = true
  default     = ""
}

variable "telegram_fantasy_chat_id" {
  description = "Telegram chat ID (fantasy/sci-fi alerts) — leave empty to disable"
  type        = string
  sensitive   = true
  default     = ""
}

variable "schedule_expression" {
  description = "EventBridge cron expression for the daily scan (UTC)"
  type        = string
  default     = "cron(0 7 * * ? *)"
}

variable "weekly_schedule_expression" {
  description = "EventBridge cron expression for the weekly market research job (UTC)"
  type        = string
  default     = "cron(0 8 ? * SUN *)"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 900
}

variable "lambda_memory" {
  description = "Lambda function memory in MB"
  type        = number
  default     = 512
}
