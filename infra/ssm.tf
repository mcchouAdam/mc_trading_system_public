# =====================================================================
# AWS SSM Parameter Store (Secrets Management)
# =====================================================================

locals {
  # Consolidate all secrets to be stored in SSM here for maintenance
  trading_secrets = {
    "CAPITAL_API_KEY"      = var.CAPITAL_API_KEY
    "CAPITAL_PASSWORD"     = var.CAPITAL_PASSWORD
    "CAPITAL_LOGIN_ID"     = var.CAPITAL_LOGIN_ID
    "CAPITAL_REST_URL"     = var.CAPITAL_REST_URL
    "AWS_REGION"           = data.aws_region.current.name
    "AWS_EC2_INSTANCE_ID"  = aws_instance.trading_bot_server.id
    "VITE_API_BASE_URL"    = var.VITE_API_BASE_URL
    "POSTGRES_USER"        = var.POSTGRES_USER
    "POSTGRES_PASSWORD"    = var.POSTGRES_PASSWORD
    "POSTGRES_DB"          = var.POSTGRES_DB
    "REDIS_PASSWORD"       = var.REDIS_PASSWORD
    "REDIS_HOST"           = var.REDIS_HOST
    "REDIS_PORT"           = var.REDIS_PORT
    "POSTGRES_HOST"        = var.POSTGRES_HOST
    "POSTGRES_PORT"        = var.POSTGRES_PORT
    "ALERT_EMAIL"          = var.ALERT_EMAIL
    "SMTP_USER"            = var.SMTP_USER
    "SMTP_PASS"            = var.SMTP_PASS
    "CLOUDFLARE_TUNNEL_TOKEN" = cloudflare_zero_trust_tunnel_cloudflared.mc_tunnel.tunnel_token
  }
}

resource "aws_ssm_parameter" "trading_params" {
  for_each = local.trading_secrets

  name      = "/mc_trading/prod/${each.key}"
  type      = contains(["CAPITAL_REST_URL", "AWS_REGION", "AWS_EC2_INSTANCE_ID", "VITE_API_BASE_URL"], each.key) ? "String" : "SecureString"
  value     = each.value
  overwrite = true

  tags = {
    Project = "MCTrading"
  }
}
