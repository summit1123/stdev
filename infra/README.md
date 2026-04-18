# Terraform Management

This repository uses a single Terraform stack for the hackathon phase.

The goal is not to split frontend and backend right now. The goal is to
bring the current AWS footprint under one repeatable management flow so
that new changes stop living only in the AWS console.

## What Terraform Means Here

Terraform is the source of truth for AWS infrastructure changes:

- Git tracks what changed.
- Terraform state tracks which real AWS resources belong to this code.
- `terraform plan` shows what would change before anything is applied.

For an existing AWS setup, Git alone is not enough. Existing resources
must be imported into Terraform state before Terraform can manage them
safely.

## Hackathon Direction

For today we keep one stack:

- one repository
- one service-level Terraform root
- one remote state
- logical grouping inside files only

That keeps the management model small while still making later splits
possible if the service grows.

## Layout

- `infra/service`: single Terraform root for the current service
- `infra/service/imports.md`: import order and command patterns
- `scripts/aws_inventory.sh`: quick AWS inventory helper

## Quick Start

1. Log in to AWS in the same shell you will use for Terraform.
2. Run `bash scripts/aws_inventory.sh`.
3. Copy `infra/service/backend.hcl.example` to `infra/service/backend.hcl`.
4. Copy `infra/service/terraform.tfvars.example` to `infra/service/terraform.tfvars`.
5. Fill in the real project, region, domain, and tag values.
6. Run:

```bash
cd infra/service
terraform init -backend-config=backend.hcl
terraform plan
```

At this point Terraform is initialized, but it still does not manage the
existing AWS resources. Follow `infra/service/imports.md` to import them
one by one, then keep running `terraform plan` until the remaining diff
is understood.

## Suggested First Targets

Start with low-risk resources before touching IAM or shared networking:

1. S3 buckets
2. CloudFront distributions
3. Route53 records
4. ECR repositories
5. App Runner or ECS services
6. ACM certificates
7. Security groups, VPC, IAM last
