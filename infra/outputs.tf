# =====================================================================
# Outputs
# =====================================================================

output "GITHUB_ACTION_ROLE_ARN" {
  value       = aws_iam_role.github_actions_role.arn
  description = "Role ARN for GitHub Actions OIDC"
}

output "instance_id" {
  value       = aws_instance.trading_bot_server.id
  description = "EC2 Instance ID for GitHub Secret (AWS_EC2_INSTANCE_ID)"
}
