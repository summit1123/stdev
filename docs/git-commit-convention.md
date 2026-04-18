# Git Commit Convention

이 저장소는 Conventional Commits 형식을 기본으로 사용합니다.

커밋 메시지는 **타입은 영문**, **설명은 한국어**로 작성합니다.

기본 형식:

```text
type: 변경 내용을 한국어로 한 줄 요약
```

권장 타입:

- `feat`: 기능 추가 또는 사용자 가치가 늘어나는 변경
- `fix`: 버그 수정
- `refactor`: 동작 변화 없는 구조 개선
- `design`: UI 스타일, 레이아웃, 인터랙션 개선
- `docs`: 문서 작성 및 수정
- `test`: 테스트 추가 또는 수정
- `chore`: 설정, 스크립트, 빌드, 의존성 정리

예시:

```text
feat: 일기 업로드 후 OCR 확인 화면 연결
fix: 소라 영상 생성 후 결과 URL 반영 오류 수정
design: OCR 단계 레이아웃을 2단 카드 구조로 정리
docs: 커밋 규칙과 작업 흐름 문서 추가
chore: 원격 저장소 연결과 gitignore 정리
```

작업 원칙:

1. 기능 단위로 작게 커밋합니다.
2. 화면 수정과 백엔드 수정이 분리 가능하면 나눠 커밋합니다.
3. 생성 산출물, 로그, 로컬 환경 파일은 커밋하지 않습니다.
4. 중요한 변경 전후에는 가능한 한 바로 푸시합니다.

권장 흐름:

1. 변경
2. 로컬 확인
3. `git add`
4. 한국어 Conventional Commit
5. `git push`

푸시 예시:

```bash
git add .
git commit -m "feat: 일기 결과 화면에 소라 영상 연결"
git push origin main
```
