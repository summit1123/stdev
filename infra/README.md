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

## Today's Fastest Path

For the current app, the fastest stable move is:

1. Keep the API container doing background OCR, image generation, and
   ffmpeg mixing.
2. Store uploaded and generated media in the Terraform-managed S3 bucket.
3. Keep entry state and result JSON in the app store for now.
4. Attach the generated media IAM policy to the API runtime role.

If you use direct S3 URLs, enable public read on the bucket. If you put
CloudFront in front later, keep the bucket private and point
`MEDIA_S3_PUBLIC_BASE_URL` at the CDN domain instead.

The deploy command can sit on top of this. A practical flow is:

1. `./deploy.sh` builds and uploads the web bundle.
2. The same script runs your API redeploy command.
3. Terraform only runs when the deploy environment says it should.

## Recommended AWS Deployment Shape

The repository is now aligned around one repeatable AWS flow:

- Runtime: EC2 instance (`c7i.2xlarge` by default) + Docker Compose
- Reverse proxy: Nginx on the EC2 host
- Media: S3 bucket + IAM policy for runtime access
- DNS: Cloudflare in front of the EC2 origin

Terraform manages the infrastructure itself. `deploy.sh` handles the
artifact push:

1. `terraform apply` creates or updates the EC2 host, EIP, IAM, security
   group, and the media bucket.
2. `./deploy.sh` pushes the runtime secrets to SSM Parameter Store.
3. The same script triggers an SSM Run Command on the instance.
4. The instance pulls the latest repo, builds the web app, rebuilds the
   API container, and brings `docker compose` back up.

## First Real Apply

1. Copy the examples:

```bash
cp infra/service/backend.hcl.example infra/service/backend.hcl
cp infra/service/terraform.tfvars.example infra/service/terraform.tfvars
cp deploy.env.example deploy.env
```

2. Fill in:

- the real Terraform state bucket/table in `backend.hcl`
- the real Cloudflare-facing domains in `terraform.tfvars`
- any VPC/subnet overrides if you do not want the default VPC
- `.env` locally with the real `OPENAI_API_KEY` and
  `ELEVENLABS_API_KEY`

3. Initialize and review the plan:

```bash
terraform -chdir=infra/service init -backend-config=backend.hcl
terraform -chdir=infra/service plan
```

4. Apply when the diff looks right:

```bash
terraform -chdir=infra/service apply
```

5. Then deploy code:

```bash
./deploy.sh
```

6. Point Cloudflare DNS records at the Terraform output `ec2_public_ip`:

- `diary-app.summit1123.co.kr` -> A record -> `ec2_public_ip`
- `diary-api.summit1123.co.kr` -> A record -> `ec2_public_ip`

Keep Cloudflare proxied if you want the public hostname to stay stable
while the origin remains plain HTTP on port 80.
