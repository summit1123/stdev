# Import Runbook

This stack is for existing AWS resources that were created before
Terraform was introduced.

## Core Rule

Do not start with `terraform apply`.

For every existing resource:

1. declare the Terraform resource block
2. import the real AWS resource into state
3. run `terraform plan`
4. adjust the code until the diff is expected
5. only then allow changes through Terraform

## Recommended Order

1. S3 buckets
2. CloudFront distributions
3. Route53 records
4. ECR repositories
5. App Runner or ECS services
6. ACM certificates
7. Security groups, VPC, IAM

## Prep

```bash
bash scripts/aws_inventory.sh
cd infra/service
terraform init -backend-config=backend.hcl
terraform plan
```

If `terraform plan` cannot read the account identity, your AWS login is
not available in the current shell yet.

## Common Import Patterns

### S3 bucket

```bash
terraform import aws_s3_bucket.media diary-to-discovery-media
terraform import aws_s3_bucket_ownership_controls.media diary-to-discovery-media
terraform import aws_s3_bucket_public_access_block.media diary-to-discovery-media
terraform import aws_s3_bucket_server_side_encryption_configuration.media diary-to-discovery-media
terraform import aws_s3_bucket_versioning.media diary-to-discovery-media
```

Related resources are often separate in Terraform and may also need
imports:

- `aws_s3_bucket_policy`
- `aws_s3_bucket_cors_configuration`
- `aws_s3_bucket_lifecycle_configuration`

If Terraform will create the bucket from scratch instead of importing it,
the most useful first outputs are:

- `media_bucket_name`
- `media_bucket_public_base_url`
- `media_access_policy_arn`

### CloudFront distribution

```bash
terraform import aws_cloudfront_distribution.web E1234567890ABC
```

### Route53 record

Route53 imports use `ZONEID_RECORDNAME_TYPE`:

```bash
terraform import aws_route53_record.web Z1234567890ABC_app.summit1123.co.kr_A
terraform import aws_route53_record.api Z1234567890ABC_api.summit1123.co.kr_A
```

### ACM certificate

```bash
terraform import aws_acm_certificate.web arn:aws:acm:us-east-1:123456789012:certificate/abcd-1234
```

### ECR repository

```bash
terraform import aws_ecr_repository.api diary-to-discovery-api
```

### App Runner service

```bash
terraform import aws_apprunner_service.api arn:aws:apprunner:ap-northeast-2:123456789012:service/diary-api/abc123
```

### ECS cluster or service

```bash
terraform import aws_ecs_cluster.main arn:aws:ecs:ap-northeast-2:123456789012:cluster/diary
terraform import aws_ecs_service.api arn:aws:ecs:ap-northeast-2:123456789012:service/diary-cluster/diary-api
```

## Working Rule For Today

Keep everything in one service stack even if the runtime has separate web
and API endpoints. The split can happen later, but today's goal is
consistency:

- one Terraform root
- one state
- one review path
- one source of truth

## Practical Stop Condition

This first pass is good enough when:

- `terraform plan` runs cleanly
- imported resources map to real AWS IDs
- remaining diffs are understood
- new changes are made through Terraform instead of the console
