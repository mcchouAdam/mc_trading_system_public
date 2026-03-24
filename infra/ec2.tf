# =====================================================================
# EC2 Instance & AMI
# =====================================================================

# 1. Get the latest Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}

# 2. Create EC2 instance (t3.small used for this setup)
resource "aws_instance" "trading_bot_server" {
  ami           = data.aws_ami.amazon_linux_2023.id
  instance_type = "t3.small" 
  
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name
  vpc_security_group_ids = [aws_security_group.trading_sg.id]

  root_block_device {
    volume_size = 16
    volume_type = "gp3"
  }

  user_data = <<-EOF
              #!/bin/bash
              # Setup 2GB Swap file for stability on small instances
              if [ ! -f /swapfile ]; then
                  dd if=/dev/zero of=/swapfile bs=128M count=16
                  chmod 600 /swapfile
                  mkswap /swapfile
                  swapon /swapfile
                  echo '/swapfile swap swap defaults 0 0' >> /etc/fstab
              fi

              # Update system
              dnf update -y
              
              # Install and start Docker
              dnf install -y docker
              systemctl enable docker
              systemctl start docker
              
              # Add default user ec2-user to docker group (no sudo required)
              usermod -aG docker ec2-user
              
              # Install Docker Compose
              curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
              chmod +x /usr/local/bin/docker-compose
              
              # Create project directory
              mkdir -p /home/ec2-user/mc_trading_system
              chown -R ec2-user:ec2-user /home/ec2-user/mc_trading_system
              
              # ==========================================
              # Install PowerShell for Monitor Script
              # ==========================================
              dnf install -y https://github.com/PowerShell/PowerShell/releases/download/v7.4.1/powershell-7.4.1-1.rh.x86_64.rpm
              EOF

  tags = {
    Name = "MCTradingEngine"
  }

  lifecycle {
    ignore_changes = [
      ami,
      user_data,
    ]
  }
}
