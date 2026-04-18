import json

from app.config import get_settings
from app.store import LocalStore


def test_load_result_backfills_legacy_scenario_text(tmp_path) -> None:
    settings = get_settings().model_copy(update={"data_dir": tmp_path})
    store = LocalStore(settings)
    entry = store.create_entry("image")

    legacy_payload = {
        "entryId": entry.id,
        "summary": "legacy summary",
        "emotions": ["호기심"],
        "scienceLens": ["관찰"],
        "questionSeeds": ["무엇을 볼까?"],
        "experimentCard": {
            "title": "legacy experiment",
            "hypothesis": "가설",
            "independentVariable": "원인",
            "dependentVariable": "결과",
            "method": "기록한다.",
            "durationDays": 1,
            "whatToWatch": "반응을 본다.",
        },
        "gameModes": [],
        "recommendedModeId": "observe",
        "videoDirector": {
            "title": "legacy video",
            "concept": "legacy concept",
            "visualStyle": "legacy style",
            "mixDirection": "legacy mix",
            "soraPrompt": "legacy prompt",
            "targetDurationSeconds": 12,
            "shots": [
                {
                    "sceneTitle": "오늘의 마음",
                    "subtitle": "친구 마음이 궁금해요",
                    "visualPrompt": "legacy shot",
                    "durationSeconds": 3,
                }
            ],
        },
        "creativeExpansion": None,
        "guardianNote": None,
        "narration": {"script": "legacy narration"},
        "sceneCards": [{"title": "오늘의 마음", "body": "legacy"}],
        "media": {"posterUrl": None, "videoModel": "sora-2-pro"},
        "analysisMode": "fallback",
    }

    store.result_json_path(entry.id).write_text(
        json.dumps(legacy_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result = store.load_result(entry.id)
    assert "오늘의 마음" in result.videoDirector.scenarioText


def test_list_entries_ignores_invalid_legacy_result(tmp_path) -> None:
    settings = get_settings().model_copy(update={"data_dir": tmp_path})
    store = LocalStore(settings)
    entry = store.create_entry("image")
    store.result_json_path(entry.id).write_text("null", encoding="utf-8")

    items = store.list_entries()
    assert len(items) == 1
    assert items[0].entryId == entry.id


def test_save_upload_uses_local_media_url_by_default(tmp_path) -> None:
    settings = get_settings().model_copy(update={"data_dir": tmp_path})
    store = LocalStore(settings)
    entry = store.create_entry("image")

    url = store.save_upload(entry.id, "note.png", b"image-bytes")

    assert url == f"/media/entries/{entry.id}/original.png"
    assert store.original_upload_path(entry.id) == store.abs_media_path(entry.id, "original.png")


def test_save_upload_uses_s3_url_when_enabled(tmp_path, monkeypatch) -> None:
    settings = get_settings().model_copy(
        update={
            "data_dir": tmp_path,
            "media_storage_backend": "s3",
            "media_s3_bucket": "demo-bucket",
            "media_s3_region": "ap-northeast-2",
            "media_s3_prefix": "hackathon-media",
        }
    )
    store = LocalStore(settings)
    entry = store.create_entry("image")
    uploads: list[tuple[str, str, str]] = []

    monkeypatch.setattr(
        store,
        "_upload_local_file",
        lambda path, key, content_type: uploads.append((path.name, key, content_type)),
    )

    url = store.save_upload(entry.id, "note.png", b"image-bytes")

    assert url == (
        f"https://demo-bucket.s3.ap-northeast-2.amazonaws.com/"
        f"hackathon-media/entries/{entry.id}/original.png"
    )
    assert uploads == [
        (
            "original.png",
            f"hackathon-media/entries/{entry.id}/original.png",
            "image/png",
        )
    ]
