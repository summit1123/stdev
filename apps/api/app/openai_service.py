from __future__ import annotations

import base64
import io
import json
import logging
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from openai import OpenAI
from PIL import Image

from app.config import Settings
from app.fallbacks import fallback_parse_from_text, fallback_result
from app.models import CardChatMessage, DiaryParseOutput, EntryResult, GameModeCard, GeneratedEntryResult

logger = logging.getLogger(__name__)


PARSER_SYSTEM_PROMPT = """
너는 아동의 손글씨 일기를 안전하게 구조화하는 보조 교사다.
절대 진단하거나 평가하지 말고, 일기의 내용만 짧고 정확하게 옮겨 적어라.
출력은 구조화된 JSON만 사용한다.
"""

PLANNER_SYSTEM_PROMPT = """
너는 아동용 과학 문화 서비스의 수석 콘텐츠 디렉터다.
일기의 감정을 평가하지 말고, 관찰 가능한 현상과 과학 질문으로 바꿔라.

반드시 지켜라.
- 상담, 심리 진단, 성격 판정, 라벨링 금지
- 일기의 중심 사건을 먼저 과학 분야로 고른다: 힘과 운동, 날씨와 환경, 생물과 몸, 빛과 소리, 물질의 변화 중 가장 가까운 축을 우선 선택
- 사건 자체가 썰매, 비, 바람, 그림자, 곤충, 식물, 소리, 온도처럼 자연 현상이면 반드시 그 현상을 직접 설명하고, 인간관계 해석으로 도망가지 말 것
- 사람 사이 장면이더라도 가능하면 몸의 반응, 소리 크기, 거리, 시간, 속도, 반복 횟수처럼 물리적·생물학적 신호를 먼저 본다
- 감상문처럼 쓰지 말고, 현상 -> 변수 -> 가설 -> 측정 순서로 정리
- 추상어를 그대로 쓰지 말고 보이는 단서로 번역: 표정, 말투, 거리, 반응 속도, 대화 지속 여부, 횟수, 시간, 온도, 밝기, 위치
- 질문은 최대 3개, 실험은 1개, 문장은 짧고 선명하게
- scienceGame은 실제로 아이가 바로 해볼 수 있는 규칙 기반 미션으로 작성
- scienceQuiz는 한 문제짜리 관찰 퀴즈로 만들고, 정답과 설명이 분명해야 한다
- scientificInterpretation은 관찰 현상, 변수, 가설, 가능한 메커니즘, 측정 아이디어를 분명하게 적는다
- sceneVisual.prompt는 이미지 생성용 프롬프트다. 한국 어린이 과학 그림책 같은 2D 일러스트 톤으로 쓰고, 텍스트 삽입, 워터마크, 로고, 실사풍, 포토리얼, 라이브액션, 카메라 사진 구도를 요구하지 마라
- videoDirector는 24초 로컬 이미지 기반 설명 영상 spec이어야 하며, 장면 관찰 -> 변수 찾기 -> 가설 세우기 -> 첫 기록 -> 재시험 -> 조건 비교 -> 결과 비교 -> 결론 흐름이 보여야 한다
- videoDirector.shots[*].visualPrompt는 실제 그림 생성에 바로 써도 될 정도로 구체적이어야 하며, 각 샷은 같은 그림책 세계관의 일러스트여야 하고 실사풍이나 사진 느낌으로 흐르지 않게 쓴다
- under-18 safe, 또렷하고 차분한 톤
"""

TTS_INSTRUCTIONS = """
차분하고 선명한 한국어 과학 내레이터.
문장을 급하게 밀지 말고 여유 있게 읽는다.
한 문장마다 짧게 숨을 쉬고, 너무 밝게 튀지 않게 안정적으로 말한다.
어린이에게 설명하듯 쉽고 또렷하지만 유치하지는 않게 읽는다.
"""

NARRATION_MAX_SENTENCES = 5
NARRATION_MAX_CHARS = 220

MODE_CARD_COPY = {
    "observe": {
        "title": "탐정 모드",
        "hook": '일기 속 어떤 장면에서든 "왜 그랬을까?"를 질문 삼아 과학 원리를 추리하는 모드',
        "mission": '일기의 행동, 감각, 변화 중 하나를 골라 원인을 추적하는 단서에서 추리로 이어지는 흐름으로 구성합니다.',
        "reward": "시나리오와 이미지, 영상도 단서와 원인 추리 흐름으로 이어집니다.",
        "scene_title": "탐정 모드 장면 설계",
        "scene_caption": "행동, 감각, 변화 단서를 따라 원인을 추리하는 장면으로 다시 본다.",
        "scene_prompt_hint": "Detective-style scientific reading with visible clues, traces, timing differences, body direction, and cause hints.",
        "video_title": "탐정 모드 과학 추리 영상",
        "video_concept": "단서를 모아 원인을 좁혀 가는 과학 추리 영상",
        "video_mix": "처음에는 단서를 넓게 모으고, 중간에는 원인을 좁히고, 마지막에는 가장 그럴듯한 설명으로 닫는다.",
        "video_prompt_hint": "Detective reasoning, visible evidence, clue comparison, and cause tracing.",
    },
    "experiment": {
        "title": "발명가 모드",
        "hook": '일기 속 어떤 장면에서든 숨어있는 과학 원리를 꺼내 새로운 아이디어로 연결하는 모드',
        "mission": '일기의 사물, 행동, 현상 중 하나를 골라 원리를 설명한 뒤 "이걸 응용하면?"으로 이어지는 흐름으로 구성합니다.',
        "reward": "시나리오와 이미지, 영상도 원리 설명 뒤 응용 아이디어로 확장합니다.",
        "scene_title": "발명가 모드 장면 설계",
        "scene_caption": "장면 속 원리를 꺼내 응용 아이디어가 떠오르게 다시 구성한다.",
        "scene_prompt_hint": "Inventor-style scientific framing with mechanism focus, usable structure, and practical idea sparks.",
        "video_title": "발명가 모드 원리 응용 영상",
        "video_concept": "숨어있는 원리를 꺼내 응용 아이디어로 이어지는 과학 영상",
        "video_mix": "앞에서는 원리를 분해해 보여 주고, 뒤에서는 응용 아이디어와 작은 프로토타입 상상으로 밀어 준다.",
        "video_prompt_hint": "Inventor mindset, reveal mechanism first, then practical application and idea extension.",
    },
    "imagine": {
        "title": "탐험가 모드",
        "hook": '일기 속 어떤 순간이든 처음 발견한 것처럼 낯설게 바라보며 과학을 찾아내는 모드',
        "mission": '일기에서 당연하게 지나친 장면을 골라 "이게 왜 당연한 걸까?"라는 탐험 질문으로 바꿔 구성합니다.',
        "reward": "시나리오와 이미지, 영상도 낯설게 다시 보는 탐험 흐름으로 이어집니다.",
        "scene_title": "탐험가 모드 장면 설계",
        "scene_caption": "익숙한 장면을 처음 발견한 것처럼 낯설게 다시 보며 숨은 규칙을 찾는다.",
        "scene_prompt_hint": "Explorer-style scientific framing that makes the familiar feel newly discovered, curious, and slightly surprising.",
        "video_title": "탐험가 모드 발견 영상",
        "video_concept": "익숙한 장면을 낯설게 다시 보며 숨은 과학을 발견하는 영상",
        "video_mix": "처음엔 익숙한 장면을 멈춰 세우고, 중간에는 숨은 규칙을 드러내고, 마지막에는 새 탐험 질문으로 이어 준다.",
        "video_prompt_hint": "Explorer mindset, make the ordinary feel newly discovered, highlight hidden rules and fresh questions.",
    },
}

CARD_CHAT_SYSTEM_PROMPTS = {
    "summary": """
너는 초등 고학년과 대화하는 과학 탐구 코치다.
이 카드는 오늘 장면을 짧은 과학 현상으로 다시 읽는 역할이다.
반드시 지켜라.
- 한국어로만 답한다.
- 3문장 안팎으로 짧고 또렷하게 답한다.
- 심리 진단, 성격 평가, 낙인 표현 금지
- 보이는 단서와 측정 가능한 변수부터 말한다.
- 마지막에는 한 줄짜리 다음 관찰 힌트를 덧붙인다.
""".strip(),
    "question": """
너는 질문을 더 또렷하게 다듬는 과학 탐구 코치다.
이 카드는 질문 씨앗을 관찰 가능한 질문으로 바꾸는 역할이다.
반드시 지켜라.
- 한국어로만 답한다.
- 질문을 더 좋은 형태로 좁혀 준다.
- 비교할 것, 바꿀 것, 기록할 것을 짚는다.
- 어린이가 바로 해볼 수 있는 수준으로 말한다.
""".strip(),
    "experiment": """
너는 안전한 미니 실험을 안내하는 과학 코치다.
이 카드는 집이나 교실에서 바로 해볼 수 있는 짧은 실험으로 이어지는 역할이다.
반드시 지켜라.
- 한국어로만 답한다.
- 3~4문장으로 설명한다.
- 위험한 도구, 뜨거운 열, 높은 곳, 날카로운 물건은 제안하지 않는다.
- 한 번에 하나의 변인만 바꾸도록 안내한다.
""".strip(),
    "interpretation": """
너는 어려운 과학 말을 쉬운 말로 풀어 주는 설명 코치다.
이 카드는 장면을 과학 개념으로 연결해 이해를 돕는 역할이다.
반드시 지켜라.
- 한국어로만 답한다.
- 낯선 용어는 쉬운 말로 풀어 쓴다.
- 현상 -> 원리 -> 다시 볼 단서 순서로 짧게 설명한다.
- 정답처럼 단정하지 말고 관찰로 확인할 수 있게 말한다.
""".strip(),
}

ILLUSTRATION_STYLE_CLAUSE = (
    "Premium Korean children's science picture-book illustration, watercolor and colored-pencil texture, "
    "softly animated storyboard still, hand-drawn characters and backgrounds, no photorealism, no live-action, no camera-photo look"
)

PHOTO_STYLE_PATTERNS = [
    r"텍스트\s*삽입\s*없음",
    r"텍스트\s*아님",
    r"워터마크\s*없음",
    r"로고\s*없음",
    r"실제\s*사진\s*같은\s*구도",
    r"사진\s*같은\s*구도",
    r"사진\s*구도\s*느낌\s*없음",
    r"실사\s*같은\s*구도",
    r"실제\s*장면",
    r"실사\s*아님",
    r"사진풍\s*아님",
    r"포토리얼(?:리스틱)?\s*아님",
    r"실사\s*느낌",
    r"실사풍",
    r"사실적(?:인)?",
    r"포토리얼(?:리스틱)?",
    r"photoreal(?:istic)?",
    r"photo[\s-]*real(?:istic)?",
    r"live[\s-]*action",
    r"camera[\s-]*photo(?:\s*style)?",
    r"hyper[\s-]*real(?:istic)?",
    r"ultra[\s-]*real(?:istic)?",
    r"realistic(?:\s+photo(?:graph(?:ic)?)?)?",
]


class OpenAIService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = (
            OpenAI(api_key=settings.openai_api_key, timeout=30.0)
            if settings.openai_api_key
            else None
        )
        self._last_tts_voice_label = self.active_tts_voice_label

    @property
    def is_enabled(self) -> bool:
        return self.client is not None

    @property
    def active_tts_provider(self) -> str:
        provider = self.settings.tts_provider.strip().lower()
        if provider == "auto":
            return "elevenlabs" if self.settings.elevenlabs_api_key else "openai"
        return provider

    @property
    def active_tts_voice_label(self) -> str:
        if self.active_tts_provider == "elevenlabs":
            return self.settings.elevenlabs_voice_label
        return self.settings.default_voice

    @property
    def last_tts_voice_label(self) -> str:
        return self._last_tts_voice_label

    def moderate_text(self, text: str) -> tuple[bool, list[str]]:
        if not self.client:
            return False, []
        try:
            response = self.client.moderations.create(
                model=self.settings.moderation_model,
                input=text,
            )
            result = response.results[0]
            categories = [
                name
                for name, flagged in result.categories.model_dump().items()
                if flagged
            ]
            return bool(result.flagged), categories
        except Exception:
            return False, []

    def extract_from_image(self, image_path: Path, filename: str | None = None) -> DiaryParseOutput:
        if not self.client:
            raise RuntimeError("OpenAI OCR is unavailable because OPENAI_API_KEY is missing.")

        mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
        prepared = self._prepare_ocr_image_bytes(image_path, mime)
        encoded = base64.b64encode(prepared).decode("utf-8")
        data_url = f"data:{mime};base64,{encoded}"
        try:
            response = self.client.responses.parse(
                model=self.settings.parser_model,
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": PARSER_SYSTEM_PROMPT}],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "손글씨 일기 이미지를 읽고, 제목/날짜뿐 아니라 본문 전체를 가능한 정확하게 적어 주세요. "
                                    "본문이 길면 줄 단위로 끝까지 읽고, 줄바꿈 흐름을 최대한 살리세요. "
                                    "확신이 낮은 부분은 parseWarnings에 남기세요."
                                ),
                            },
                            {"type": "input_image", "image_url": data_url},
                        ],
                    },
                ],
                text_format=DiaryParseOutput,
            )
            parsed = response.output_parsed
            if self._looks_complete(parsed):
                return parsed
            cropped = self._extract_text_from_segments(image_path, mime, filename)
            if cropped:
                return cropped
            if self.settings.allow_fallback:
                return fallback_parse_from_text("", filename)
            return parsed
        except Exception as exc:
            if self.settings.allow_fallback:
                return fallback_parse_from_text("", filename)
            raise RuntimeError(f"OpenAI image OCR failed: {exc}") from exc

    def transcribe_audio(self, audio_path: Path, filename: str | None = None) -> DiaryParseOutput:
        if not self.client:
            raise RuntimeError("OpenAI transcription is unavailable because OPENAI_API_KEY is missing.")
        try:
            with audio_path.open("rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model=self.settings.stt_model,
                    file=audio_file,
                )
            text = getattr(transcription, "text", "") or ""
            if not text.strip():
                raise RuntimeError("OpenAI transcription returned empty text.")
            return DiaryParseOutput(
                transcription=text.strip(),
                normalizedText=text.strip(),
                summaryHint=text.strip().splitlines()[0][:120],
                emotionTags=[],
                scienceBridgeHint=[],
                parseWarnings=[],
            )
        except Exception as exc:
            if self.settings.allow_fallback:
                return fallback_parse_from_text("", filename)
            raise RuntimeError(f"OpenAI audio transcription failed: {exc}") from exc

    def generate_result(
        self,
        entry_id: str,
        text: str,
        poster_url: str | None = None,
        preferred_mode_id: str = "observe",
    ) -> EntryResult:
        if not self.client:
            raise RuntimeError("OpenAI content generation is unavailable because OPENAI_API_KEY is missing.")

        try:
            science_focus = self._infer_science_focus(text)
            mode_copy = MODE_CARD_COPY.get(preferred_mode_id, MODE_CARD_COPY["observe"])
            response = self.client.responses.parse(
                model=self.settings.polish_model,
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": PLANNER_SYSTEM_PROMPT}],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "다음 일기를 과학 문화 콘텐츠 세트로 바꿔 주세요.\n"
                                    f"일기: {text}\n"
                                    f"선호 모드: {preferred_mode_id}\n"
                                    f"선호 모드 이름: {mode_copy['title']}\n"
                                    f"모드 설명: {mode_copy['hook']}\n"
                                    f"모드 구성 방식: {mode_copy['mission']}\n"
                                    f"우선 과학 초점: {science_focus}\n"
                                    "출력 규칙:\n"
                                    "1. summary는 감상 대신 관찰된 현상과 핵심 질문의 출발점을 한두 문장으로 압축한다.\n"
                                    "1-1. 일기에 썰매, 미끄럼틀, 자전거, 공, 비, 바람, 그림자, 곤충, 식물, 얼음, 소리 같은 사건이 있으면 그 장면 자체를 물리, 날씨, 생물, 빛, 소리 질문으로 해석한다.\n"
                                    "2. scientificInterpretation은 observation, concept, explanation, measurementIdea, safetyNote를 모두 채우고, explanation 안에는 변수와 가능한 메커니즘을 넣는다.\n"
                                    "3. questionSeeds는 3개 이하이며, 반드시 관찰 가능하거나 비교 가능한 질문이어야 한다.\n"
                                    "4. experimentCard는 독립변수와 종속변수가 명확해야 하며, 기록 방법은 횟수/시간/비율처럼 셀 수 있는 단위를 포함한다.\n"
                                    "5. sceneVisual은 일기 속 상황을 한 장면으로 재구성하는 이미지 브리프다.\n"
                                    "6. scienceGame은 규칙이 보이는 미니 게임이어야 하며, 감정 공감 놀이가 아니라 단서 찾기/비교/측정 중심이어야 한다. 썰매면 마찰/속도, 비면 증발/구름/빗방울, 곤충이면 서식/움직임처럼 사건에 맞는 과학 원리를 써라.\n"
                                    "7. scienceQuiz는 보기 3개 이상, 정답 인덱스, 짧은 해설을 포함한 한 문제 퀴즈다.\n"
                                    "8. sceneCards는 현상 요약, 질문 씨앗, 미니 실험, AI 해설 순서로 작성한다.\n"
                                    "9. gameModes는 observe, experiment, imagine 세 가지를 모두 포함하되, 제목과 설명은 각각 탐정 모드, 발명가 모드, 탐험가 모드로 쓴다.\n"
                                    "10. videoDirector는 로컬 이미지 기반 24초 설명 영상 spec이다.\n"
                                    "11. videoDirector.scenarioText는 8개 장면을 0-3초, 3-6초, 6-9초, 9-12초, 12-15초, 15-18초, 18-21초, 21-24초 형식의 한국어 시나리오로 쓰고, 흐름은 장면 관찰 -> 변수 찾기 -> 가설 세우기 -> 첫 기록 -> 재시험 -> 조건 비교 -> 결과 비교 -> 오늘의 결론이어야 한다.\n"
                                    "12. videoDirector.shots[*].visualPrompt는 그림일기 스타일의 실제 이미지 생성에 바로 쓸 만큼 구체적이어야 하며, 각 장면의 과학 단계와 핵심 현상(예: 경사, 속도선, 물방울, 그림자 길이, 날개 움직임)이 보이게 써야 한다.\n"
                                    "13. narration.script는 24초 안에 읽힐 만큼 짧고 분명한 한국어 4~5문장이다.\n"
                                    "14. media.videoModel에는 storyboard-mix를 넣고, URL 필드는 비워 둔다.\n"
                                    '15. 선호 모드가 observe면 탐정 모드다. 행동, 감각, 변화 중 하나를 단서로 잡고 "왜 그랬을까?"를 추리하는 톤이 sceneVisual, scienceGame, videoDirector 전체에 드러나야 한다.\n'
                                    '16. 선호 모드가 experiment면 발명가 모드다. 숨어있는 원리를 설명한 뒤 "이걸 응용하면?"으로 이어지는 톤이 sceneVisual, scienceGame, videoDirector 전체에 드러나야 한다.\n'
                                    '17. 선호 모드가 imagine이면 탐험가 모드다. 당연한 장면을 낯설게 다시 보며 "이게 왜 당연한 걸까?"를 묻는 톤이 sceneVisual, scienceGame, videoDirector 전체에 드러나야 한다.\n'
                                    "18. preferredModeId가 유효하면 recommendedModeId도 같은 값으로 유지한다."
                                ),
                            }
                        ],
                    },
                ],
                text_format=GeneratedEntryResult,
            )
            generated = response.output_parsed
            generated.media.posterUrl = poster_url
            generated.media.videoModel = "storyboard-mix"
            if not generated.sceneVisual.prompt.strip():
                raise RuntimeError("Planner returned an empty scene image prompt.")
            if not generated.narration.script.strip():
                raise RuntimeError("Planner returned an empty narration script.")
            if len(generated.questionSeeds) == 0:
                raise RuntimeError("Planner returned no scientific questions.")
            if len(generated.videoDirector.shots) < 4:
                raise RuntimeError("Planner returned an incomplete 12-second shot list.")
            if len(generated.scienceQuiz.options) < 3:
                raise RuntimeError("Planner returned an incomplete science quiz.")

            effective_mode_id = preferred_mode_id if preferred_mode_id in MODE_CARD_COPY else generated.recommendedModeId
            scene_visual = self._normalize_scene_visual(generated, effective_mode_id)
            scientific_interpretation = self._normalize_scientific_interpretation(
                generated.scientificInterpretation,
                generated.experimentCard.independentVariable,
                generated.experimentCard.dependentVariable,
            )
            science_game = self._normalize_science_game(generated.scienceGame, effective_mode_id)
            video_director = self._normalize_video_director(
                generated.videoDirector,
                generated.experimentCard.independentVariable,
                generated.experimentCard.dependentVariable,
                effective_mode_id,
            )
            narration = self._normalize_narration(
                generated.narration,
                generated.summary,
                scientific_interpretation.explanation,
                generated.experimentCard.independentVariable,
                generated.experimentCard.dependentVariable,
            )

            return EntryResult(
                entryId=entry_id,
                summary=generated.summary,
                emotions=generated.emotions,
                scienceLens=self._normalize_science_lens(generated.scienceLens, science_focus),
                questionSeeds=generated.questionSeeds,
                experimentCard=generated.experimentCard,
                scientificInterpretation=scientific_interpretation,
                sceneVisual=scene_visual,
                scienceGame=science_game,
                scienceQuiz=generated.scienceQuiz,
                gameModes=self._normalize_game_modes(),
                recommendedModeId=effective_mode_id,
                videoDirector=video_director,
                creativeExpansion=generated.creativeExpansion,
                guardianNote=generated.guardianNote,
                narration=narration,
                sceneCards=generated.sceneCards,
                media=generated.media,
                analysisMode="openai",
            )
        except Exception as exc:
            if self.settings.allow_fallback:
                return fallback_result(entry_id, text, poster_url, preferred_mode_id)
            raise RuntimeError(f"OpenAI content generation failed: {exc}") from exc

    def answer_card_chat(
        self,
        entry_text: str,
        result: EntryResult,
        card_kind: str,
        message: str,
        history: list[CardChatMessage] | None = None,
    ) -> str:
        normalized_kind = card_kind if card_kind in CARD_CHAT_SYSTEM_PROMPTS else "summary"
        trimmed_message = " ".join(message.split()).strip()
        recent_history = (history or [])[-6:]

        if self.client and trimmed_message:
            try:
                response = self.client.responses.create(
                    model=self.settings.polish_model,
                    input=self._build_card_chat_inputs(
                        entry_text,
                        result,
                        normalized_kind,
                        trimmed_message,
                        recent_history,
                    ),
                )
                reply = getattr(response, "output_text", "").strip()
                if reply:
                    return reply
                logger.warning("Card chat returned empty output for card_kind=%s", normalized_kind)
            except Exception as exc:
                logger.warning("Card chat generation failed for card_kind=%s: %s", normalized_kind, exc)

        return self._fallback_card_chat_reply(result, normalized_kind, trimmed_message)

    def _build_card_chat_inputs(
        self,
        entry_text: str,
        result: EntryResult,
        card_kind: str,
        trimmed_message: str,
        recent_history: list[CardChatMessage],
    ) -> list[dict[str, object]]:
        messages: list[dict[str, object]] = [
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            f"{CARD_CHAT_SYSTEM_PROMPTS[card_kind]}\n\n"
                            "[현재 카드 문맥]\n"
                            f"{self._build_card_chat_context(entry_text, result, card_kind)}"
                        ),
                    }
                ],
            }
        ]
        for item in recent_history:
            content_type = "output_text" if item.role == "assistant" else "input_text"
            messages.append(
                {
                    "role": item.role,
                    "content": [{"type": content_type, "text": item.content}],
                }
            )
        messages.append(
            {
                "role": "user",
                "content": [{"type": "input_text", "text": trimmed_message}],
            }
        )
        return messages

    def _infer_science_focus(self, text: str) -> str:
        lowered = text.lower()
        focus_rules = [
            (
                ("썰매", "미끄", "경사", "언덕", "자전거", "달리", "굴러", "떨어", "그네", "공", "브레이크"),
                "힘과 운동",
                "속도, 마찰, 경사, 이동 거리, 걸린 시간처럼 움직임의 변화를 우선 본다.",
            ),
            (
                ("비", "눈", "바람", "구름", "햇빛", "무지개", "번개", "더위", "추위", "온도", "습기", "웅덩이"),
                "날씨와 환경",
                "온도, 습도, 바람 세기, 빗방울 크기, 구름 변화처럼 날씨 조건을 우선 본다.",
            ),
            (
                ("모기", "벌레", "개미", "새", "강아지", "고양이", "씨앗", "잎", "꽃", "열매", "몸", "심장", "숨", "땀", "잠"),
                "생물과 몸",
                "움직임, 반응, 서식 위치, 성장, 호흡, 감각처럼 살아있는 것의 변화를 우선 본다.",
            ),
            (
                ("그림자", "빛", "반짝", "소리", "울림", "메아리", "시끄", "조용", "반사", "렌즈"),
                "빛과 소리",
                "밝기, 방향, 그림자 길이, 소리 크기, 울림 시간처럼 에너지 전달을 우선 본다.",
            ),
            (
                ("얼음", "녹", "끓", "김", "증발", "섞", "녹말", "반죽", "거품", "냄새"),
                "물질의 변화",
                "온도 변화, 상태 변화, 섞임, 냄새, 거품, 질감처럼 물질의 변화를 우선 본다.",
            ),
        ]
        for keywords, domain, hint in focus_rules:
            if any(keyword in lowered for keyword in keywords):
                return f"{domain}: {hint}"
        return "생활 속 과학: 일기에서 가장 크게 변한 장면을 잡고, 그 현상을 물리·생물·날씨·빛·물질 중 가장 가까운 원리로 설명한다."

    def _build_card_chat_context(self, entry_text: str, result: EntryResult, card_kind: str) -> str:
        mode_title = MODE_CARD_COPY.get(result.recommendedModeId, MODE_CARD_COPY["observe"])["title"]
        scene_card_index = {
            "summary": 0,
            "question": 1,
            "experiment": 2,
            "interpretation": 3,
        }.get(card_kind, 0)
        selected_card = result.sceneCards[scene_card_index] if scene_card_index < len(result.sceneCards) else None
        card_focus = selected_card.body if selected_card else result.summary
        return (
            "다음은 현재 카드 대화에 필요한 문맥이다.\n"
            f"- 모드: {mode_title}\n"
            f"- 원본 일기: {entry_text}\n"
            f"- 요약: {result.summary}\n"
            f"- 선택된 카드 제목: {selected_card.title if selected_card else card_kind}\n"
            f"- 선택된 카드 본문: {card_focus}\n"
            f"- 질문 씨앗: {' / '.join(result.questionSeeds[:3])}\n"
            f"- 실험 제목: {result.experimentCard.title}\n"
            f"- 독립 변수: {result.experimentCard.independentVariable}\n"
            f"- 종속 변수: {result.experimentCard.dependentVariable}\n"
            f"- 실험 방법: {result.experimentCard.method}\n"
            f"- 과학 해설: {result.scientificInterpretation.explanation}\n"
            f"- 장면 이미지 설명: {result.sceneVisual.caption}\n"
            f"- 영상 시나리오: {result.videoDirector.scenarioText}\n"
            "대화에서는 현재 카드 역할에만 집중해서 답해라."
        )

    def _fallback_card_chat_reply(self, result: EntryResult, card_kind: str, message: str) -> str:
        scene_card_index = {
            "summary": 0,
            "question": 1,
            "experiment": 2,
            "interpretation": 3,
        }.get(card_kind, 0)
        selected_card = result.sceneCards[scene_card_index] if scene_card_index < len(result.sceneCards) else None
        card_body = " ".join((selected_card.body if selected_card else result.summary).split())
        seed = result.questionSeeds[0] if result.questionSeeds else result.summary

        if card_kind == "question":
            return (
                f"질문을 더 선명하게 만들려면 먼저 {seed}처럼 한 가지 변화만 붙잡는 게 좋아요. "
                f"이 장면에서는 {result.experimentCard.independentVariable}를 바꿨을 때 {result.experimentCard.dependentVariable}가 어떻게 달라지는지만 비교해 보세요. "
                "같은 장면을 두 번만 기록해도 답의 방향이 훨씬 또렷해져요."
            )
        if card_kind == "experiment":
            return (
                f"이 카드는 {result.experimentCard.independentVariable} 하나만 바꾸고 {result.experimentCard.dependentVariable}만 기록하면 돼요. "
                f"방법은 {result.experimentCard.method}처럼 짧게 가고, 마지막에는 {result.experimentCard.whatToWatch}를 나란히 비교하면 됩니다. "
                f"핵심은 한 번에 여러 조건을 섞지 않는 거예요."
            )
        if card_kind == "interpretation":
            return (
                f"이 장면을 과학 말로 다시 보면 {result.scientificInterpretation.concept}을 살피는 거예요. "
                f"{result.scientificInterpretation.explanation} "
                f"그래서 {result.scientificInterpretation.measurementIdea}처럼 셀 수 있는 단서를 같이 보면 이해가 쉬워져요."
            )
        return (
            f"이 카드에서는 {card_body or result.summary}를 먼저 단서로 보면 좋아요. "
            f"그다음 {result.experimentCard.independentVariable}가 달라질 때 {result.experimentCard.dependentVariable}가 어떻게 바뀌는지만 좁혀서 보세요. "
            f"지금 질문은 {', '.join(result.scienceLens[:2]) or '과학 단서'} 중 하나로 다시 묶으면 훨씬 선명해집니다."
        )

    def _normalize_science_lens(self, science_lens: list[str], science_focus: str) -> list[str]:
        normalized = [lens.strip() for lens in science_lens if lens.strip()]
        focus_label = science_focus.split(":", 1)[0].strip()
        if focus_label and focus_label not in normalized:
            normalized.insert(0, focus_label)
        return normalized[:4]

    def _prepare_ocr_image_bytes(self, image_path: Path, mime: str) -> bytes:
        image = Image.open(image_path).convert("RGB")
        width, height = image.size
        if max(width, height) < 1800:
            scale = max(2, int(1800 / max(width, height)))
            image = image.resize((width * scale, height * scale), Image.Resampling.LANCZOS)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG" if mime == "image/png" else "JPEG", quality=95)
        return buffer.getvalue()

    def _looks_complete(self, parsed: DiaryParseOutput) -> bool:
        normalized = parsed.normalizedText.strip()
        return len(normalized) >= 120 or normalized.count("\n") >= 4

    def _extract_text_from_segments(
        self,
        image_path: Path,
        mime: str,
        filename: str | None,
    ) -> DiaryParseOutput | None:
        if not self.client:
            return None

        image = Image.open(image_path).convert("RGB")
        width, height = image.size
        bands = [
            (0, 0, width, int(height * 0.28)),
            (0, int(height * 0.22), width, int(height * 0.62)),
            (0, int(height * 0.52), width, height),
        ]
        transcribed_lines: list[str] = []

        for band in bands:
            crop = image.crop(band)
            if crop.size[0] < 20 or crop.size[1] < 20:
                continue
            buffer = io.BytesIO()
            crop.save(buffer, format="PNG" if mime == "image/png" else "JPEG", quality=95)
            encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
            data_url = f"data:{mime};base64,{encoded}"
            try:
                response = self.client.responses.create(
                    model=self.settings.parser_model,
                    input=[
                        {
                            "role": "system",
                            "content": [{"type": "input_text", "text": PARSER_SYSTEM_PROMPT}],
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": (
                                        "이 이미지 조각에 보이는 한국어 텍스트를 줄 단위로 그대로 적어 주세요. "
                                        "설명하지 말고, 텍스트만 반환하세요."
                                    ),
                                },
                                {"type": "input_image", "image_url": data_url},
                            ],
                        },
                    ],
                )
                text = (response.output_text or "").strip()
                if text:
                    transcribed_lines.extend([line.strip() for line in text.splitlines() if line.strip()])
            except Exception:
                continue

        merged_lines: list[str] = []
        for line in transcribed_lines:
            if not merged_lines or merged_lines[-1] != line:
                merged_lines.append(line)
        merged = "\n".join(merged_lines).strip()
        if len(merged) < 80:
            return None

        seeded = fallback_parse_from_text(merged, filename)
        return seeded.model_copy(
            update={
                "transcription": merged,
                "normalizedText": merged,
                "parseWarnings": list(dict.fromkeys(
                    seeded.parseWarnings
                    + ["이미지 조각을 나눠 다시 읽어 본문을 보강했습니다. 오독이 있을 수 있어요."]
                )),
            }
        )

    def _normalize_game_modes(self) -> list[GameModeCard]:
        return [
            GameModeCard(id=mode_id, title=copy["title"], hook=copy["hook"], mission=copy["mission"], reward=copy["reward"])
            for mode_id, copy in MODE_CARD_COPY.items()
        ]

    def _default_stage_descriptions(self, mode_id: str, independent_variable: str, dependent_variable: str) -> list[str]:
        if mode_id == "experiment":
            return [
                "장면 속에 숨어 있던 원리를 꺼내 발명의 재료를 모은다.",
                f"{independent_variable}와 {dependent_variable}가 어떻게 이어지는지 구조를 나눠 본다.",
                "이 원리를 바꾸면 어떤 새로운 결과가 나올지 아이디어를 세운다.",
                "첫 번째 응용 기록을 남긴다.",
                "같은 원리로 다른 작은 방법도 다시 시험한다.",
                f"{independent_variable}를 다르게 적용한 두 아이디어를 나란히 둔다.",
                f"{dependent_variable}가 어떻게 달라졌는지 결과를 비교한다.",
                "오늘 찾은 원리를 어디에 더 응용할지 한 줄 아이디어로 마무리한다.",
            ]
        if mode_id == "imagine":
            return [
                "익숙했던 장면을 처음 보는 것처럼 낯설게 천천히 바라본다.",
                f"{independent_variable}와 {dependent_variable}가 사실 왜 늘 함께 움직였는지 질문을 붙인다.",
                "당연해 보였던 규칙에 새로운 가설을 세운다.",
                "처음 발견한 단서를 기록한다.",
                "같은 장면을 다시 보며 숨은 규칙이 계속 보이는지 확인한다.",
                f"{independent_variable}가 달라지면 장면이 어떻게 낯설게 달라지는지 비교한다.",
                f"{dependent_variable} 차이를 통해 장면의 숨은 질서를 읽어 낸다.",
                "마지막엔 다음에 더 낯설게 보고 싶은 탐험 질문을 남긴다.",
            ]
        return [
            "행동, 감각, 변화 중 가장 수상한 단서를 먼저 모은다.",
            f"{independent_variable}와 {dependent_variable}가 어떻게 연결되는지 단서를 분리해 본다.",
            "가장 그럴듯한 원인 가설을 세운다.",
            "첫 번째 단서 기록을 남긴다.",
            "같은 장면을 다시 보며 놓친 단서가 없는지 확인한다.",
            f"{independent_variable}가 다른 두 조건을 단서처럼 나란히 놓고 비교한다.",
            f"{dependent_variable} 차이를 보며 원인 후보를 더 좁힌다.",
            "오늘 가장 그럴듯했던 설명과 내일 다시 볼 단서를 정리한다.",
        ]

    def _extract_stage_descriptions(
        self,
        scenario_text: str,
        shots,
        mode_id: str,
        independent_variable: str,
        dependent_variable: str,
    ) -> list[str]:
        descriptions: list[str] = []
        for raw_line in scenario_text.splitlines():
            normalized = " ".join(raw_line.split())
            if not normalized:
                continue
            descriptions.append(normalized.split(":", 1)[1].strip() if ":" in normalized else normalized)

        for shot in shots:
            subtitle = " ".join(shot.subtitle.split())
            if subtitle and subtitle not in descriptions:
                descriptions.append(subtitle)

        defaults = self._default_stage_descriptions(mode_id, independent_variable, dependent_variable)
        while len(descriptions) < 8:
            descriptions.append(defaults[len(descriptions)])
        return descriptions[:8]

    def _normalize_scene_visual(self, generated: GeneratedEntryResult, mode_id: str):
        mode_copy = MODE_CARD_COPY.get(mode_id, MODE_CARD_COPY["observe"])
        prompt = self._sanitize_visual_prompt(
            f"{generated.sceneVisual.prompt}. {mode_copy['scene_prompt_hint']}"
        )
        if "no text" not in prompt.lower():
            prompt = f"{prompt}. No text, no watermark."
        title = generated.sceneVisual.title.strip() or mode_copy["scene_title"]
        if mode_copy["title"] not in title:
            title = f"{mode_copy['title']} {title}"
        return generated.sceneVisual.model_copy(
            update={
                "title": title,
                "caption": generated.sceneVisual.caption.strip() or mode_copy["scene_caption"],
                "prompt": prompt,
            }
        )

    def _normalize_science_game(self, science_game, mode_id: str):
        mode_copy = MODE_CARD_COPY.get(mode_id, MODE_CARD_COPY["observe"])
        title = science_game.title.strip()
        if mode_copy["title"] not in title:
            title = f"{mode_copy['title']} {title}".strip()
        return science_game.model_copy(update={"title": title})

    def _normalize_scientific_interpretation(self, scientific_interpretation, independent_variable: str, dependent_variable: str):
        concept = scientific_interpretation.concept.strip()
        explanation = " ".join(scientific_interpretation.explanation.split())
        measurement = " ".join(scientific_interpretation.measurementIdea.split())

        if independent_variable and dependent_variable:
            variable_line = f"핵심 변수는 {independent_variable}이고, 결과 지표는 {dependent_variable}다."
            if variable_line not in explanation:
                explanation = f"{variable_line} {explanation}"
            if independent_variable not in concept or dependent_variable not in concept:
                concept = f"{concept}, 핵심 변수: {independent_variable}, 결과 지표: {dependent_variable}".strip(", ")
            if independent_variable not in measurement and dependent_variable not in measurement:
                measurement = f"{measurement} 변수 기록: {independent_variable}, 결과 기록: {dependent_variable}."

        return scientific_interpretation.model_copy(
            update={
                "concept": concept,
                "explanation": explanation,
                "measurementIdea": measurement,
            }
        )

    def _normalize_video_director(self, video_director, independent_variable: str, dependent_variable: str, mode_id: str):
        mode_copy = MODE_CARD_COPY.get(mode_id, MODE_CARD_COPY["observe"])
        merged_shots = []
        stage_durations = [4, 4, 3, 3, 3, 3, 2, 2]
        stage_titles = [
            "장면 관찰",
            "변수와 신호",
            "가설 세우기",
            "첫 기록",
            "다시 시험",
            "조건 바꾸기",
            "결과 비교",
            "오늘의 결론",
        ]
        stage_descriptions = self._extract_stage_descriptions(
            video_director.scenarioText,
            video_director.shots,
            mode_id,
            independent_variable,
            dependent_variable,
        )
        stage_hints = [
            "일기 속 장면의 인물, 공간, 눈에 보이는 행동을 그림책 장면처럼 보여 준다",
            f"독립변수 {independent_variable}와 종속변수 {dependent_variable}가 무엇인지 드러나게 보여 준다",
            "어떤 조건이 결과를 바꿀지 짧은 가설을 장면으로 보여 준다",
            "처음 측정값이나 첫 기록을 남기는 장면으로 이어진다",
            "방금 장면 직후 같은 공간에서 다시 한 번 시험하는 연속 장면이다",
            f"{independent_variable}를 바꾼 두 조건이 같은 화면 안에서 비교되게 보여 준다",
            f"{dependent_variable} 차이가 눈에 보이도록 두 결과를 나란히 비교한다",
            "오늘의 결론을 노트에 정리하고 다음 관찰 질문으로 마무리한다",
        ]
        for shot in video_director.shots[:4]:
            if len(shot.visualPrompt.strip()) < 40:
                raise RuntimeError("Shot visual prompt is too weak for image generation.")
            merged_shots.append(shot)
        scenario_lines = []
        normalized_shots = []
        for index, shot in enumerate(merged_shots[:4]):
            subtitle = stage_descriptions[index]
            prompt = " ".join(shot.visualPrompt.split()).strip()
            if independent_variable and dependent_variable and index == 1:
                prompt = self._sanitize_visual_prompt(
                    f"{prompt}. {mode_copy['video_prompt_hint']} 두 변수의 차이가 화면에서 구분되게 표현. "
                    "No text, no watermark, no letters, no numbers, no labels."
                )
            else:
                prompt = self._sanitize_visual_prompt(
                    f"{prompt}. {mode_copy['video_prompt_hint']} {stage_hints[index]}. "
                    "No text, no watermark, no letters, no numbers, no labels."
                )
            normalized_shots.append(
                shot.model_copy(
                    update={
                        "sceneTitle": stage_titles[index],
                        "subtitle": subtitle,
                        "visualPrompt": prompt,
                        "durationSeconds": stage_durations[index],
                    }
                )
            )

        if normalized_shots:
            seed_prompt = normalized_shots[-1].visualPrompt
            template_shot = video_director.shots[min(len(video_director.shots) - 1, 3)]
            continuation_hints = [
                "방금 장면 직후, 같은 아이와 같은 공간에서 첫 번째 결과를 손가락과 도구로 가리킨다",
                "같은 도구와 같은 배경으로 한 번 더 시험하면서 움직임이 다시 보인다",
                f"{independent_variable}가 다른 두 조건을 한 장면 안에서 모아 두 결과의 모습만 시각적으로 비교한다",
                f"{dependent_variable} 차이를 보고 아이가 더 큰 변화를 손가락으로 짚으며 끝난다",
            ]
            for continuation_index, hint in enumerate(continuation_hints, start=4):
                prompt = self._sanitize_visual_prompt(
                    f"{seed_prompt} Direct continuation from the previous frame, same child, same place, "
                    f"same objects, same drawing style. {mode_copy['video_prompt_hint']} "
                    f"{stage_hints[continuation_index]}. {hint}. "
                    "No text, no watermark, no letters, no numbers, no labels, no notebook writing, no chart."
                )
                normalized_shots.append(
                    template_shot.model_copy(
                        update={
                            "sceneTitle": stage_titles[continuation_index],
                            "subtitle": stage_descriptions[continuation_index],
                            "visualPrompt": prompt,
                            "durationSeconds": stage_durations[continuation_index],
                        }
                    )
                )

        elapsed = 0
        for index, shot in enumerate(normalized_shots):
            start = elapsed
            elapsed += shot.durationSeconds
            scenario_lines.append(f"{index + 1}장면 {start}-{elapsed}초: {stage_descriptions[index]}")

        scenario_text = "\n".join(scenario_lines)
        title = video_director.title.strip() or mode_copy["video_title"]
        if mode_copy["title"] not in title:
            title = f"{mode_copy['title']} {title}".strip()
        return video_director.model_copy(
            update={
                "title": title,
                "concept": video_director.concept.strip() or mode_copy["video_concept"],
                "visualStyle": self._sanitize_visual_prompt(video_director.visualStyle),
                "mixDirection": (
                    video_director.mixDirection.strip()
                    or mode_copy["video_mix"]
                ),
                "scenarioText": scenario_text,
                "soraPrompt": video_director.soraPrompt.strip(),
                "targetDurationSeconds": 24,
                "shots": normalized_shots,
            }
        )

    def _sanitize_visual_prompt(self, prompt: str) -> str:
        normalized = " ".join(prompt.split()).strip()
        for pattern in PHOTO_STYLE_PATTERNS:
            normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s*,\s*,+", ", ", normalized)
        normalized = re.sub(r",\s*\.", ".", normalized)
        normalized = re.sub(r"\s+\.\s+", ". ", normalized)
        normalized = re.sub(r"(?:^|[,\s.])아님(?:$|[,\s.])", " ", normalized)
        normalized = re.sub(r"(?:^|[,\s.])없음(?:$|[,\s.])", " ", normalized)
        normalized = re.sub(r"(^|,\s*)없이\s+", r"\1", normalized)
        normalized = re.sub(r"\s*,\s*,+", ", ", normalized)
        normalized = re.sub(r",\s*\.", ".", normalized)
        normalized = re.sub(r"\s+\.\s+", ". ", normalized)
        normalized = re.sub(r"\s{2,}", " ", normalized)
        normalized = normalized.strip(" .,")
        lowered = normalized.lower()
        if "science picture-book illustration" not in lowered:
            normalized = f"{ILLUSTRATION_STYLE_CLAUSE}. {normalized}" if normalized else ILLUSTRATION_STYLE_CLAUSE
        if "no photorealism" not in normalized.lower():
            normalized = f"{normalized}. No photorealism, no live-action, no camera-photo style"
        return normalized

    def _normalize_narration(
        self,
        narration,
        summary: str,
        explanation: str,
        independent_variable: str,
        dependent_variable: str,
    ):
        script = self._fit_narration_script(
            " ".join(narration.script.split()),
            summary,
            explanation,
            independent_variable,
            dependent_variable,
        )
        return narration.model_copy(update={"script": script})

    def _fit_narration_script(
        self,
        original_script: str,
        summary: str,
        explanation: str,
        independent_variable: str,
        dependent_variable: str,
    ) -> str:
        prepared = self._trim_narration_script(original_script)
        original_sentence_count = len(self._split_sentences(original_script))
        is_overlong = len(" ".join(original_script.split())) > NARRATION_MAX_CHARS or original_sentence_count > NARRATION_MAX_SENTENCES
        mentions_variables = (
            independent_variable in prepared and dependent_variable in prepared
        ) if independent_variable and dependent_variable else True
        if prepared and not is_overlong and mentions_variables:
            return prepared

        rebuilt = self._build_compact_narration(
            summary,
            explanation,
            independent_variable,
            dependent_variable,
        )
        return self._trim_narration_script(rebuilt)

    def _build_compact_narration(
        self,
        summary: str,
        explanation: str,
        independent_variable: str,
        dependent_variable: str,
    ) -> str:
        summary_line = self._clip_sentence(summary, 56)
        explanation_line = self._clip_sentence(explanation, 70)
        variable_line = self._clip_sentence(
            f"이제 {independent_variable}를 바꾸고 {dependent_variable}가 어떻게 달라지는지 본다.",
            58,
        )
        close_line = "두 결과를 나란히 비교하고 오늘의 결론을 짧게 적는다."
        script = " ".join(
            line for line in [summary_line, explanation_line, variable_line, close_line] if line
        )
        return script.strip()

    def _trim_narration_script(self, script: str) -> str:
        sentences = self._split_sentences(script)
        kept: list[str] = []
        current_length = 0
        for sentence in sentences:
            cleaned = self._ensure_sentence_period(self._clip_sentence(sentence, 72))
            if not cleaned:
                continue
            projected = current_length + len(cleaned) + (1 if kept else 0)
            if kept and (len(kept) >= NARRATION_MAX_SENTENCES or projected > NARRATION_MAX_CHARS):
                break
            kept.append(cleaned)
            current_length = projected

        if not kept:
            return ""
        trimmed = " ".join(kept).strip()
        if len(trimmed) > NARRATION_MAX_CHARS:
            trimmed = self._clip_sentence(trimmed, NARRATION_MAX_CHARS)
        return self._ensure_sentence_period(trimmed)

    def _split_sentences(self, text: str) -> list[str]:
        collapsed = " ".join(text.split())
        if not collapsed:
            return []
        pieces = re.split(r"(?<=[.!?])\s+|(?<=[다요죠니다])\s+", collapsed)
        return [piece.strip() for piece in pieces if piece.strip()]

    def _clip_sentence(self, text: str, limit: int) -> str:
        compact = " ".join(text.split()).strip(" .")
        if len(compact) <= limit:
            return compact
        clipped = compact[:limit].rstrip(" ,")
        last_break = max(clipped.rfind("."), clipped.rfind(","), clipped.rfind(" "), clipped.rfind("·"))
        if last_break >= max(18, limit // 2):
            clipped = clipped[:last_break].rstrip(" ,.")
        return clipped

    def _ensure_sentence_period(self, text: str) -> str:
        normalized = text.strip()
        if not normalized:
            return ""
        if normalized[-1] in ".!?":
            return normalized
        return f"{normalized}."

    def generate_scene_image(self, prompt: str) -> bytes | None:
        if not self.client or not prompt.strip():
            return None
        try:
            response = self.client.images.generate(
                model=self.settings.image_model,
                prompt=prompt,
                size="1024x1024",
                quality="medium",
                output_format="png",
            )
            image = response.data[0]
            encoded = getattr(image, "b64_json", None)
            if encoded:
                return base64.b64decode(encoded)

            image_url = getattr(image, "url", None)
            if image_url:
                with urlopen(image_url, timeout=30) as response_stream:
                    return response_stream.read()
        except Exception:
            return None
        return None

    def edit_scene_image(self, image_path: Path, prompt: str) -> bytes | None:
        if not self.client or not prompt.strip() or not image_path.exists():
            return None
        try:
            with image_path.open("rb") as image_file:
                response = self.client.images.edit(
                    model=self.settings.image_model,
                    image=image_file,
                    prompt=prompt,
                    input_fidelity="high",
                    size="1024x1024",
                    quality="medium",
                    output_format="png",
                )
            image = response.data[0]
            encoded = getattr(image, "b64_json", None)
            if encoded:
                return base64.b64decode(encoded)

            image_url = getattr(image, "url", None)
            if image_url:
                with urlopen(image_url, timeout=30) as response_stream:
                    return response_stream.read()
        except Exception:
            return None
        return None

    def synthesize_speech(self, script: str) -> bytes | None:
        if not script.strip():
            return None
        provider = self.active_tts_provider
        prepared_script = self._prepare_tts_script(script)
        self._last_tts_voice_label = self.active_tts_voice_label
        if provider == "elevenlabs":
            audio = self._synthesize_with_elevenlabs(prepared_script)
            if audio:
                self._last_tts_voice_label = self.settings.elevenlabs_voice_label
                return audio
            if not self.client:
                return None
            logger.warning("ElevenLabs TTS failed, falling back to OpenAI TTS.")
        if not self.client:
            return None
        try:
            response = self.client.audio.speech.create(
                model=self.settings.tts_model,
                voice=self.settings.default_voice,
                input=prepared_script,
                instructions=TTS_INSTRUCTIONS,
            )
            self._last_tts_voice_label = self.settings.default_voice
            return response.read()
        except Exception as exc:
            logger.warning("OpenAI TTS failed: %s", exc)
            return None

    def _synthesize_with_elevenlabs(self, script: str) -> bytes | None:
        if not self.settings.elevenlabs_api_key or not script.strip():
            return None

        voice_settings = {
            "stability": self.settings.elevenlabs_stability,
            "similarity_boost": self.settings.elevenlabs_similarity_boost,
            "style": self.settings.elevenlabs_style,
            "speed": self.settings.elevenlabs_speed,
            "use_speaker_boost": self.settings.elevenlabs_speaker_boost,
        }
        payload = {
            "text": script,
            "model_id": self.settings.elevenlabs_model_id,
            "language_code": self.settings.elevenlabs_language_code,
            "voice_settings": voice_settings,
            "apply_text_normalization": "auto",
        }
        endpoint = (
            f"https://api.elevenlabs.io/v1/text-to-speech/"
            f"{self.settings.elevenlabs_voice_id}?output_format={self.settings.elevenlabs_output_format}"
        )
        request = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "xi-api-key": self.settings.elevenlabs_api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=45) as response:
                return response.read()
        except HTTPError as exc:
            error_body = ""
            try:
                error_body = exc.read().decode("utf-8", errors="ignore").strip()
            except Exception:
                error_body = ""
            logger.warning(
                "ElevenLabs TTS HTTP error %s: %s",
                exc.code,
                error_body or exc.reason,
            )
            return None
        except Exception as exc:
            logger.warning("ElevenLabs TTS failed: %s", exc)
            return None

    def _prepare_tts_script(self, script: str) -> str:
        collapsed = " ".join(script.split())
        if not collapsed:
            return ""
        pieces = re.split(r"(?<=[.!?])\s+", collapsed)
        normalized = []
        for piece in pieces:
            segment = piece.strip()
            if segment:
                normalized.append(segment)
        return "\n".join(normalized)
