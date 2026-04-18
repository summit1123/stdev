# kwail

kwail은 아이의 손글씨 일기나 음성 기록을 받아, 오늘 장면을 과학 질문과 관찰 미션으로 바꾸는 멀티모달 탐구 서비스입니다.

긴 글을 한 번에 쏟아내는 대신, 결과를 아래 흐름으로 압축합니다.

1. 읽기 확인
2. 질문 씨앗 3개 이내
3. 미니 실험 카드 1개
4. 과학 해석 이미지와 설명 영상
5. 다시 돌아오게 만드는 관찰 루프

## 지금 동작하는 핵심 기능

- 손글씨 일기 이미지 업로드
- OpenAI 비전 기반 OCR과 수정 단계
- 탐정 모드 / 발명가 모드 / 탐험가 모드
- 상황 이미지 생성
- 24초 이미지 기반 설명 영상 렌더링
- Card Chat으로 카드별 추가 질문
- 관찰 로그 저장과 보관함 다시 보기
- ElevenLabs 우선 TTS, OpenAI TTS 보조

## 제품 구조

- Web: React + Vite + TypeScript
- API: FastAPI + Pydantic
- AI:
  - OpenAI Vision / Responses / `gpt-image-1`
  - ElevenLabs TTS 우선, `gpt-4o-mini-tts` 보조
- Media:
  - ffmpeg 이미지 시퀀스 영상 믹싱
  - 로컬 미디어 저장 + 선택적 S3 업로드
- Infra:
  - Terraform
  - EC2 + Docker Compose + Nginx
  - Cloudflare public hostname
  - SSM Parameter Store for runtime secrets

## 현재 AI 흐름

현재 프로덕션 경로는 "멀티 에이전트 군집"이 아니라, 하나의 오케스트레이션 파이프라인 위에 카드 채팅을 얹는 구조입니다.

- OCR과 구조화 추출
- 콘텐츠 생성
- 이미지 생성
- TTS 생성
- ffmpeg 영상 렌더링
- 결과 저장
- 카드별 후속 질문은 Card Chat API가 처리

자세한 시스템/AI 구조는 [docs/architecture/README.md](/Users/gimdonghyeon/Desktop/cscodex/stdev/docs/architecture/README.md)에서 Mermaid로 볼 수 있습니다.

## 로컬 실행

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
pnpm dev --host 0.0.0.0 --port 4175
```

- Web: `http://localhost:4175`
- API: `http://localhost:8000`

## 환경 변수

루트 `.env`에서 읽습니다.

주요 키는 아래입니다.

- `OPENAI_API_KEY`
- `ELEVENLABS_API_KEY`
- `TTS_PROVIDER=auto`
- `MEDIA_STORAGE_BACKEND`
- `MEDIA_S3_BUCKET`
- `PUBLIC_API_BASE_URL`

예시는 [.env.example](/Users/gimdonghyeon/Desktop/cscodex/stdev/.env.example)에 있습니다.

## 배포

현재 배포 구조는 EC2 한 대를 기준으로 돌아갑니다.

- App: [https://diary-app.summit1123.co.kr](https://diary-app.summit1123.co.kr)
- API: [https://diary-api.summit1123.co.kr](https://diary-api.summit1123.co.kr)

배포는 아래 흐름으로 맞춰져 있습니다.

1. `terraform apply`로 인프라 상태를 맞춘다.
2. `./deploy.sh`가 SSM에 런타임 시크릿을 밀어 넣는다.
3. 같은 스크립트가 EC2에서 최신 `main`을 pull하고 재빌드한다.

인프라 상세는 [infra/README.md](/Users/gimdonghyeon/Desktop/cscodex/stdev/infra/README.md)를 보면 됩니다.

## 테스트와 검증

### API 테스트

```bash
uv run --project apps/api pytest apps/api/tests -q
```

### Web 빌드

```bash
pnpm --filter web build
```

## 저장소 정리 원칙

- 제품과 직접 관련 없는 오케스트레이터/하네스 스크립트는 저장소에서 제거했습니다.
- 제품 문서, 배포 문서, 인프라 문서만 남깁니다.
- 커밋 메시지는 [docs/git-commit-convention.md](/Users/gimdonghyeon/Desktop/cscodex/stdev/docs/git-commit-convention.md)를 따릅니다.
