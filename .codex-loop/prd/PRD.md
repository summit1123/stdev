# Product Requirements Document

## Working title

Diary to Discovery

## Problem

아이의 일기는 감정 표현에서 끝나는 경우가 많습니다. 이 서비스는 일기를
평가하거나 교정하지 않고, 관찰과 질문의 출발점으로 바꾸어 과학적 탐구
습관을 만드는 것을 목표로 합니다.

## Users

- Primary user: 초등 고학년 ~ 중학생과 함께 보는 보호자, 행사 데모 운영자
- Secondary user: 교사, 교육 콘텐츠 심사위원, 해커톤 관람자

## Outcome

- 아이는 자기 경험에서 질문을 발견합니다.
- 보호자와 교사는 평가가 아니라 관찰 대화를 이어갈 수 있습니다.
- 데모에서는 업로드 후 15초 안에 구조화된 결과를, 이어서 이미지·음성·짧은 영상을 보여줍니다.

## Core flows

1. 사용자는 첫 화면에서 이미지 업로드 또는 샘플 일기를 바로 선택합니다.
2. 시스템은 추출 텍스트를 보여주고, 사용자는 필요한 경우 수정합니다.
3. 시스템은 질문 씨앗, 과학 해석, 게임형 콘텐츠, 상황 이미지, 내레이션 오디오를 생성합니다.
4. 시스템은 시나리오 기반으로 12초 분량의 과학 해석 영상을 생성하거나, 실패 시 카드 결과를 유지합니다.
5. 사용자는 결과를 저장하고 다시 보며, 다음 관찰 기록을 남깁니다.

## Functional requirements

- 일기 이미지 업로드
- 음성 업로드
- 추출 텍스트 확인 및 수정
- OpenAI 기반 구조화 분석
- 질문 카드 최대 3개
- 실험 카드 1개
- 과학 해석 패널
- 과학 게임 패널
- 상황 이미지 생성
- 짧은 TTS 내레이션
- 시나리오 텍스트와 shot list
- 12초 영상 렌더링
- 결과 저장과 다시 보기
- 미션 로그 저장
- 샘플 3종 fallback

## Non-functional requirements

- 성능: 첫 구조화 결과 15초 내 목표, 미디어는 이어서 상태 표시와 함께 생성
- 신뢰성: OpenAI 실패 시 fallback 콘텐츠 제공
- 보안: API 키는 서버 환경변수로만 사용
- 접근성: 모바일 우선, 버튼/폼 명확한 라벨 제공
- 안전: 진단/평가/낙인 표현 금지, moderation 적용
- 제품성: 첫 화면은 실제 툴 워크스페이스여야 하며, 우측 보조 패널은 독립 스크롤이 가능해야 함

## AI behavior

- 일기 구조화: `gpt-5.4-mini`
- 결과 정제: `gpt-5.4-mini`
- TTS: `gpt-4o-mini-tts`
- STT: `gpt-4o-mini-transcribe`
- 이미지 생성: `gpt-image-1`
- 영상 스트레치: `sora-2-pro`
- moderation: `omni-moderation-latest`
- fallback: 샘플 결과 + 규칙 기반 생성
- privacy: 데모는 로컬 파일 저장만 사용하고 최소 메타데이터만 기록

## Design direction

- 연구노트와 편집 도구가 만나는 따뜻한 작업 공간
- 검정 타이포 중심, 민트/코랄/옐로 포인트
- 첫 화면부터 실제 업로드 경험과 결과 캔버스 제공
- 데스크톱에서는 source / main canvas / inspector의 3열 구조
- 상태, 라이브러리, 미션은 메인 캔버스와 분리된 보조 패널에서 다룸

## Canonical states

- `created`: 새 세션 준비
- `queued`: 분석 요청 접수
- `parsing`: OCR 또는 STT 진행
- `text_ready`: 원문 수정 가능
- `planning`: 구조화 추론 진행
- `rendering_image`: 상황 이미지 생성
- `rendering_audio`: 설명 음성 생성
- `rendering_video`: 12초 영상 생성
- `completed`: 결과 완료
- `failed`: 오류 또는 fallback 결과 사용

## Non-goals

- 심리 진단 또는 성격 판정
- 관계 점수화
- 긴 챗봇 대화
- LMS, 교실 관리, 멀티유저 협업
- 영상이 준비되지 않았는데도 완성인 척하는 데모 화면

## Acceptance bar

- 웹에서 업로드 -> 수정 -> 분석 -> 이미지/오디오/영상 -> 저장 흐름이 동작
- 샘플 일기 3종 이상이 안정적으로 재현
- 실패 상태와 fallback 상태가 명확히 보임
- 과학 해석, 게임형 콘텐츠, 미션 루프가 같은 결과 세션 안에 저장됨
- 실제 런타임 스크린샷 또는 영상 캡처가 남아 있음
- lint/build/backend test가 통과
