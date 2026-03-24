# =====================================================================
# Security Groups
# =====================================================================

# Security Group: No inbound ports opened; all outbound traffic allowed for downloads
resource "aws_security_group" "trading_sg" {
  name        = "mc_trading_sg"
  description = "Security group for trading bot (SSM only, no SSH required)"

  ingress = []

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
