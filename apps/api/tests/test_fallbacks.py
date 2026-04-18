from app.fallbacks import fallback_parse_from_text, fallback_result


def test_fallback_parse_uses_sample_filename() -> None:
    parsed = fallback_parse_from_text("", "sample-popular-friend.png")
    assert "인기 많은 친구" in parsed.normalizedText
    assert parsed.parseWarnings == []


def test_fallback_result_builds_four_card_flow() -> None:
    result = fallback_result("entry_test", "나는 인기 많은 친구가 되고 싶다.", "/media/demo.png")
    assert result.summary
    assert len(result.questionSeeds) == 3
    assert len(result.gameModes) == 3
    assert result.videoDirector.targetDurationSeconds == 12
    assert result.sceneCards[0].title == "오늘의 마음"
    assert result.media.posterUrl == "/media/demo.png"
