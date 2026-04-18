resource "aws_s3_bucket" "media" {
  count = var.create_media_bucket ? 1 : 0

  bucket        = local.media_bucket_name
  force_destroy = var.media_bucket_force_destroy
}

resource "aws_s3_bucket_ownership_controls" "media" {
  count = var.create_media_bucket ? 1 : 0

  bucket = aws_s3_bucket.media[0].id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "media" {
  count = var.create_media_bucket ? 1 : 0

  bucket = aws_s3_bucket.media[0].id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = !var.media_bucket_public_read_enabled
  restrict_public_buckets = !var.media_bucket_public_read_enabled
}

resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  count = var.create_media_bucket ? 1 : 0

  bucket = aws_s3_bucket.media[0].id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_versioning" "media" {
  count = var.create_media_bucket ? 1 : 0

  bucket = aws_s3_bucket.media[0].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_cors_configuration" "media" {
  count = var.create_media_bucket && length(var.media_bucket_cors_allowed_origins) > 0 ? 1 : 0

  bucket = aws_s3_bucket.media[0].id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = var.media_bucket_cors_allowed_methods
    allowed_origins = var.media_bucket_cors_allowed_origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "media" {
  count = var.create_media_bucket && var.media_bucket_expiration_days != null ? 1 : 0

  bucket = aws_s3_bucket.media[0].id

  rule {
    id     = "media-expiration"
    status = "Enabled"

    filter {}

    expiration {
      days = var.media_bucket_expiration_days
    }
  }
}

data "aws_iam_policy_document" "media_public_read" {
  count = var.create_media_bucket && var.media_bucket_public_read_enabled ? 1 : 0

  statement {
    sid    = "PublicReadForMediaObjects"
    effect = "Allow"

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    actions = ["s3:GetObject"]

    resources = [
      "${aws_s3_bucket.media[0].arn}/*",
    ]
  }
}

resource "aws_s3_bucket_policy" "media_public_read" {
  count = var.create_media_bucket && var.media_bucket_public_read_enabled ? 1 : 0

  bucket = aws_s3_bucket.media[0].id
  policy = data.aws_iam_policy_document.media_public_read[0].json
}

data "aws_iam_policy_document" "media_rw" {
  count = var.create_media_bucket && var.create_media_access_policy ? 1 : 0

  statement {
    sid    = "ListMediaBucket"
    effect = "Allow"

    actions = [
      "s3:ListBucket",
      "s3:GetBucketLocation",
    ]

    resources = [
      aws_s3_bucket.media[0].arn,
    ]
  }

  statement {
    sid    = "ReadWriteMediaObjects"
    effect = "Allow"

    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:AbortMultipartUpload",
    ]

    resources = [
      "${aws_s3_bucket.media[0].arn}/*",
    ]
  }
}

resource "aws_iam_policy" "media_rw" {
  count = var.create_media_bucket && var.create_media_access_policy ? 1 : 0

  name        = "${local.name_prefix}-media-rw"
  description = "Read/write access for Diary to Discovery media assets."
  policy      = data.aws_iam_policy_document.media_rw[0].json
}
