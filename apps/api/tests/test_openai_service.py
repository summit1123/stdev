from app.config import Settings
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
