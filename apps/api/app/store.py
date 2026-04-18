from __future__ import annotations

import json
from pathlib import Path

from app.config import Settings
from app.models import (
    DiaryEntryRecord,
    EntryListItem,
    EntryResult,
    EntryStatusResponse,
    MissionLog,
    new_id,
    utc_now,
)


class LocalStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.entries_dir.mkdir(parents=True, exist_ok=True)

    def create_entry(self, input_type: str) -> DiaryEntryRecord:
        entry = DiaryEntryRecord(inputType=input_type)
        self.save_entry(entry)
        return entry

    def entry_dir(self, entry_id: str) -> Path:
        directory = self.settings.entries_dir / entry_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def entry_json_path(self, entry_id: str) -> Path:
        return self.entry_dir(entry_id) / "entry.json"

    def result_json_path(self, entry_id: str) -> Path:
        return self.entry_dir(entry_id) / "result.json"

    def mission_json_path(self, entry_id: str) -> Path:
        return self.entry_dir(entry_id) / "mission_logs.json"

    def save_entry(self, entry: DiaryEntryRecord) -> DiaryEntryRecord:
        entry.updatedAt = utc_now()
        self.entry_json_path(entry.id).write_text(
            json.dumps(entry.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return entry

    def load_entry(self, entry_id: str) -> DiaryEntryRecord:
        payload = json.loads(self.entry_json_path(entry_id).read_text(encoding="utf-8"))
        return DiaryEntryRecord.model_validate(payload)

    def save_upload(self, entry_id: str, filename: str, content: bytes) -> str:
        suffix = Path(filename).suffix or ".bin"
        stored_name = f"original{suffix}"
        path = self.entry_dir(entry_id) / stored_name
        path.write_bytes(content)
        return f"/media/entries/{entry_id}/{stored_name}"

    def abs_media_path(self, entry_id: str, filename: str) -> Path:
        return self.entry_dir(entry_id) / filename

    def save_result(self, entry_id: str, result: EntryResult) -> EntryResult:
        self.result_json_path(entry_id).write_text(
            json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return result

    def load_result(self, entry_id: str) -> EntryResult:
        payload = json.loads(self.result_json_path(entry_id).read_text(encoding="utf-8"))
        payload = self._normalize_result_payload(payload)
        return EntryResult.model_validate(payload)

    def has_result(self, entry_id: str) -> bool:
        return self.result_json_path(entry_id).exists()

    def save_audio(self, entry_id: str, content: bytes, filename: str = "narration.mp3") -> str:
        path = self.entry_dir(entry_id) / filename
        path.write_bytes(content)
        return f"/media/entries/{entry_id}/{filename}"

    def save_generated_image(
        self,
        entry_id: str,
        content: bytes,
        filename: str = "scene-visual.png",
    ) -> str:
        path = self.entry_dir(entry_id) / filename
        path.write_bytes(content)
        return f"/media/entries/{entry_id}/{filename}"

    def append_mission_log(self, entry_id: str, mission_log: MissionLog) -> MissionLog:
        existing = self.list_mission_logs(entry_id)
        existing.append(mission_log)
        self.mission_json_path(entry_id).write_text(
            json.dumps([item.model_dump(mode="json") for item in existing], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return mission_log

    def list_mission_logs(self, entry_id: str) -> list[MissionLog]:
        path = self.mission_json_path(entry_id)
        if not path.exists():
            return []
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [MissionLog.model_validate(item) for item in payload]

    def list_entries(self) -> list[EntryListItem]:
        items: list[EntryListItem] = []
        for entry_file in sorted(self.settings.entries_dir.glob("*/entry.json"), reverse=True):
            payload = json.loads(entry_file.read_text(encoding="utf-8"))
            entry = DiaryEntryRecord.model_validate(payload)
            result = None
            if self.has_result(entry.id):
                try:
                    result = self.load_result(entry.id)
                except Exception:
                    result = None
            items.append(
                EntryListItem(
                    entryId=entry.id,
                    createdAt=entry.createdAt,
                    status=entry.status,
                    summary=result.summary if result else None,
                    emotions=result.emotions if result else [],
                    posterUrl=(
                        result.sceneVisual.imageUrl
                        if result and result.sceneVisual.imageUrl
                        else (result.media.posterUrl if result else entry.originalFileUrl)
                    ),
                    missionLogCount=len(self.list_mission_logs(entry.id)),
                )
            )
        return sorted(items, key=lambda item: item.createdAt, reverse=True)

    def status_response(self, entry_id: str) -> EntryStatusResponse:
        entry = self.load_entry(entry_id)
        return EntryStatusResponse(
            entryId=entry.id,
            status=entry.status,
            preferredModeId=entry.preferredModeId,
            originalFileUrl=entry.originalFileUrl,
            rawText=entry.rawText,
            normalizedText=entry.normalizedText,
            parseWarnings=entry.parseWarnings,
            errorMessage=entry.errorMessage,
            hasResult=self.has_result(entry.id),
            missionLogCount=len(self.list_mission_logs(entry.id)),
        )

    def next_job_id(self) -> str:
        return new_id("job")

    def _normalize_result_payload(self, payload: object) -> dict:
        if not isinstance(payload, dict):
            raise ValueError("result payload must be an object")

        video_director = payload.get("videoDirector")
        if isinstance(video_director, dict) and "scenarioText" not in video_director:
            shots = video_director.get("shots")
            if isinstance(shots, list) and shots:
                scenario_lines = []
                offsets = ["0-3초", "3-6초", "6-9초", "9-12초"]
                for index, shot in enumerate(shots[:4]):
                    if not isinstance(shot, dict):
                        continue
                    title = str(shot.get("sceneTitle", f"{index + 1}장면")).strip()
                    subtitle = str(shot.get("subtitle", "")).strip()
                    offset = offsets[index] if index < len(offsets) else f"{index * 3}-{(index + 1) * 3}초"
                    line = f"{title} {offset}: {subtitle}".strip()
                    scenario_lines.append(line)
                video_director["scenarioText"] = "\n".join(scenario_lines) or "시나리오를 다시 생성해 주세요."
            else:
                video_director["scenarioText"] = "시나리오를 다시 생성해 주세요."

        return payload
