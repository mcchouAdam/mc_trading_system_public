# =====================================================================
# Cloudflare Tunnel & DNS Management
# =====================================================================

# Random ID for the tunnel secret
resource "random_id" "tunnel_secret" {
  byte_length = 32
}

# 1. Create the Tunnel Resource
resource "cloudflare_zero_trust_tunnel_cloudflared" "mc_tunnel" {
  account_id = var.CLOUDFLARE_ACCOUNT_ID
  name       = "mc-trading-tunnel"
  secret     = random_id.tunnel_secret.b64_std
}

# 2. Ingress Rules
resource "cloudflare_zero_trust_tunnel_cloudflared_config" "mc_tunnel_config" {
  account_id = var.CLOUDFLARE_ACCOUNT_ID
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.mc_tunnel.id

  config {
    dynamic "ingress_rule" {
      for_each = var.CLOUDFLARE_INGRESS_RULES
      content {
        hostname = ingress_rule.value.hostname
        service  = ingress_rule.value.service
      }
    }
    # Important: Catch-all rule for 404
    ingress_rule {
      service  = "http_status:404"
    }
  }
}

# 3. DNS Records pointing to our terraform-managed tunnel
resource "cloudflare_record" "dynamic_dns" {
  for_each = { for rule in var.CLOUDFLARE_INGRESS_RULES : rule.hostname => rule }
  
  zone_id = var.CLOUDFLARE_ZONE_ID
  name    = each.value.hostname == var.CLOUDFLARE_ZONE_NAME ? "@" : split(".", each.value.hostname)[0]
  content = "${cloudflare_zero_trust_tunnel_cloudflared.mc_tunnel.id}.cfargotunnel.com"
  type    = "CNAME"
  proxied = true
  allow_overwrite = true
}
