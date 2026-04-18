# kwail API

FastAPI 기반 백엔드입니다.

## 실행

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

API는 저장소 루트 `.env`를 읽습니다.

## 주요 책임

- 이미지 업로드와 엔트리 생성
- OpenAI OCR / STT
- 결과 스키마 생성
- 장면 이미지와 설명 대본 생성
- TTS 생성
- ffmpeg 설명 영상 렌더링
- Card Chat 응답
- 보관함 / 미션 로그 / 미디어 URL 제공

## 테스트

```bash
uv run pytest tests -q
```

## 선택적 S3 미디어 저장

```bash
MEDIA_STORAGE_BACKEND=s3
MEDIA_S3_BUCKET=your-media-bucket
MEDIA_S3_REGION=ap-northeast-2
MEDIA_S3_PREFIX=media
MEDIA_S3_PUBLIC_BASE_URL=https://cdn.example.com
PUBLIC_API_BASE_URL=https://diary-api.example.com
```

메모:

- OCR, 이미지 편집, ffmpeg 렌더링은 로컬 경로 기준으로 먼저 처리됩니다.
- 업로드가 성공하면 최종 미디어 URL은 S3 또는 CDN 기준으로 바뀔 수 있습니다.
- S3를 쓰지 않으면 `/media/...` 경로를 API가 그대로 제공합니다.
