from app.config import Settings
from app.models import CardChatMessage
from app.fallbacks import fallback_result
from app.openai_service import OpenAIService


def test_infer_science_focus_prefers_motion_for_sled_diary() -> None:
    service = OpenAIService(Settings(openai_api_key=None))

    focus = service._infer_science_focus("오늘 눈썰매를 타고 언덕 아래로 엄청 빨리 미끄러져 내려갔다.")

    assert focus.startswith("힘과 운동")


def test_normalize_science_lens_injects_focus_label() -> None:
    service = OpenAIService(Settings(openai_api_key=None))

    normalized = service._normalize_science_lens(["속도", "마찰"], "힘과 운동: 속도와 마찰을 본다.")

    assert normalized[0] == "힘과 운동"
    assert "속도" in normalized


def test_synthesize_speech_prefers_elevenlabs_when_key_exists(monkeypatch) -> None:
    service = OpenAIService(
        Settings(
            openai_api_key=None,
            elevenlabs_api_key="test-key",
            tts_provider="auto",
            elevenlabs_voice_id="voice-test",
        )
    )

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return b"fake-mp3"

    captured: dict[str, str] = {}

    def fake_urlopen(request, timeout=0):
        captured["url"] = request.full_url
        captured["api_key"] = request.headers["Xi-api-key"]
        return FakeResponse()

    monkeypatch.setattr("app.openai_service.urlopen", fake_urlopen)

    audio = service.synthesize_speech("첫 문장입니다. 두 번째 문장입니다.")

    assert audio == b"fake-mp3"
    assert "voice-test" in captured["url"]
    assert captured["api_key"] == "test-key"


def test_answer_card_chat_falls_back_with_card_specific_guidance() -> None:
    service = OpenAIService(Settings(openai_api_key=None))
    result = fallback_result("entry_demo", "오늘 학교에 늦게 도착했다.", None, "observe")

    summary_reply = service.answer_card_chat(
        "오늘 학교에 늦게 도착했다.",
        result,
        "summary",
        "왜 늦었는지 더 알고 싶어.",
        [],
    )
    experiment_reply = service.answer_card_chat(
        "오늘 학교에 늦게 도착했다.",
        result,
        "experiment",
        "어떻게 실험하면 돼?",
        [],
    )

    assert "카드" in summary_reply or "장면" in summary_reply
    assert result.experimentCard.independentVariable in experiment_reply
    assert result.experimentCard.dependentVariable in experiment_reply


def test_answer_card_chat_builds_valid_responses_api_inputs() -> None:
    service = OpenAIService(Settings(openai_api_key="test-key"))
    result = fallback_result("entry_demo", "오늘 학교에 늦게 도착했다.", None, "observe")
    captured: dict[str, object] = {}

    class FakeResponses:
        def create(self, *, model, input):
            captured["model"] = model
            captured["input"] = input
            class FakeResponse:
                output_text = "좋아요. 먼저 출발 시각부터 보면 돼요."
            return FakeResponse()

    class FakeClient:
        responses = FakeResponses()

    service.client = FakeClient()

    reply = service.answer_card_chat(
        "오늘 학교에 늦게 도착했다.",
        result,
        "summary",
        "이 장면에서 가장 먼저 봐야 할 변수는 뭐야?",
        [
            CardChatMessage(role="assistant", content="먼저 장면을 같이 정리해 볼게요."),
            CardChatMessage(role="user", content="응, 변수부터 알고 싶어."),
        ],
    )

    assert "출발 시각" in reply
    payload = captured["input"]
    assert payload[0]["role"] == "system"
    assert payload[0]["content"][0]["type"] == "input_text"
    assert payload[1]["role"] == "assistant"
    assert payload[1]["content"][0]["type"] == "output_text"
    assert payload[2]["role"] == "user"
    assert payload[2]["content"][0]["type"] == "input_text"


def test_sanitize_visual_prompt_removes_photo_style_bias() -> None:
    service = OpenAIService(Settings(openai_api_key=None))

    sanitized = service._sanitize_visual_prompt(
        "그림일기 스타일, 실제 사진 같은 구도, 실제 장면, photoreal lighting, calm scene"
    )

    lowered = sanitized.lower()
    assert "실제 사진 같은 구도" not in sanitized
    assert "실제 장면" not in sanitized
    assert "photoreal lighting" not in lowered
    assert "science picture-book illustration" in lowered
    assert "no photorealism" in lowered


def test_fit_narration_script_compacts_overlong_script() -> None:
    service = OpenAIService(Settings(openai_api_key=None))
    long_script = (
        "호수에 얼음이 얼었습니다. 얼음 조각은 바닥에 따라 멀리 가는 거리가 달라집니다. "
        "매끈한 곳은 마찰이 작아서 더 잘 미끄러집니다. 오늘의 질문은 왜 그랬을까입니다. "
        "월드컵공원 호수에서 얼음을 깨서 작은 조각으로 놀이를 했고 손과 발이 차가워졌습니다. "
        "핵심 변수는 바닥 재질과 밀어 준 힘이고 결과 지표는 이동한 거리입니다. "
        "두 결과를 나란히 비교한 뒤 오늘의 결론을 짧게 적고 내일 다시 확인합니다."
    )

    compact = service._fit_narration_script(
        long_script,
        "얼음 조각은 바닥에 따라 멀리 가는 거리가 달라집니다.",
        "매끈한 바닥은 마찰이 작아서 얼음 조각이 더 멀리 갑니다.",
        "바닥 재질",
        "이동 거리",
    )

    assert len(compact) <= 220
    assert compact.count(".") <= 5
    assert "바닥 재질" in compact
    assert "이동 거리" in compact
