from __future__ import annotations

import math
import shutil
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from app.config import Settings
from app.models import EntryResult
from app.store import LocalStore


class MediaComposer:
    def __init__(self, settings: Settings, store: LocalStore) -> None:
        self.settings = settings
        self.store = store
        self.font_path = self._resolve_font_path()
        self.ffmpeg_path = self._resolve_binary("ffmpeg")
        self.ffprobe_path = self._resolve_binary("ffprobe")

    def render(self, entry_id: str, result: EntryResult) -> EntryResult:
        image_paths, generated_paths = self._render_storyboards(entry_id, result)
        result.media.storyboardUrls = [self._media_url(path) for path in image_paths]
        result.media.generatedStoryboardUrls = [self._media_url(path) for path in generated_paths]
        if generated_paths:
            result.media.thumbnailUrl = self._media_url(generated_paths[0])
        elif result.sceneVisual.imageUrl:
            result.media.thumbnailUrl = result.sceneVisual.imageUrl
        else:
            result.media.thumbnailUrl = None

        audio_path = self._audio_path(entry_id)
        audio_duration = self._probe_duration(audio_path) if audio_path and audio_path.exists() else None
        if audio_duration:
            result.narration.durationSec = round(audio_duration, 2)

        render_duration = self._resolve_render_duration(result, audio_duration)
        result.videoDirector.targetDurationSeconds = math.ceil(render_duration)

        video_path = self._render_video(
            entry_id,
            result,
            image_paths,
            total_duration=render_duration,
            source_video=None,
        )
        if video_path:
            result.media.videoUrl = self._media_url(video_path)
        result.media.soraRequestUrl = None
        result.media.soraVideoUrl = None
        return result

    def planned_generated_shot_indices(self, result: EntryResult) -> list[int]:
        shot_count = len(result.videoDirector.shots)
        if shot_count <= 1:
            return [0] if shot_count == 1 else []
        target_count = max(1, (shot_count + 1) // 2)
        if target_count == 1:
            return [0]
        indices = {
            min(
                shot_count - 1,
                round(sample_index * (shot_count - 1) / (target_count - 1)),
            )
            for sample_index in range(target_count)
        }
        return sorted(indices)

    def _render_storyboards(self, entry_id: str, result: EntryResult) -> tuple[list[Path], list[Path]]:
        poster = self._load_poster(entry_id)
        rendered: list[Path] = []
        generated: list[Path] = []
        for index, shot in enumerate(result.videoDirector.shots):
            path = self.store.abs_media_path(entry_id, f"storyboard-{index + 1:02d}.png")
            generated_path = self.store.abs_media_path(entry_id, f"generated-storyboard-{index + 1:02d}.png")
            if generated_path.exists():
                Image.open(generated_path).convert("RGB").save(path)
                rendered.append(path)
                generated.append(path)
                continue

            if path.exists() and index < 2:
                rendered.append(path)
                continue

            image = self._render_storyboard_slide(entry_id, index, shot, result, poster)
            image.save(path)
            rendered.append(path)
        return rendered, generated

    def _render_video(
        self,
        entry_id: str,
        result: EntryResult,
        image_paths: list[Path],
        total_duration: float,
        source_video: Path | None = None,
        output_name: str = "story-video.mp4",
    ) -> Path | None:
        if self.ffmpeg_path is None:
            return None

        if source_video is None:
            if not image_paths:
                return None

            segment_paths: list[Path] = []
            segment_durations = self._scaled_shot_durations(result, total_duration, len(image_paths))
            for index, image_path in enumerate(image_paths):
                segment_path = self.store.abs_media_path(entry_id, f"segment-{index + 1:02d}.mp4")
                duration_seconds = segment_durations[index]
                cmd = [
                    str(self.ffmpeg_path),
                    "-y",
                    "-loop",
                    "1",
                    "-i",
                    str(image_path),
                    "-vf",
                    (
                        "scale=1280:720:force_original_aspect_ratio=increase,"
                        "crop=1280:720,"
                        "format=yuv420p"
                    ),
                    "-t",
                    str(duration_seconds),
                    "-r",
                    "25",
                    str(segment_path),
                ]
                self._run(cmd)
                segment_paths.append(segment_path)

            concat_file = self.store.abs_media_path(entry_id, "segments.txt")
            concat_file.write_text(
                "\n".join(f"file '{segment_path.as_posix()}'" for segment_path in segment_paths),
                encoding="utf-8",
            )

            stitched_path = self.store.abs_media_path(entry_id, "story-video-base.mp4")
            self._run(
                [
                    str(self.ffmpeg_path),
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(concat_file),
                    "-c",
                    "copy",
                    str(stitched_path),
                ]
            )
        else:
            stitched_path = source_video

        audio_path = self._audio_path(entry_id)
        final_path = self.store.abs_media_path(entry_id, output_name)
        fade_out_start = max(total_duration - 0.45, 0.1)
        if audio_path and audio_path.exists():
            self._run(
                [
                    str(self.ffmpeg_path),
                    "-y",
                    "-i",
                    str(stitched_path),
                    "-i",
                    str(audio_path),
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-vf",
                    f"fade=t=in:st=0:d=0.25,fade=t=out:st={fade_out_start:.2f}:d=0.45",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-movflags",
                    "+faststart",
                    "-af",
                    (
                        f"aresample=48000:resampler=soxr,"
                        "highpass=f=60,"
                        "lowpass=f=12000,"
                        "volume=1.08,"
                        "alimiter=limit=0.92,"
                        f"apad=whole_dur={total_duration}"
                    ),
                    "-ar",
                    "48000",
                    "-ac",
                    "1",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "128k",
                    "-t",
                    str(total_duration),
                    str(final_path),
                ]
            )
        else:
            self._run(
                [
                    str(self.ffmpeg_path),
                    "-y",
                    "-i",
                    str(stitched_path),
                    "-vf",
                    f"fade=t=in:st=0:d=0.25,fade=t=out:st={fade_out_start:.2f}:d=0.45",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-movflags",
                    "+faststart",
                    "-an",
                    "-t",
                    str(total_duration),
                    str(final_path),
                ]
            )
        return final_path

    def _resolve_video_duration(self, result: EntryResult, source_video: Path | None) -> float:
        if source_video and source_video.exists():
            probed = self._probe_duration(source_video)
            if probed:
                return probed
        return float(result.videoDirector.targetDurationSeconds)

    def _resolve_render_duration(self, result: EntryResult, audio_duration: float | None) -> float:
        base_duration = float(result.videoDirector.targetDurationSeconds)
        if not audio_duration:
            return base_duration
        return max(base_duration, round(audio_duration + 0.35, 2))

    def _scaled_shot_durations(
        self,
        result: EntryResult,
        total_duration: float,
        image_count: int,
    ) -> list[float]:
        base_durations = [
            float(result.videoDirector.shots[index].durationSeconds if index < len(result.videoDirector.shots) else 3)
            for index in range(image_count)
        ]
        base_total = sum(base_durations) or float(image_count or 1)
        scale = total_duration / base_total
        scaled = [round(duration * scale, 2) for duration in base_durations]
        drift = round(total_duration - sum(scaled), 2)
        if scaled:
            scaled[-1] = round(max(0.4, scaled[-1] + drift), 2)
        return scaled

    def _probe_duration(self, path: Path) -> float | None:
        if self.ffprobe_path is None:
            return None
        try:
            completed = subprocess.run(
                [
                    str(self.ffprobe_path),
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(path),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            value = completed.stdout.strip()
            if not value:
                return None
            return float(value)
        except Exception:
            return None

    def _audio_path(self, entry_id: str) -> Path | None:
        path = self.store.abs_media_path(entry_id, "narration.mp3")
        return path if path.exists() else None

    def _load_poster(self, entry_id: str) -> Image.Image | None:
        entry_dir = self.store.entry_dir(entry_id)
        for candidate in entry_dir.glob("original.*"):
            if candidate.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                return Image.open(candidate).convert("RGB")
        return None

    def _run(
        self,
        cmd: list[str],
        env: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> None:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            timeout=timeout,
        )

    def _render_storyboard_slide(
        self,
        entry_id: str,
        index: int,
        shot,
        result: EntryResult,
        poster: Image.Image | None,
    ) -> Image.Image:
        source = self._storyboard_source_image(entry_id, index, result, poster)
        return ImageOps.fit(source, (1280, 720), method=Image.Resampling.LANCZOS)

    def _storyboard_source_image(
        self,
        entry_id: str,
        index: int,
        result: EntryResult,
        poster: Image.Image | None,
    ) -> Image.Image:
        frame_number = index + 1
        candidates = [
            self.store.abs_media_path(entry_id, f"generated-storyboard-{frame_number:02d}.png"),
            self.store.abs_media_path(entry_id, f"storyboard-{frame_number:02d}.png"),
            self.store.abs_media_path(entry_id, "scene-visual.png"),
            self.store.abs_media_path(entry_id, "generated-storyboard-01.png"),
            self.store.abs_media_path(entry_id, "generated-storyboard-02.png"),
            self.store.abs_media_path(entry_id, "storyboard-01.png"),
            self.store.abs_media_path(entry_id, "storyboard-02.png"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return Image.open(candidate).convert("RGB")
        if poster is not None:
            return poster.copy()
        return Image.new("RGB", (1280, 720), "#F8F2E8")

    def _clip(self, text: str, limit: int) -> str:
        compact = " ".join(text.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 1].rstrip() + "…"

    def _font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        if self.font_path:
            return ImageFont.truetype(str(self.font_path), size=size)
        return ImageFont.load_default()

    def _resolve_font_path(self) -> Path | None:
        candidates = [
            Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
            Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
            Path("/Library/Fonts/Arial Unicode.ttf"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _resolve_binary(self, name: str) -> Path | None:
        discovered = shutil.which(name)
        if discovered:
            return Path(discovered)

        candidates = [
            Path(f"/opt/homebrew/bin/{name}"),
            Path(f"/usr/local/bin/{name}"),
            Path(f"/usr/bin/{name}"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _media_url(self, path: Path) -> str:
        return self.store.media_url_for_path(path)
