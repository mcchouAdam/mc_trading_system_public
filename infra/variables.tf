# =====================================================================
# Cloudflare Parameter Store Variables
# =====================================================================

variable "CLOUDFLARE_API_TOKEN" {
  description = "Cloudflare API Token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "CLOUDFLARE_ACCOUNT_ID" {
  description = "Cloudflare Account ID"
  type        = string
  sensitive   = true
}

variable "CLOUDFLARE_ZONE_ID" {
  description = "Cloudflare Zone ID for the domain"
  type        = string
  sensitive   = true
}

variable "CLOUDFLARE_ZONE_NAME" {
  description = "Domain name (e.g. mc-trading.link)"
  type        = string
}

variable "CLOUDFLARE_INGRESS_RULES" {
  description = "List of ingress rules for the tunnel"
  type = list(object({
    hostname = string
    service  = string
  }))
}

# =====================================================================
# AWS SSM Parameter Store Variables
# =====================================================================
variable "CAPITAL_API_KEY" {
  description = "Capital API Key"
  type        = string
  sensitive   = true
}

variable "CAPITAL_PASSWORD" {
  description = "Capital Password"
  type        = string
  sensitive   = true
}

variable "CAPITAL_LOGIN_ID" {
  description = "Capital Login ID"
  type        = string
  sensitive   = true
}

variable "CAPITAL_REST_URL" {
  type = string
}

variable "VITE_API_BASE_URL" {
  description = "The base URL for the API utilized by the frontend"
  type        = string
}

# DB & Tools Creds
variable "POSTGRES_HOST" {
  default = "mc-postgres"
}
variable "POSTGRES_USER" {}
variable "POSTGRES_PASSWORD" {
  sensitive = true
}
variable "POSTGRES_PORT" {}
variable "POSTGRES_DB" {
  default = "trading_db"
}
variable "REDIS_HOST" {}
variable "REDIS_PORT" {}
variable "REDIS_PASSWORD" {
  sensitive = true
}
# Monitoring Alert Variables
variable "ALERT_EMAIL" {
  description = "Destination email for system alerts"
  type        = string
}

variable "SMTP_USER" {
  description = "SMTP user for sending alert emails"
  type        = string
}

variable "SMTP_PASS" {
  description = "SMTP password for sending alert emails"
  type        = string
  sensitive   = true
}
