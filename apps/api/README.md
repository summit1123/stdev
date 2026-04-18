# kwail API

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

The API reads environment variables from the repository root `.env`.
Use `.env.example` as the starting point for local or deployed values.

## Optional S3 media storage

Keep the API container doing the background work, but push generated media
to S3 by setting:

```bash
MEDIA_STORAGE_BACKEND=s3
MEDIA_S3_BUCKET=your-media-bucket
MEDIA_S3_REGION=ap-northeast-2
MEDIA_S3_PREFIX=media
MEDIA_S3_PUBLIC_BASE_URL=https://cdn.example.com
```

Notes:

- Files are still written locally first so OCR, image edits, and ffmpeg
  mixing can keep using local paths.
- Public URLs switch to S3 or CloudFront when upload succeeds.
- If S3 is not configured, the API keeps using local `/media/...` URLs.
