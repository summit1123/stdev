from app.config import get_settings
from app.models import DiaryParseOutput, EntryStatus
from app.pipeline import AnalysisPipeline
from app.store import LocalStore


class StubAI:
    def __init__(self) -> None:
        self.last_path = None
        self.last_filename = None

    def extract_from_image(self, file_path, filename):
        self.last_path = file_path
        self.last_filename = filename
        return DiaryParseOutput(
            transcription="오늘 비를 봤다.",
            normalizedText="오늘 비를 봤다.",
            summaryHint="비 관찰",
        )

    def transcribe_audio(self, file_path, filename):
        raise AssertionError("voice parsing is not expected in this test")


def test_parse_upload_uses_local_file_path_even_with_s3_url(tmp_path, monkeypatch) -> None:
    settings = get_settings().model_copy(
        update={
            "data_dir": tmp_path,
            "media_storage_backend": "s3",
            "media_s3_bucket": "demo-bucket",
            "media_s3_region": "ap-northeast-2",
        }
    )
    store = LocalStore(settings)
    entry = store.create_entry("image")

    monkeypatch.setattr(store, "_upload_local_file", lambda path, key, content_type: None)

    entry.originalFilename = "note.png"
    entry.originalFileUrl = store.save_upload(entry.id, entry.originalFilename, b"image-bytes")
    store.save_entry(entry)

    ai = StubAI()
    pipeline = AnalysisPipeline(store, ai, media=None)  # type: ignore[arg-type]

    updated = pipeline.parse_upload(entry)

    assert updated.status == EntryStatus.TEXT_READY
    assert ai.last_filename == "note.png"
    assert ai.last_path == store.abs_media_path(entry.id, "original.png")
