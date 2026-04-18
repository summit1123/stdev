resource "aws_ecr_repository" "api" {
  count = var.create_api_ecr_repository ? 1 : 0

  name                 = local.api_ecr_repository_name
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "api" {
  count = var.create_api_ecr_repository ? 1 : 0

  repository = aws_ecr_repository.api[0].name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep the last 30 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 30
        }
        action = {
          type = "expire"
        }
      },
    ]
  })
}

data "aws_iam_policy_document" "apprunner_ecr_access_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["build.apprunner.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "apprunner_ecr_access" {
  count = var.create_api_service ? 1 : 0

  name               = "${local.api_service_name}-ecr-access"
  assume_role_policy = data.aws_iam_policy_document.apprunner_ecr_access_assume_role.json
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr_access" {
  count = var.create_api_service ? 1 : 0

  role       = aws_iam_role.apprunner_ecr_access[0].name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

data "aws_iam_policy_document" "apprunner_instance_assume_role" {
  statement {
    effect = "Allow"

    principals {
      type        = "Service"
      identifiers = ["tasks.apprunner.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "apprunner_instance" {
  count = var.create_api_service ? 1 : 0

  name               = "${local.api_service_name}-instance"
  assume_role_policy = data.aws_iam_policy_document.apprunner_instance_assume_role.json
}

resource "aws_iam_role_policy_attachment" "apprunner_instance" {
  for_each = (
    var.create_api_service
    ? { for arn in local.api_runtime_policy_arns : arn => arn }
    : {}
  )

  role       = aws_iam_role.apprunner_instance[0].name
  policy_arn = each.value
}

resource "aws_apprunner_service" "api" {
  count = var.create_api_service ? 1 : 0

  service_name = local.api_service_name

  source_configuration {
    auto_deployments_enabled = var.api_auto_deployments_enabled

    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access[0].arn
    }

    image_repository {
      image_identifier      = "${local.api_image_repository_url}:${var.api_image_tag}"
      image_repository_type = "ECR"

      image_configuration {
        port                          = tostring(var.api_port)
        runtime_environment_variables = local.api_runtime_environment
        runtime_environment_secrets   = var.api_runtime_secret_arns
      }
    }
  }

  instance_configuration {
    cpu               = var.api_cpu
    memory            = var.api_memory
    instance_role_arn = aws_iam_role.apprunner_instance[0].arn
  }

  health_check_configuration {
    protocol            = "HTTP"
    path                = var.api_health_check_path
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }
}

resource "aws_apprunner_custom_domain_association" "api" {
  count = (
    var.create_api_service &&
    var.create_api_custom_domain &&
    var.api_domain != null
  ) ? 1 : 0

  service_arn          = aws_apprunner_service.api[0].arn
  domain_name          = var.api_domain
  enable_www_subdomain = false
}
