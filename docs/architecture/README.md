# kwail Architecture

이 문서는 현재 배포된 kwail의 실제 구조를 기준으로 정리한 아키텍처 문서입니다.

핵심 원칙은 두 가지입니다.

- 지금 돌아가는 구조만 적습니다.
- 미래 구상은 현재 구조와 섞지 않습니다.

## 1. 서비스 아키텍처

```mermaid
flowchart LR
    U["User Browser"] --> CF["Cloudflare"]
    CF --> N["Nginx on EC2"]

    subgraph EC2["EC2 Runtime"]
      N --> W["Web static bundle<br/>Vite build output"]
      N --> A["FastAPI API container"]
      A --> D["Local entry store<br/>JSON + uploaded diary + rendered media"]
      A --> F["ffmpeg video mixer"]
    end

    A --> O["OpenAI<br/>Vision + Responses + gpt-image-1"]
    A --> E["ElevenLabs TTS<br/>(fallback: OpenAI TTS)"]
    A --> S["S3 media bucket<br/>(optional public delivery)"]
    A --> P["SSM Parameter Store"]
```

### 메모

- 공개 도메인은 Cloudflare가 받습니다.
- 실제 런타임은 EC2 한 대입니다.
- 웹 정적 파일과 API는 같은 EC2의 Nginx 뒤에서 서비스됩니다.
- 영상은 Sora를 기본으로 쓰지 않고, 이미지 시퀀스를 ffmpeg로 합성합니다.

## 2. AI 처리 흐름

```mermaid
flowchart TD
    I["Diary image upload"] --> OCR["OpenAI Vision OCR"]
    OCR --> EDIT["User reviews and edits text"]
    EDIT --> PLAN["OpenAI content planning<br/>summary + questions + experiment + interpretation + video plan"]
    PLAN --> IMG["Scene image generation"]
    PLAN --> TTS["Narration TTS"]
    PLAN --> BOARD["Storyboard frame plan"]
    IMG --> MIX["ffmpeg mixes storyboard video"]
    TTS --> MIX
    BOARD --> MIX
    MIX --> SAVE["Persist result JSON + media"]
    SAVE --> UI["Result page"]
    UI --> CHAT["Card Chat API<br/>question follow-up by card context"]
```

### 메모

- 현재 메인 경로는 단일 오케스트레이션 파이프라인입니다.
- Card Chat은 생성 완료 후 카드별 질문을 이어주는 보조 인터랙션입니다.
- 즉, “멀티 에이전트가 각각 따로 결과를 만든다”가 아니라 “하나의 결과를 만든 뒤 카드별 대화를 붙인다”가 현재 상태에 맞는 설명입니다.

## 3. 결과물 구조

```mermaid
flowchart LR
    R["Entry Result"] --> C1["Summary / scene cards"]
    R --> C2["Question seeds"]
    R --> C3["Experiment card"]
    R --> C4["Scientific interpretation"]
    R --> C5["Scene image"]
    R --> C6["Quiz + game panel"]
    R --> C7["Narration audio"]
    R --> C8["24s mixed video"]
    R --> C9["Mission log + library"]
```

## 4. 배포 플로우

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant TF as Terraform
    participant SSM as AWS SSM
    participant EC2 as EC2 runtime
    participant CF as Cloudflare

    Dev->>TF: terraform apply
    TF-->>Dev: EC2 / EIP / IAM / S3 state synced
    Dev->>SSM: ./deploy.sh pushes runtime secrets
    Dev->>EC2: ./deploy.sh triggers SSM Run Command
    EC2->>EC2: git pull origin/main
    EC2->>EC2: build web + rebuild api container
    EC2-->>CF: origin stays reachable
    CF-->>Dev: public domains serve updated app
```

## 5. 현재 공개 엔드포인트

- App: [https://diary-app.summit1123.co.kr](https://diary-app.summit1123.co.kr)
- API: [https://diary-api.summit1123.co.kr](https://diary-api.summit1123.co.kr)

## 6. 문서 범위 밖

아래는 현재 기본 아키텍처 문서 범위 밖입니다.

- Sora를 기본 영상 파이프라인으로 쓰는 구조
- 진짜 멀티 에이전트 워커 오케스트레이션
- 교실/LMS 연동
- 실시간 멀티유저
