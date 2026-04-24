output "ecr_repository_url" {
  description = "ECR repository URL — use this as the image URI base in deploy.sh"
  value       = aws_ecr_repository.app.repository_url
}

output "s3_bucket_name" {
  description = "S3 bucket name for the SQLite database"
  value       = aws_s3_bucket.db.id
}

output "lambda_function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.app.arn
}

output "lambda_function_name" {
  description = "Lambda function name (for manual invocations)"
  value       = aws_lambda_function.app.function_name
}

output "weekly_lambda_function_arn" {
  description = "Weekly market research Lambda ARN"
  value       = aws_lambda_function.weekly.arn
}

output "weekly_lambda_function_name" {
  description = "Weekly market research Lambda name (for manual invocations)"
  value       = aws_lambda_function.weekly.function_name
}
