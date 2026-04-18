from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class InputType(StrEnum):
    IMAGE = "image"
    VOICE = "voice"
    TEXT = "text"


class EntryStatus(StrEnum):
    CREATED = "created"
    TEXT_READY = "text_ready"
    QUEUED = "queued"
    PARSING = "parsing"
    PLANNING = "planning"
    RENDERING_IMAGE = "rendering_image"
    RENDERING_AUDIO = "rendering_audio"
    RENDERING_VIDEO = "rendering_video"
    COMPLETED = "completed"
    FAILED = "failed"


class CreateEntryRequest(BaseModel):
    inputType: InputType = InputType.IMAGE


class CreateEntryResponse(BaseModel):
    entryId: str
    status: EntryStatus


class UploadResponse(BaseModel):
    entryId: str
    status: EntryStatus
    rawText: str
    normalizedText: str
    parseWarnings: list[str] = Field(default_factory=list)
    originalFileUrl: str


class AnalyzeRequest(BaseModel):
    normalizedText: str = Field(min_length=1)
    preferredModeId: Literal["observe", "experiment", "imagine"] = "observe"


class AnalyzeResponse(BaseModel):
    entryId: str
    jobId: str
    status: EntryStatus


class ExperimentCard(BaseModel):
    title: str
    hypothesis: str
    independentVariable: str
    dependentVariable: str
    method: str
    durationDays: int
    whatToWatch: str


class CreativeExpansion(BaseModel):
    type: Literal["story", "alternate_world", "character"]
    text: str


class Narration(BaseModel):
    script: str
    audioUrl: str | None = None
    voice: str | None = None
    durationSec: float | None = None


class SceneCard(BaseModel):
    title: str
    body: str


class EntryMedia(BaseModel):
    posterUrl: str | None = None
    videoUrl: str | None = None
    videoModel: str | None = None
    thumbnailUrl: str | None = None
    soraRequestUrl: str | None = None
    soraVideoUrl: str | None = None
    storyboardUrls: list[str] = Field(default_factory=list)


class GameModeCard(BaseModel):
    id: Literal["observe", "experiment", "imagine"]
    title: str
    hook: str
    mission: str
    reward: str


class VideoShot(BaseModel):
    sceneTitle: str
    subtitle: str
    visualPrompt: str
    durationSeconds: int = 3


class VideoDirector(BaseModel):
    title: str
    concept: str
    visualStyle: str
    mixDirection: str
    scenarioText: str
    soraPrompt: str
    targetDurationSeconds: int = 24
    shots: list[VideoShot] = Field(default_factory=list)


class ScientificInterpretation(BaseModel):
    title: str
    observation: str
    concept: str
    explanation: str
    measurementIdea: str
    safetyNote: str


class SceneVisual(BaseModel):
    title: str
    prompt: str
    caption: str
    imageUrl: str | None = None


class ScienceGame(BaseModel):
    title: str
    premise: str
    goal: str
    howToPlay: list[str] = Field(default_factory=list)
    winCondition: str
    aiGuide: str


class ScienceQuiz(BaseModel):
    title: str
    question: str
    options: list[str] = Field(default_factory=list)
    answerIndex: int = 0
    explanation: str


def default_video_director() -> VideoDirector:
    return VideoDirector(
        title="24초 탐구 영상",
        concept="일기의 장면을 관찰, 비교, 기록까지 이어 주는 24초 과학 설명 영상",
        visualStyle="연구노트와 편집 다큐가 섞인 프리미엄 모션 스타일",
        mixDirection="첫 장면은 더 길게 잡아 몰입을 만들고, 뒤로 갈수록 비교와 결론으로 리듬을 조인다.",
        scenarioText=(
            "1장면 0-4초: 일기 속 장면을 크게 보여 주며 시작한다.\n"
            "2장면 4-8초: 장면을 과학자의 시선으로 다시 읽는다.\n"
            "3장면 8-11초: 가설을 세우고 관찰 포인트를 정한다.\n"
            "4장면 11-14초: 첫 기록을 시작한다.\n"
            "5장면 14-17초: 같은 장면을 다시 시험한다.\n"
            "6장면 17-20초: 조건을 바꿔 두 결과를 모은다.\n"
            "7장면 20-22초: 차이를 비교한다.\n"
            "8장면 22-24초: 오늘의 결론과 내일의 질문으로 끝낸다."
        ),
        soraPrompt="Use case: edtech explainer. Show diary scene, science explanation, experiment, comparison, and next mission in 24 seconds.",
        targetDurationSeconds=24,
        shots=[],
    )


def default_scientific_interpretation() -> ScientificInterpretation:
    return ScientificInterpretation(
        title="장면을 과학자의 눈으로 다시 보기",
        observation="일기에서 가장 크게 변하는 현상을 한 문장으로 옮긴다.",
        concept="힘, 속도, 온도, 빛, 소리, 생물의 반응처럼 원리가 보이는 단어를 고른다.",
        explanation="장면을 움직임, 에너지, 생물 반응, 날씨 변화 같은 과학 원리로 설명한다.",
        measurementIdea="거리, 시간, 횟수, 길이, 밝기, 소리 크기처럼 셀 수 있는 단서를 기록한다.",
        safetyNote="위험한 높이, 뜨거운 물건, 날카로운 도구 없이 안전한 관찰만 한다.",
    )


def default_scene_visual() -> SceneVisual:
    return SceneVisual(
        title="일기 장면 일러스트",
        prompt=(
            "Premium children's editorial illustration of a diary moment turning into a science notebook, "
            "warm light, observational details, natural expressions, no text, no watermark"
        ),
        caption="일기 장면을 한 컷으로 다시 그린다.",
        imageUrl=None,
    )


def default_science_game() -> ScienceGame:
    return ScienceGame(
        title="변수 추적 미션",
        premise="장면에서 결과를 바꾸는 조건 하나를 골라 끝까지 추적하는 게임",
        goal="어떤 조건이 결과를 바꿨는지 근거를 찾기",
        howToPlay=[
            "장면 하나를 고른다.",
            "바꿀 수 있는 조건 하나를 정한다.",
            "결과가 어떻게 달라지는지 세 번 기록한다.",
        ],
        winCondition="조건과 결과를 짝지어 설명하면 성공",
        aiGuide="AI는 어떤 변수가 핵심인지 짧게 짚어 준다.",
    )


def default_science_quiz() -> ScienceQuiz:
    return ScienceQuiz(
        title="과학 단서 퀴즈",
        question="이 장면에서 결과를 가장 크게 바꿀 수 있는 조건은 무엇일까?",
        options=[
            "측정 가능한 조건 하나",
            "그냥 느낌으로 고르기",
            "정답부터 외우기",
        ],
        answerIndex=0,
        explanation="과학자는 먼저 바뀌는 조건과 그 결과를 짝지어 본다.",
    )


class GeneratedEntryResult(BaseModel):
    summary: str
    emotions: list[str]
    scienceLens: list[str]
    questionSeeds: list[str]
    experimentCard: ExperimentCard
    scientificInterpretation: ScientificInterpretation = Field(
        default_factory=default_scientific_interpretation
    )
    sceneVisual: SceneVisual = Field(default_factory=default_scene_visual)
    scienceGame: ScienceGame = Field(default_factory=default_science_game)
    scienceQuiz: ScienceQuiz = Field(default_factory=default_science_quiz)
    gameModes: list[GameModeCard] = Field(default_factory=list)
    recommendedModeId: Literal["observe", "experiment", "imagine"] = "observe"
    videoDirector: VideoDirector = Field(default_factory=default_video_director)
    creativeExpansion: CreativeExpansion | None = None
    guardianNote: str | None = None
    narration: Narration
    sceneCards: list[SceneCard] = Field(default_factory=list)
    media: EntryMedia = Field(default_factory=EntryMedia)


class EntryResult(GeneratedEntryResult):
    entryId: str
    analysisMode: Literal["openai", "fallback"] = "fallback"
    createdAt: datetime = Field(default_factory=utc_now)


class MissionLogCreate(BaseModel):
    observationData: str = Field(min_length=1)
    reflection: str = Field(min_length=1)


class MissionLog(BaseModel):
    id: str = Field(default_factory=lambda: new_id("mission"))
    diaryEntryId: str
    observationData: str
    reflection: str
    createdAt: datetime = Field(default_factory=utc_now)


class DiaryParseOutput(BaseModel):
    transcription: str
    normalizedText: str
    summaryHint: str
    emotionTags: list[str] = Field(default_factory=list)
    scienceBridgeHint: list[str] = Field(default_factory=list)
    parseWarnings: list[str] = Field(default_factory=list)


class DiaryEntryRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("entry"))
    inputType: InputType = InputType.IMAGE
    preferredModeId: Literal["observe", "experiment", "imagine"] = "observe"
    status: EntryStatus = EntryStatus.CREATED
    originalFilename: str | None = None
    originalFileUrl: str | None = None
    rawText: str = ""
    normalizedText: str = ""
    parseWarnings: list[str] = Field(default_factory=list)
    errorMessage: str | None = None
    createdAt: datetime = Field(default_factory=utc_now)
    updatedAt: datetime = Field(default_factory=utc_now)


class EntryStatusResponse(BaseModel):
    entryId: str
    status: EntryStatus
    preferredModeId: Literal["observe", "experiment", "imagine"] = "observe"
    originalFileUrl: str | None = None
    rawText: str = ""
    normalizedText: str = ""
    parseWarnings: list[str] = Field(default_factory=list)
    errorMessage: str | None = None
    hasResult: bool = False
    missionLogCount: int = 0


class EntryListItem(BaseModel):
    entryId: str
    createdAt: datetime
    status: EntryStatus
    summary: str | None = None
    emotions: list[str] = Field(default_factory=list)
    posterUrl: str | None = None
    missionLogCount: int = 0
