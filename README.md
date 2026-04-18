# Diary to Discovery

아이의 손글씨 일기나 음성 기록을 과학적 질문, 실험 미션, 설명 음성, 짧은 영상으로 이어 주는 멀티모달 에듀테크 데모입니다.

## Stack

- Web: React + Vite + TypeScript
- API: FastAPI + Pydantic
- AI: OpenAI Responses / Audio APIs
- Storage: local filesystem for demo persistence

## Golden Path

1. 일기 이미지 또는 음성 파일을 올립니다.
2. OpenAI OCR/STT 결과를 확인하고 원문을 바로 고칩니다.
3. AI가 상황 이미지, 과학 해석, 게임형 콘텐츠, 질문 씨앗, 실험 카드, 설명 음성을 만듭니다.
4. 시나리오를 바탕으로 12초 분량의 과학 해석 영상을 렌더링합니다.
5. 결과를 저장하고, 미션 로그를 남기고, 이전 세션을 다시 엽니다.

## Product Surface

- 실제 업로드와 샘플 3종
- OCR 수정 단계
- 3가지 콘텐츠 모드
- Live status와 단계별 진행 표시
- 상황 이미지 + 12초 영상 + AI 음성
- 과학 해석 패널 + 과학 게임 패널
- 미션 루프 기록과 최근 세션 라이브러리

## Models

- OCR / 구조화 추출: `gpt-5.4-mini`
- 교육 콘텐츠 정리: `gpt-5.4-mini`
- TTS: `gpt-4o-mini-tts`
- STT: `gpt-4o-mini-transcribe`
- 이미지 생성: `gpt-image-1`
- 영상 생성: `sora-2-pro`
- moderation: `omni-moderation-latest`

## Run

### API

```bash
cd apps/api
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

### Web

```bash
cd apps/web
pnpm install
pnpm dev --host 0.0.0.0 --port 4173
```

웹은 `http://localhost:4173`, API는 `http://localhost:8000`입니다.

## Infrastructure

Hackathon infrastructure is managed as a single Terraform stack under
`infra/service`.

- guide: `infra/README.md`
- import runbook: `infra/service/imports.md`
- inventory helper: `bash scripts/aws_inventory.sh`

## Git Workflow

- 커밋 규칙은 `docs/git-commit-convention.md`를 따릅니다.
- 커밋 메시지는 `feat: 한국어 설명` 형태로 작성합니다.
- 로컬 산출물과 비밀키는 `.gitignore`로 제외합니다.
