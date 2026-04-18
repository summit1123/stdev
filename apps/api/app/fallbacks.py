from __future__ import annotations

from pathlib import Path

from app.models import (
    CreativeExpansion,
    DiaryParseOutput,
    EntryMedia,
    EntryResult,
    ExperimentCard,
    GameModeCard,
    Narration,
    SceneCard,
    SceneVisual,
    ScienceGame,
    ScienceQuiz,
    ScientificInterpretation,
    VideoDirector,
    VideoShot,
)


SAMPLE_TEXT_BY_STEM = {
    "sample-popular-friend": "나는 인기 많은 친구가 되고 싶다. 친구들이 어떤 행동을 좋아하는지 궁금하다.",
    "sample-rainy-day": "오늘은 비가 와서 운동장에 나가지 못했다. 날씨가 내 기분을 바꾸는 것 같았다.",
    "sample-mosquito-night": "어젯밤 모기 때문에 잠을 설쳤다. 왜 어떤 날에는 모기가 더 많을까 궁금했다.",
}

MODE_CARD_COPY = {
    "observe": GameModeCard(
        id="observe",
        title="탐정 모드",
        hook='일기 속 어떤 장면에서든 "왜 그랬을까?"를 질문 삼아 과학 원리를 추리하는 모드',
        mission='일기의 행동, 감각, 변화 중 하나를 골라 원인을 추적하는 단서에서 추리로 이어지는 흐름으로 구성합니다.',
        reward="시나리오와 이미지, 영상도 단서와 원인 추리 흐름으로 이어집니다.",
    ),
    "experiment": GameModeCard(
        id="experiment",
        title="발명가 모드",
        hook='일기 속 어떤 장면에서든 숨어있는 과학 원리를 꺼내 새로운 아이디어로 연결하는 모드',
        mission='일기의 사물, 행동, 현상 중 하나를 골라 원리를 설명한 뒤 "이걸 응용하면?"으로 이어지는 흐름으로 구성합니다.',
        reward="시나리오와 이미지, 영상도 원리 설명 뒤 응용 아이디어로 확장합니다.",
    ),
    "imagine": GameModeCard(
        id="imagine",
        title="탐험가 모드",
        hook='일기 속 어떤 순간이든 처음 발견한 것처럼 낯설게 바라보며 과학을 찾아내는 모드',
        mission='일기에서 당연하게 지나친 장면을 골라 "이게 왜 당연한 걸까?"라는 탐험 질문으로 바꿔 구성합니다.',
        reward="시나리오와 이미지, 영상도 낯설게 다시 보는 탐험 흐름으로 이어집니다.",
    ),
}


def _first_sentence(text: str) -> str:
    cleaned = " ".join(text.replace("\n", " ").split())
    if not cleaned:
        return "오늘 있었던 일을 적어 준 기록"
    parts = [part.strip() for part in cleaned.split(".") if part.strip()]
    if parts:
        return parts[0]
    return cleaned[:80]


def infer_sample_text(filename: str) -> str | None:
    return SAMPLE_TEXT_BY_STEM.get(Path(filename).stem)


def fallback_parse_from_text(text: str, filename: str | None = None):
    seeded = infer_sample_text(filename or "")
    normalized = seeded or " ".join(text.replace("\n", " ").split())
    if not normalized:
        normalized = "오늘 있었던 일을 적고, 내일 어떤 점을 관찰해볼지 떠올려 보자."
    return DiaryParseOutput(
        transcription=normalized,
        normalizedText=normalized,
        summaryHint=_first_sentence(normalized),
        emotionTags=infer_emotions(normalized),
        scienceBridgeHint=infer_science_lens(normalized),
        parseWarnings=[]
        if seeded
        else ["자동 추출이 완벽하지 않을 수 있어요. 필요한 부분을 직접 고쳐 주세요."],
    )


def infer_emotions(text: str) -> list[str]:
    mapping = [
        ("친구", "관계에 대한 호기심"),
        ("욕", "낯선 장면에 대한 의문"),
        ("비", "날씨에 대한 감각"),
        ("모기", "불편함"),
        ("궁금", "호기심"),
        ("걱정", "걱정"),
        ("무섭", "긴장"),
        ("좋", "기대"),
    ]
    found: list[str] = []
    for needle, emotion in mapping:
        if needle in text and emotion not in found:
            found.append(emotion)
    return found or ["호기심"]


def infer_topic(text: str) -> str:
    rules = [
        (("친구", "인기", "도와", "같이", "놀", "욕", "막지우"), "social"),
        (("비", "날씨", "바람", "구름", "하늘"), "weather"),
        (("모기", "개미", "고양이", "강아지", "곤충"), "animals"),
        (("공부", "시험", "숙제", "학교"), "study"),
        (("엄마", "아빠", "가족", "동생", "오빠"), "family"),
    ]
    for needles, topic in rules:
        if any(needle in text for needle in needles):
            return topic
    return "general"


def infer_science_lens(text: str) -> list[str]:
    topic = infer_topic(text)
    mapping = {
        "social": ["행동의 맥락 보기", "반응 신호 기록", "말과 표정 비교"],
        "weather": ["날씨 조건 기록", "기분과 활동 비교", "시간대 관찰"],
        "animals": ["출현 패턴 관찰", "조건 비교", "횟수 기록"],
        "study": ["집중 시간 측정", "습관 비교", "전후 변화 기록"],
        "family": ["말투와 반응 비교", "대화 분위기 관찰", "반복 신호 찾기"],
        "general": ["장면 관찰", "조건 비교", "반복 기록"],
    }
    return mapping[topic]


def fallback_result(
    entry_id: str,
    text: str,
    poster_url: str | None = None,
    preferred_mode_id: str = "observe",
) -> EntryResult:
    cleaned = " ".join(text.replace("\n", " ").split())
    if not cleaned:
        cleaned = "오늘 있었던 일을 과학자의 눈으로 다시 바라보자."

    topic = infer_topic(cleaned)
    emotions = infer_emotions(cleaned)
    science_lens = infer_science_lens(cleaned)
    summary = build_summary(cleaned, topic)
    questions = build_questions(topic)
    experiment = build_experiment(topic)
    scientific_interpretation = build_scientific_interpretation(topic, cleaned)
    recommended_mode_id = choose_mode(topic, preferred_mode_id)
    scene_visual = build_scene_visual(topic, cleaned, recommended_mode_id)
    science_game = build_science_game(topic, recommended_mode_id)
    science_quiz = build_science_quiz(topic)
    creative = build_creative(topic)
    narration_script = build_narration(topic, questions[0], experiment)
    game_modes = build_game_modes(topic)
    video_director = build_video_director(
        summary,
        questions,
        experiment,
        scientific_interpretation,
        recommended_mode_id,
    )
    media = EntryMedia(posterUrl=poster_url, videoModel="storyboard-mix")

    return EntryResult(
        entryId=entry_id,
        summary=summary,
        emotions=emotions,
        scienceLens=science_lens,
        questionSeeds=questions,
        experimentCard=experiment,
        scientificInterpretation=scientific_interpretation,
        sceneVisual=scene_visual,
        scienceGame=science_game,
        scienceQuiz=science_quiz,
        gameModes=game_modes,
        recommendedModeId=recommended_mode_id,
        videoDirector=video_director,
        creativeExpansion=creative,
        guardianNote="아이의 느낌을 판정하지 말고, 실제로 본 장면과 반응을 다시 말하게 도와주세요.",
        narration=Narration(script=narration_script),
        sceneCards=[
            SceneCard(title="오늘의 마음", body=summary),
            SceneCard(title="질문 씨앗", body=questions[0]),
            SceneCard(title="미니 실험", body=experiment.method),
            SceneCard(title="AI 해설", body=scientific_interpretation.explanation),
        ],
        media=media,
        analysisMode="fallback",
    )


def build_summary(text: str, topic: str) -> str:
    first_sentence = _first_sentence(text)
    summaries = {
        "social": "친한 사이의 말도 왜 다르게 느껴지는지 궁금해한 기록이야.",
        "weather": "날씨 변화가 하루의 기분과 행동에 어떤 영향을 주는지 떠올리게 하는 기록이야.",
        "animals": "작은 생물이 언제 더 많이 보이는지 관찰로 이어질 수 있는 기록이야.",
        "study": "공부 습관과 집중이 어떻게 달라지는지 살펴볼 수 있는 기록이야.",
        "family": "가족 사이의 말과 반응을 비교해볼 수 있는 기록이야.",
        "general": "오늘의 장면을 질문과 실험으로 바꾸기 좋은 기록이야.",
    }
    return f"{first_sentence}. {summaries[topic]}"


def build_questions(topic: str) -> list[str]:
    mapping = {
        "social": [
            "친한 장난과 불편한 말은 표정, 웃음, 대화 지속에서 어떤 차이가 있을까?",
            "같은 말도 친한 정도나 상황에 따라 반응이 달라질까?",
            "예의 있는 말과 편한 말은 관계 신호에 어떤 차이를 만들까?",
        ],
        "weather": [
            "비가 오는 날과 맑은 날의 기분 차이는 어떻게 다를까?",
            "날씨가 바뀌면 내가 하는 활동도 달라질까?",
            "하늘의 색과 바람 세기는 서로 관련이 있을까?",
        ],
        "animals": [
            "곤충은 어떤 시간과 장소에서 더 자주 보일까?",
            "빛과 온도는 곤충이 나타나는 횟수에 영향을 줄까?",
            "며칠 동안 같은 패턴이 반복될까?",
        ],
        "study": [
            "집중이 잘 되는 시간대에는 어떤 공통점이 있을까?",
            "공부 전에 준비 행동을 하면 집중 시간이 길어질까?",
            "짧은 쉬는 시간은 기억에 어떤 차이를 만들까?",
        ],
        "family": [
            "같은 부탁도 말하는 방식에 따라 반응이 달라질까?",
            "부드러운 말투는 대화 시간을 더 길게 만들까?",
            "가족이 편안해 보이는 순간에는 어떤 신호가 있을까?",
        ],
        "general": [
            "오늘 있었던 일에서 가장 또렷한 변화는 무엇일까?",
            "그 변화를 만든 조건은 무엇이었을까?",
            "내일 다시 보면 어떤 점을 비교할 수 있을까?",
        ],
    }
    return mapping[topic]


def build_experiment(topic: str) -> ExperimentCard:
    mapping = {
        "social": ExperimentCard(
            title="말투와 반응 신호 비교",
            hypothesis="예의 있는 말과 편한 말은 상대의 표정과 대답 방식에 다른 신호를 만들 수 있다.",
            independentVariable="말투의 종류",
            dependentVariable="표정, 대답 속도, 대화 지속 여부",
            method="3일 동안 부탁이나 인사를 할 때 정중한 말과 편한 말을 써 보고, 웃음, 고개 끄덕임, 대답 길이만 기록한다. 불편한 말이나 공격적인 말은 사용하지 않는다.",
            durationDays=3,
            whatToWatch="어떤 말투에서 상대가 더 편안해 보였는지 비교한다.",
        ),
        "weather": ExperimentCard(
            title="날씨와 기분 변화 기록",
            hypothesis="날씨가 흐리거나 비가 오면 내가 선택하는 활동과 기분도 달라질 수 있다.",
            independentVariable="날씨 상태",
            dependentVariable="기분 점수와 활동 선택",
            method="3일 동안 아침과 오후의 날씨, 기분 점수, 가장 오래 한 활동을 표로 적는다.",
            durationDays=3,
            whatToWatch="날씨가 다른 날에 기분과 활동이 어떻게 달라지는지 비교한다.",
        ),
        "animals": ExperimentCard(
            title="곤충이 많이 보이는 조건 찾기",
            hypothesis="곤충은 특정 시간이나 밝기에서 더 자주 나타날 것이다.",
            independentVariable="관찰 시간 또는 밝기",
            dependentVariable="곤충을 본 횟수",
            method="같은 장소를 아침과 저녁에 3일 동안 관찰하고, 보인 횟수를 체크한다.",
            durationDays=3,
            whatToWatch="언제 더 자주 보였는지와 주변 조건을 함께 본다.",
        ),
        "study": ExperimentCard(
            title="집중 시간 비교",
            hypothesis="공부 전에 준비 행동을 하면 집중 시간이 길어질 것이다.",
            independentVariable="준비 행동 유무",
            dependentVariable="집중 시간",
            method="3일 동안 공부 시작 전 2분 준비를 한 날과 하지 않은 날의 집중 시간을 잰다.",
            durationDays=3,
            whatToWatch="준비 행동이 있을 때 집중 시간이 길어지는지 본다.",
        ),
        "family": ExperimentCard(
            title="말투와 가족 반응 비교",
            hypothesis="부드럽게 먼저 말하면 대화의 반응도 더 부드러워질 수 있다.",
            independentVariable="말 건네는 방식",
            dependentVariable="대답 속도와 표정",
            method="3일 동안 인사나 부탁을 할 때 말투를 적고, 상대의 표정과 대답을 한 줄로 기록한다.",
            durationDays=3,
            whatToWatch="어떤 말투에서 더 편안한 반응이 나오는지 본다.",
        ),
        "general": ExperimentCard(
            title="내일 다시 보기 실험",
            hypothesis="같은 장면을 다시 보면 처음엔 못 본 새로운 단서를 발견할 수 있다.",
            independentVariable="관찰 횟수",
            dependentVariable="발견한 단서 수",
            method="오늘의 장면을 떠올리고, 내일 같은 장소나 상황을 다시 보며 새로 본 점을 적는다.",
            durationDays=2,
            whatToWatch="두 번째 관찰에서 새로 발견한 점이 늘어나는지 본다.",
        ),
    }
    return mapping[topic]


def build_scientific_interpretation(topic: str, text: str) -> ScientificInterpretation:
    observation = _first_sentence(text)
    mapping = {
        "social": ScientificInterpretation(
            title="말의 뜻은 단어만이 아니라 맥락으로 읽힌다",
            observation=f"일기에서는 {observation} 장면을 떠올렸다.",
            concept="사회과학에서는 말 자체뿐 아니라 표정, 거리, 목소리, 이후 반응을 함께 본다.",
            explanation="같은 표현도 친한 장난인지 상처 주는 말인지 구분하려면 웃음이 있었는지, 상대가 편안해 보였는지, 대화가 계속 이어졌는지를 관찰해야 한다.",
            measurementIdea="표정 변화, 웃음 여부, 대답 길이, 대화가 이어진 시간",
            safetyNote="사람을 불편하게 만드는 말은 실험하지 않는다. 예의 있는 말과 편한 말만 비교한다.",
        ),
        "weather": ScientificInterpretation(
            title="날씨는 기분과 행동 선택에 영향을 줄 수 있다",
            observation=f"일기에서는 {observation} 상황을 적었다.",
            concept="환경과 행동의 관계를 보려면 같은 사람의 여러 날 기록을 비교한다.",
            explanation="날씨는 빛, 온도, 소리 같은 조건을 함께 바꾸기 때문에 활동 선택과 기분에 차이가 생길 수 있다.",
            measurementIdea="날씨 상태, 기분 점수, 활동 시간",
            safetyNote="짧고 가벼운 기록만 하고, 몸 상태가 좋지 않으면 쉬어 간다.",
        ),
        "animals": ScientificInterpretation(
            title="생물은 특정 조건에서 더 자주 나타난다",
            observation=f"일기에서는 {observation} 장면을 적었다.",
            concept="생물 관찰은 시간, 밝기, 온도처럼 바뀌는 조건을 함께 본다.",
            explanation="곤충이나 작은 생물은 환경이 바뀌면 나타나는 빈도도 달라질 수 있어서, 며칠 동안 같은 방식으로 기록하면 패턴이 보인다.",
            measurementIdea="관찰 시간, 장소, 밝기, 발견 횟수",
            safetyNote="멀리서 안전하게 보고, 만지지 않는다.",
        ),
        "study": ScientificInterpretation(
            title="집중은 준비 행동과 환경의 영향을 받을 수 있다",
            observation=f"일기에서는 {observation} 경험을 적었다.",
            concept="습관 연구에서는 시작 전 조건과 결과 시간을 함께 본다.",
            explanation="공부 전 준비 행동이 있으면 몸과 마음이 시작 신호를 더 빨리 받아들여 집중 시간이 달라질 수 있다.",
            measurementIdea="준비 행동 유무, 시작 시간, 집중 시간",
            safetyNote="무리하게 오래 하지 말고, 짧은 단위로 기록한다.",
        ),
        "family": ScientificInterpretation(
            title="말투는 관계의 분위기를 바꿀 수 있다",
            observation=f"일기에서는 {observation} 순간을 적었다.",
            concept="대화 연구에서는 단어 선택과 함께 표정, 속도, 대화 길이를 본다.",
            explanation="같은 부탁도 말하는 방식이 달라지면 상대가 받아들이는 느낌과 반응의 속도가 달라질 수 있다.",
            measurementIdea="말투, 표정, 대답 속도, 대화 길이",
            safetyNote="편안한 상황에서 짧게 기록하고, 다툼 상황은 실험으로 만들지 않는다.",
        ),
        "general": ScientificInterpretation(
            title="과학은 장면을 다시 보는 데서 시작한다",
            observation=f"일기에서는 {observation} 일을 적었다.",
            concept="과학자는 장면을 한 번 더 보고, 바뀌는 조건과 반복되는 신호를 나눈다.",
            explanation="감정으로 지나간 일도 다시 보면 비교할 수 있는 단서가 생기고, 그 단서가 질문과 실험의 출발점이 된다.",
            measurementIdea="횟수, 시간, 전후 차이",
            safetyNote="안전하고 편안한 장면만 다시 관찰한다.",
        ),
    }
    return mapping[topic]


def build_scene_visual(topic: str, text: str, recommended_mode_id: str) -> SceneVisual:
    first_line = _first_sentence(text)
    mode_copy = MODE_CARD_COPY.get(recommended_mode_id, MODE_CARD_COPY["observe"])
    mode_prompt = {
        "observe": "Show clue-like evidence, traces, timing differences, and visible cause hints in the same frame.",
        "experiment": "Show the hidden mechanism clearly and hint at a practical application or new idea in the same frame.",
        "imagine": "Make the familiar moment feel newly discovered, slightly surprising, and full of hidden rules.",
    }[recommended_mode_id]
    prompts = {
        "social": (
            "Premium Korean picture-book editorial illustration. Two Korean children in an elementary classroom or hallway "
            "are talking in a very close, familiar way. One child looks playful, the other is smiling but thinking carefully. "
            "A small science notebook and stickers suggest observation and comparison. Warm natural light, expressive faces, "
            "clear body language, premium children's publishing quality, no text, no watermark"
        ),
        "weather": (
            "Premium children's editorial illustration of a Korean child watching rainy weather from a classroom window, "
            "science notebook open, puddles, clouds, gentle light, detailed observation mood, no text, no watermark"
        ),
        "animals": (
            "Premium children's editorial illustration of a child observing insects in the evening with a notebook, "
            "safe distance, tiny flashlight glow, clear environment details, no text, no watermark"
        ),
        "study": (
            "Premium children's editorial illustration of a child setting up a desk before studying, timer, notebook, "
            "focused but calm atmosphere, editorial style, no text, no watermark"
        ),
        "family": (
            "Premium children's editorial illustration of a warm home conversation scene between siblings or family, "
            "gentle expressions, observable reactions, science notebook nearby, no text, no watermark"
        ),
        "general": (
            "Premium children's editorial illustration of a diary moment turning into a science observation scene, "
            "warm light, notebook, stickers, clear gestures, no text, no watermark"
        ),
    }
    return SceneVisual(
        title=mode_copy.title,
        prompt=f"{prompts[topic]}. {mode_prompt}",
        caption=f"{first_line}. {mode_copy.mission}",
        imageUrl=None,
    )


def build_science_game(topic: str, recommended_mode_id: str) -> ScienceGame:
    mapping = {
        "social": ScienceGame(
            title="반응 신호 탐정",
            premise="말보다 먼저 표정과 반응 신호를 읽는 관찰 게임",
            goal="편안한 신호와 불편한 신호를 근거와 함께 구분하기",
            howToPlay=[
                "상황 카드 한 장을 고른다.",
                "표정, 거리, 대답 길이 단서 세 개를 찾는다.",
                "왜 그 신호가 편안함 또는 불편함을 말해 주는지 설명한다.",
            ],
            winCondition="세 턴 연속으로 단서와 이유를 함께 말하면 성공",
            aiGuide="AI는 단어보다 반응 신호가 왜 중요한지 한 줄씩 설명한다.",
        ),
        "weather": ScienceGame(
            title="구름 패턴 레이스",
            premise="날씨 신호를 모아 다음 장면을 예측하는 게임",
            goal="관찰한 하늘 단서로 활동 변화를 설명하기",
            howToPlay=[
                "하늘 카드와 기분 카드를 한 장씩 놓는다.",
                "어울리는 활동 카드를 연결한다.",
                "왜 그렇게 연결했는지 관찰 근거를 말한다.",
            ],
            winCondition="세 장면을 연속으로 근거 있게 연결하면 성공",
            aiGuide="AI는 날씨와 행동을 연결한 이유를 짧게 짚어 준다.",
        ),
        "animals": ScienceGame(
            title="곤충 출현 지도",
            premise="시간과 장소 단서로 곤충이 나타날 지점을 찾는 게임",
            goal="조건과 출현 횟수의 관계를 추리하기",
            howToPlay=[
                "시간 카드와 밝기 카드를 고른다.",
                "곤충이 가장 많이 보일 곳을 고른다.",
                "근거 단서를 한 문장으로 말한다.",
            ],
            winCondition="세 번 연속 관찰 근거를 맞추면 성공",
            aiGuide="AI는 어떤 조건이 중요한지 다시 정리해 준다.",
        ),
        "study": ScienceGame(
            title="집중 스타트 보드",
            premise="집중을 돕는 준비 단서를 모아 출발선을 만드는 게임",
            goal="집중 시간이 늘어나는 조건을 찾기",
            howToPlay=[
                "준비 행동 카드 두 장을 고른다.",
                "집중 시간을 예상한다.",
                "실제 기록과 비교해 다음 전략을 바꾼다.",
            ],
            winCondition="세 번의 비교 후 가장 잘 맞는 준비 조합을 찾으면 성공",
            aiGuide="AI는 준비 행동과 집중 시간의 연결을 설명한다.",
        ),
        "family": ScienceGame(
            title="말투 온도계",
            premise="같은 부탁을 다른 말투로 관찰하는 게임",
            goal="편안한 대화 신호를 찾기",
            howToPlay=[
                "상황 카드를 읽는다.",
                "말투 카드 두 장을 비교한다.",
                "예상 반응과 실제 반응을 나란히 적는다.",
            ],
            winCondition="세 상황에서 가장 편안한 말투를 찾으면 성공",
            aiGuide="AI는 반응 신호를 보고 왜 그런지 설명한다.",
        ),
        "general": ScienceGame(
            title="단서 수집 미션",
            premise="오늘의 장면에서 보이는 단서를 모으는 게임",
            goal="단서로 질문을 만드는 습관 익히기",
            howToPlay=[
                "장면 하나를 고른다.",
                "보이는 단서 세 개를 적는다.",
                "그 단서로 질문 하나를 만든다.",
            ],
            winCondition="세 턴 동안 근거 있는 질문을 만들면 성공",
            aiGuide="AI는 단서가 왜 질문으로 이어지는지 설명한다.",
        ),
    }
    base = mapping[topic]
    if recommended_mode_id == "experiment":
        return base.model_copy(
            update={
                "title": f"발명가 모드: {base.title}",
                "premise": "장면 속 원리를 꺼내 새 아이디어로 바꾸는 발명가 게임",
                "goal": "원리를 설명한 뒤 어디에 응용할지 한 가지 아이디어로 연결하기",
                "aiGuide": 'AI는 "이걸 응용하면?" 질문으로 다음 아이디어를 한 줄 던져 준다.',
            }
        )
    if recommended_mode_id == "imagine":
        return base.model_copy(
            update={
                "title": f"탐험가 모드: {base.title}",
                "premise": "당연한 장면을 낯설게 다시 보며 숨은 규칙을 찾는 탐험 게임",
                "goal": '익숙한 장면을 "이게 왜 당연한 걸까?" 질문으로 바꾸기',
                "aiGuide": 'AI는 익숙한 장면을 낯설게 볼 수 있게 새로운 탐험 질문을 하나 더 붙여 준다.',
            }
        )
    return base.model_copy(
        update={
            "title": f"탐정 모드: {base.title}",
            "premise": "행동, 감각, 변화 단서를 모아 원인을 추리하는 탐정 게임",
            "goal": '단서를 따라 "왜 그랬을까?"에 가장 가까운 설명을 고르기',
            "aiGuide": 'AI는 어떤 단서가 가장 결정적이었는지 짚으며 추리 흐름을 정리해 준다.',
        }
    )


def build_science_quiz(topic: str) -> ScienceQuiz:
    mapping = {
        "social": ScienceQuiz(
            title="관계 신호 퀴즈",
            question="친한 장난인지 불편한 말인지 구분할 때 먼저 봐야 할 단서는 무엇일까?",
            options=[
                "표정과 대화가 계속 이어지는지 보기",
                "내가 싫은 단어인지 바로 점수 매기기",
                "누가 더 인기 있는지 추측하기",
            ],
            answerIndex=0,
            explanation="같은 말도 표정, 웃음, 대화 지속 여부를 함께 보면 훨씬 정확하게 읽을 수 있다.",
        ),
        "weather": ScienceQuiz(
            title="날씨 단서 퀴즈",
            question="날씨가 기분에 영향을 주는지 보려면 무엇을 함께 적어야 할까?",
            options=[
                "하늘 상태와 내가 한 활동",
                "좋아하는 색깔",
                "친구 이름 점수",
            ],
            answerIndex=0,
            explanation="날씨와 행동을 같이 기록해야 둘 사이의 변화를 비교할 수 있다.",
        ),
        "animals": ScienceQuiz(
            title="출현 패턴 퀴즈",
            question="곤충이 언제 많이 보이는지 알려면 어떤 비교가 중요할까?",
            options=[
                "시간대와 밝기 비교",
                "기분 점수만 적기",
                "한 번만 보고 결정하기",
            ],
            answerIndex=0,
            explanation="생물 관찰은 시간과 환경 조건을 함께 비교해야 패턴이 보인다.",
        ),
        "study": ScienceQuiz(
            title="집중 실험 퀴즈",
            question="집중 시간이 달라지는 이유를 보려면 무엇을 비교해야 할까?",
            options=[
                "준비 행동이 있었는지와 집중 시간",
                "오늘 먹은 간식 이름만 적기",
                "공부를 잘했는지 느낌만 적기",
            ],
            answerIndex=0,
            explanation="준비 행동과 결과 시간을 같이 적어야 정말 차이가 있는지 볼 수 있다.",
        ),
        "family": ScienceQuiz(
            title="말투 온도 퀴즈",
            question="같은 부탁이라도 반응이 달라지는지 보려면 무엇을 먼저 기록해야 할까?",
            options=[
                "말투와 상대 반응",
                "누가 더 강한 사람인지",
                "마음속 의도 추측하기",
            ],
            answerIndex=0,
            explanation="대화 연구에서는 단어보다 말투, 표정, 대답 속도 같은 관찰 가능한 단서를 먼저 본다.",
        ),
        "general": ScienceQuiz(
            title="관찰 시작 퀴즈",
            question="오늘의 장면을 과학으로 바꾸려면 먼저 무엇을 해야 할까?",
            options=[
                "반복해서 보이는 단서를 적기",
                "정답을 바로 정하기",
                "기분만 한 단어로 끝내기",
            ],
            answerIndex=0,
            explanation="과학은 먼저 보이는 단서를 적고, 그다음 비교 질문을 만드는 데서 시작한다.",
        ),
    }
    return mapping[topic]


def build_creative(topic: str) -> CreativeExpansion:
    mapping = {
        "social": CreativeExpansion(
            type="alternate_world",
            text="우주 학교에서는 장난과 배려를 어떤 신호로 구분할까?",
        ),
        "weather": CreativeExpansion(
            type="story",
            text="구름 연구원이 되어 하늘의 단서를 모은다면 무엇부터 기록할까?",
        ),
        "animals": CreativeExpansion(
            type="alternate_world",
            text="개미 도시의 과학자는 곤충이 몰리는 시간을 어떻게 지도에 남길까?",
        ),
        "study": CreativeExpansion(
            type="character",
            text="집중 탐정이라면 시작 전 어떤 준비 신호를 가장 먼저 확인할까?",
        ),
        "family": CreativeExpansion(
            type="story",
            text="말의 온도를 재는 실험실이 있다면 어떤 단어보다 어떤 표정을 먼저 기록할까?",
        ),
        "general": CreativeExpansion(
            type="story",
            text="오늘의 장면을 다시 관찰하는 탐정이 되어 작은 단서를 모아 보자.",
        ),
    }
    return mapping[topic]


def build_narration(topic: str, first_question: str, experiment: ExperimentCard) -> str:
    if topic == "social":
        return (
            "같은 말도 상황과 표정에 따라 다르게 들릴까? "
            "과학자는 반응 신호를 함께 봐. "
            f"내일은 {experiment.title}으로 그 차이를 기록해 보자."
        )
    return (
        f"오늘의 질문은 {first_question} "
        "과학자는 눈에 보이는 단서를 먼저 기록해. "
        f"내일은 {experiment.title}으로 확인해 보자."
    )


def choose_mode(topic: str, preferred_mode_id: str) -> str:
    if preferred_mode_id in {"observe", "experiment", "imagine"}:
        return preferred_mode_id
    default_by_topic = {
        "social": "observe",
        "weather": "experiment",
        "animals": "observe",
        "study": "experiment",
        "family": "observe",
        "general": "imagine",
    }
    return default_by_topic[topic]


def build_game_modes(topic: str) -> list[GameModeCard]:
    return [MODE_CARD_COPY["observe"], MODE_CARD_COPY["experiment"], MODE_CARD_COPY["imagine"]]


def build_video_director(
    summary: str,
    questions: list[str],
    experiment: ExperimentCard,
    scientific_interpretation: ScientificInterpretation,
    recommended_mode_id: str,
) -> VideoDirector:
    mode_copy = MODE_CARD_COPY.get(recommended_mode_id, MODE_CARD_COPY["observe"])
    mode_line = {
        "observe": "detective-style clue tracing rhythm",
        "experiment": "inventor-style mechanism to application rhythm",
        "imagine": "explorer-style rediscovery rhythm",
    }[recommended_mode_id]
    shots = [
        VideoShot(
            sceneTitle="일기 장면",
            subtitle=summary,
            visualPrompt=(
                "Premium Korean children's picture-book frame. Show the exact diary moment as a cinematic still, "
                "with clear facial expression, body direction, place clues, and one strong emotional situation. "
                "Feels like a real illustrated scene from a high-end science storybook, no text, no watermark."
            ),
        ),
        VideoShot(
            sceneTitle="과학 해석",
            subtitle=scientific_interpretation.concept,
            visualPrompt=(
                "Science explainer frame for children. The same scene is re-read through observation: arrows, icons, "
                "reaction cues, distance, timing, expression, and cause-effect clues are visually separated in a clean "
                "editorial illustration style. Premium educational design, no literal text, no watermark."
            ),
        ),
        VideoShot(
            sceneTitle="퀴즈와 실험",
            subtitle=experiment.title,
            visualPrompt=(
                "Interactive science game frame. A Korean child chooses between quiz cards, tokens, stickers, or simple "
                "observation choices, then starts a tiny safe experiment. Feels playful but intelligent, like a premium "
                "edtech game screen turned into an illustration. No text, no watermark."
            ),
        ),
        VideoShot(
            sceneTitle="내일의 미션",
            subtitle=experiment.whatToWatch,
            visualPrompt=(
                "Mission loop ending frame. The child returns the next day, writes a short observation note, and compares "
                "today versus tomorrow using visible evidence. Feels hopeful, scientific, and complete. No text, no watermark."
            ),
        ),
    ]
    sora_prompt = "\n".join(
        [
            "Use case: educational science interpretation video",
            "Primary request: create a premium 12 second child-safe explainer based on a diary entry",
            f"Rhythm: {mode_line}",
            "Structure: diary scene, scientific explanation overlay, playful observation game, next-day mission",
            "Visual world: premium Korean picture-book illustration mixed with elegant science explainer motion",
            "Subject: child-safe illustrated children, visible evidence cues, quiz-like game pieces, notebooks, observation icons, subtle classroom or home props",
            "Camera: cinematic close-ups for emotion, then clean explainer transitions for evidence and mission",
            "Lighting: bright natural daylight with warm highlights",
            "Color palette: charcoal ink, coral, butter yellow, jade green, sky blue",
            "Style: polished designer-made motion piece, not toy-like, not generic AI montage, not slideshow feeling",
            "Timing: 0-3s diary scene, 3-6s science explanation, 6-9s quiz or game-like experiment, 9-12s return mission",
            "Constraints: under-18 safe, no copyrighted characters, no visible text blocks, no watermark",
        ]
    )
    scenario_text = "\n".join(
        [
            (
                f"1장면 0-3초: 일기 속 장면을 그대로 꺼내고, 가장 먼저 보이는 단서를 붙잡는다. {summary}"
                if recommended_mode_id == "observe"
                else (
                    f"1장면 0-3초: 일기 장면 속에 숨어 있던 원리를 꺼내 발명의 재료처럼 바라본다. {summary}"
                    if recommended_mode_id == "experiment"
                    else f"1장면 0-3초: 익숙한 장면을 처음 본 것처럼 낯설게 멈춰 세운다. {summary}"
                )
            ),
            (
                f'2장면 3-6초: "왜 그랬을까?"를 묻고 원인 단서를 나눠 본다. {questions[0]}'
                if recommended_mode_id == "observe"
                else (
                    f'2장면 3-6초: "이걸 응용하면?"을 묻고 핵심 원리를 골라 낸다. {questions[0]}'
                    if recommended_mode_id == "experiment"
                    else f'2장면 3-6초: "이게 왜 당연한 걸까?"를 묻고 숨은 규칙을 찾는다. {questions[0]}'
                )
            ),
            (
                f"3장면 6-9초: 단서 추리 게임과 기록 실험이 시작된다. {experiment.title}"
                if recommended_mode_id == "observe"
                else (
                    f"3장면 6-9초: 원리를 작은 아이디어와 응용 장치로 바꿔 본다. {experiment.title}"
                    if recommended_mode_id == "experiment"
                    else f"3장면 6-9초: 낯설게 다시 본 장면을 탐험 질문과 실험으로 잇는다. {experiment.title}"
                )
            ),
            (
                f"4장면 9-12초: 내일 다시 돌아와 가장 결정적인 단서를 적는다. {experiment.whatToWatch}"
                if recommended_mode_id == "observe"
                else (
                    f"4장면 9-12초: 내일 다시 돌아와 응용 아이디어가 실제로 맞는지 기록한다. {experiment.whatToWatch}"
                    if recommended_mode_id == "experiment"
                    else f"4장면 9-12초: 내일 다시 돌아와 당연했던 장면이 정말 같은지 다시 탐험한다. {experiment.whatToWatch}"
                )
            ),
        ]
    )
    return VideoDirector(
        title=f"{mode_copy.title} 12초 필름",
        concept=f"{mode_copy.hook} {scientific_interpretation.explanation}",
        visualStyle="프리미엄 아동 에디토리얼 일러스트와 연구노트 모션의 결합",
        mixDirection=mode_copy.reward,
        scenarioText=scenario_text,
        soraPrompt=sora_prompt,
        targetDurationSeconds=12,
        shots=shots,
    )
