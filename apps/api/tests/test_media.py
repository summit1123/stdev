from app.config import Settings
from app.media import MediaComposer
from app.models import EntryResult, VideoDirector, VideoShot
from app.store import LocalStore


def make_result() -> EntryResult:
    return EntryResult.model_validate(
        {
            "entryId": "entry_demo",
            "summary": "요약",
            "emotions": [],
            "scienceLens": [],
            "questionSeeds": [],
            "experimentCard": {
                "title": "실험",
                "hypothesis": "가설",
                "independentVariable": "출발 시각",
                "dependentVariable": "도착 시간",
                "method": "두 번 기록한다.",
                "durationDays": 1,
                "whatToWatch": "차이 보기",
            },
            "scientificInterpretation": {
                "title": "해설",
                "observation": "관찰",
                "concept": "개념",
                "explanation": "설명",
                "measurementIdea": "기록",
                "safetyNote": "안전",
            },
            "sceneVisual": {"title": "장면", "prompt": "prompt", "caption": "caption"},
            "scienceGame": {
                "title": "게임",
                "premise": "premise",
                "goal": "goal",
                "howToPlay": ["one"],
                "winCondition": "win",
                "aiGuide": "guide",
            },
            "scienceQuiz": {
                "title": "퀴즈",
                "question": "question",
                "options": ["a", "b", "c"],
                "answerIndex": 0,
                "explanation": "exp",
            },
            "gameModes": [],
            "recommendedModeId": "observe",
            "videoDirector": {
                "title": "영상",
                "concept": "개념",
                "visualStyle": "style",
                "mixDirection": "mix",
                "scenarioText": "1장면 0-4초: 시작",
                "soraPrompt": "",
                "targetDurationSeconds": 24,
                "shots": [
                    {"sceneTitle": "1", "subtitle": "1", "visualPrompt": "a", "durationSeconds": 4},
                    {"sceneTitle": "2", "subtitle": "2", "visualPrompt": "b", "durationSeconds": 4},
                    {"sceneTitle": "3", "subtitle": "3", "visualPrompt": "c", "durationSeconds": 3},
                    {"sceneTitle": "4", "subtitle": "4", "visualPrompt": "d", "durationSeconds": 3},
                    {"sceneTitle": "5", "subtitle": "5", "visualPrompt": "e", "durationSeconds": 3},
                    {"sceneTitle": "6", "subtitle": "6", "visualPrompt": "f", "durationSeconds": 3},
                    {"sceneTitle": "7", "subtitle": "7", "visualPrompt": "g", "durationSeconds": 2},
                    {"sceneTitle": "8", "subtitle": "8", "visualPrompt": "h", "durationSeconds": 2},
                ],
            },
            "creativeExpansion": {"type": "story", "text": "story"},
            "guardianNote": "note",
            "narration": {"script": "script"},
            "sceneCards": [
                {"title": "a", "body": "a"},
                {"title": "b", "body": "b"},
                {"title": "c", "body": "c"},
                {"title": "d", "body": "d"},
            ],
            "media": {},
            "analysisMode": "openai",
        }
    )


def test_resolve_render_duration_prefers_longer_audio(tmp_path) -> None:
    settings = Settings(openai_api_key=None, data_dir=tmp_path)
    composer = MediaComposer(settings, LocalStore(settings))
    result = make_result()

    duration = composer._resolve_render_duration(result, 59.76)

    assert duration > 59.9


def test_scaled_shot_durations_fill_target_runtime(tmp_path) -> None:
    settings = Settings(openai_api_key=None, data_dir=tmp_path)
    composer = MediaComposer(settings, LocalStore(settings))
    result = make_result()

    scaled = composer._scaled_shot_durations(result, 60.11, 8)

    assert len(scaled) == 8
    assert round(sum(scaled), 2) == 60.11
    assert scaled[0] > 4


def test_planned_generated_shot_indices_sample_full_timeline(tmp_path) -> None:
    settings = Settings(openai_api_key=None, data_dir=tmp_path)
    composer = MediaComposer(settings, LocalStore(settings))
    result = make_result()

    indices = composer.planned_generated_shot_indices(result)

    assert indices == [0, 2, 5, 7]
