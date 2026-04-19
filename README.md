# kwail

![kwail key visual](./assets/readme/kwail-a4.png)

kwail은 아이의 손글씨 일기나 음성 기록을 받아, 오늘의 장면을 과학 질문과 관찰 미션으로 바꾸는 탐구 서비스입니다.

일기를 채점하지 않고, 감정과 사건을 관찰 가능한 질문으로 바꾸는 데 집중합니다.  
결과는 길게 설명하지 않고, 바로 읽고 바로 이어갈 수 있는 카드형 흐름으로 정리합니다.

1. 읽기 확인
2. 질문 씨앗
3. 미니 실험
4. 상황 이미지와 설명 영상
5. 내일 다시 이어 보는 관찰 루프

## 핵심 기능

- 손글씨 일기 이미지 업로드
- OCR 추출 텍스트 확인 및 수정
- 탐정 모드 / 발명가 모드 / 탐험가 모드 선택
- 질문 카드와 미니 실험 카드 생성
- 상황 이미지와 24초 설명 영상 생성
- 내레이션 음성 생성
- 관찰 로그 저장과 보관함 다시 보기
- 결과 카드별 추가 질문을 위한 Card Chat

## 구성

- Web: React + Vite + TypeScript
- API: FastAPI + Pydantic
- AI:
  - OpenAI Vision / Responses / `gpt-image-1`
  - ElevenLabs TTS 우선, `gpt-4o-mini-tts` 보조
- Media:
  - ffmpeg 기반 이미지 시퀀스 영상 렌더링
  - 로컬 저장 + 선택적 S3 업로드
- Infra:
  - Terraform
  - EC2 + Docker Compose + Nginx
  - Cloudflare public hostname
  - SSM Parameter Store

자세한 구조는 [docs/architecture/README.md](/Users/gimdonghyeon/Desktop/cscodex/stdev/docs/architecture/README.md)에서 확인할 수 있습니다.

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

루트 `.env`에서 읽습니다. 주요 키는 아래와 같습니다.

- `OPENAI_API_KEY`
- `ELEVENLABS_API_KEY`
- `TTS_PROVIDER=auto`
- `MEDIA_STORAGE_BACKEND`
- `MEDIA_S3_BUCKET`
- `PUBLIC_API_BASE_URL`

예시는 [.env.example](/Users/gimdonghyeon/Desktop/cscodex/stdev/.env.example)에 있습니다.

## 배포

현재 배포는 EC2 한 대를 기준으로 운영합니다.

- App: [https://diary-app.summit1123.co.kr](https://diary-app.summit1123.co.kr)
- API: [https://diary-api.summit1123.co.kr](https://diary-api.summit1123.co.kr)

배포 흐름은 아래와 같습니다.

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

커밋 메시지 규칙은 [docs/git-commit-convention.md](/Users/gimdonghyeon/Desktop/cscodex/stdev/docs/git-commit-convention.md)를 따릅니다.
