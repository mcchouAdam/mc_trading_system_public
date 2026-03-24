terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = "ap-east-2"
}

provider "cloudflare" {
  api_token = var.CLOUDFLARE_API_TOKEN
}

# Data sources for global use
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
