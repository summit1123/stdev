from __future__ import annotations

from pathlib import Path

from app.media import MediaComposer
from app.models import DiaryEntryRecord, EntryStatus, MissionLog
from app.openai_service import OpenAIService
from app.store import LocalStore


class AnalysisPipeline:
    def __init__(self, store: LocalStore, ai: OpenAIService, media: MediaComposer) -> None:
        self.store = store
        self.ai = ai
        self.media = media

    def parse_upload(self, entry: DiaryEntryRecord) -> DiaryEntryRecord:
        if not entry.originalFileUrl or not entry.originalFilename:
            entry.parseWarnings = ["파일이 아직 업로드되지 않았어요."]
            return self.store.save_entry(entry)

        file_path = self._absolute_file_path(entry.originalFileUrl)

        if entry.inputType == "voice":
            parsed = self.ai.transcribe_audio(file_path, entry.originalFilename)
        else:
            parsed = self.ai.extract_from_image(file_path, entry.originalFilename)

        entry.rawText = parsed.transcription
        entry.normalizedText = parsed.normalizedText
        entry.parseWarnings = parsed.parseWarnings
        entry.status = EntryStatus.TEXT_READY
        entry.errorMessage = None
        return self.store.save_entry(entry)

    def run_analysis(self, entry_id: str) -> None:
        entry = self.store.load_entry(entry_id)
        try:
            entry.status = EntryStatus.PARSING
            self.store.save_entry(entry)

            if not entry.normalizedText.strip():
                entry = self.parse_upload(entry)

            flagged, categories = self.ai.moderate_text(entry.normalizedText)
            if flagged:
                entry.parseWarnings.append(
                    f"안전 검토가 필요한 표현이 있을 수 있어요: {', '.join(categories)}"
                )
                self.store.save_entry(entry)

            entry.status = EntryStatus.PLANNING
            self.store.save_entry(entry)

            result = self.ai.generate_result(
                entry.id,
                entry.normalizedText or entry.rawText,
                poster_url=entry.originalFileUrl,
                preferred_mode_id=entry.preferredModeId,
            )
            self.store.save_result(entry.id, result)

            entry.status = EntryStatus.RENDERING_IMAGE
            self.store.save_entry(entry)

            image = self.ai.generate_scene_image(result.sceneVisual.prompt)
            if image:
                result.sceneVisual.imageUrl = self.store.save_generated_image(entry.id, image)
                self.store.save_result(entry.id, result)

            entry.status = EntryStatus.RENDERING_AUDIO
            self.store.save_entry(entry)

            audio = self.ai.synthesize_speech(result.narration.script)
            if audio:
                result.narration.audioUrl = self.store.save_audio(entry.id, audio)
                result.narration.voice = self.ai.settings.default_voice
                self.store.save_result(entry.id, result)

            entry.status = EntryStatus.RENDERING_VIDEO
            self.store.save_entry(entry)
            # Generate every story beat up front so the final video stays visual
            # from start to finish instead of falling back to text-heavy slides.
            for index, shot in enumerate(result.videoDirector.shots[:8], start=1):
                if index <= 4:
                    shot_image = self.ai.generate_scene_image(shot.visualPrompt)
                else:
                    source_path = self.store.abs_media_path(entry.id, f"generated-storyboard-{index - 1:02d}.png")
                    shot_image = self.ai.edit_scene_image(source_path, shot.visualPrompt)
                    if not shot_image:
                        shot_image = self.ai.generate_scene_image(shot.visualPrompt)
                if shot_image:
                    self.store.save_generated_image(
                        entry.id,
                        shot_image,
                        filename=f"generated-storyboard-{index:02d}.png",
                    )
            result = self.media.render(entry.id, result)

            self.store.save_result(entry.id, result)
            entry.status = EntryStatus.COMPLETED
            entry.errorMessage = None
            self.store.save_entry(entry)
        except Exception as exc:
            entry.status = EntryStatus.FAILED
            entry.errorMessage = f"분석 중 문제가 발생했어요: {exc}"
            self.store.save_entry(entry)

    def create_mission_log(self, entry_id: str, observation_data: str, reflection: str) -> MissionLog:
        mission = MissionLog(
            diaryEntryId=entry_id,
            observationData=observation_data,
            reflection=reflection,
        )
        return self.store.append_mission_log(entry_id, mission)

    def _absolute_file_path(self, media_url: str) -> Path:
        relative = media_url.removeprefix("/media/")
        return self.store.settings.media_mount_dir / relative
