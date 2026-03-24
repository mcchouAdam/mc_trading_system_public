# =====================================================================
# ECR Repositories (Container Registry)
# =====================================================================

locals {
  ecr_repos = {
    "base_repo"   = "mc-cpp-base"
    "cpp_repo"    = "mc-cpp-ingestor"
    "auth_repo"   = "mc-auth-manager"
    "trade_repo"  = "mc-trade-manager"
    "ui_repo"     = "mc-frontend"
    "api_repo"    = "mc-api-server"
    "engine_repo" = "mc-trading-engine"
  }
}

resource "aws_ecr_repository" "repos" {
  for_each             = local.ecr_repos
  name                 = each.value
  image_tag_mutability = "MUTABLE"
  force_delete         = true
}

resource "aws_ecr_lifecycle_policy" "repo_policies" {
  for_each   = aws_ecr_repository.repos
  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 10,
        description  = "Cleanup untagged images (keep for 1 day)",
        selection = {
          tagStatus   = "untagged",
          countType   = "sinceImagePushed",
          countUnit   = "days",
          countNumber = 1
        },
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 20,
        description  = "Keep only the 3 most recent images per service",
        selection = {
          tagStatus     = "any",
          countType     = "imageCountMoreThan",
          countNumber   = 3
        },
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# State migration: Prevent Terraform from deleting existing repositories
moved {
  from = aws_ecr_repository.cpp_repo
  to   = aws_ecr_repository.repos["cpp_repo"]
}
moved {
  from = aws_ecr_repository.auth_repo
  to   = aws_ecr_repository.repos["auth_repo"]
}
moved {
  from = aws_ecr_repository.trade_repo
  to   = aws_ecr_repository.repos["trade_repo"]
}
moved {
  from = aws_ecr_repository.ui_repo
  to   = aws_ecr_repository.repos["ui_repo"]
}
moved {
  from = aws_ecr_repository.api_repo
  to   = aws_ecr_repository.repos["api_repo"]
}
moved {
  from = aws_ecr_repository.engine_repo
  to   = aws_ecr_repository.repos["engine_repo"]
}
