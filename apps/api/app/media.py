from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
import os
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

    def render(self, entry_id: str, result: EntryResult) -> EntryResult:
        image_paths = self._render_storyboards(entry_id, result)
        result.media.storyboardUrls = [self._media_url(path) for path in image_paths]
        if image_paths:
            result.media.thumbnailUrl = self._media_url(image_paths[0])

        video_path = self._render_video(
            entry_id,
            result,
            image_paths,
            source_video=None,
        )
        if video_path:
            result.media.videoUrl = self._media_url(video_path)

        sora_asset = self._prepare_sora_request(entry_id, result)
        if sora_asset:
            if sora_asset.suffix == ".mp4":
                result.media.soraVideoUrl = self._media_url(sora_asset)
            else:
                result.media.soraRequestUrl = self._media_url(sora_asset)
        return result

    def _render_storyboards(self, entry_id: str, result: EntryResult) -> list[Path]:
        poster = self._load_poster(entry_id)
        rendered: list[Path] = []
        for index, shot in enumerate(result.videoDirector.shots):
            path = self.store.abs_media_path(entry_id, f"storyboard-{index + 1:02d}.png")
            generated_path = self.store.abs_media_path(entry_id, f"generated-storyboard-{index + 1:02d}.png")
            if generated_path.exists():
                Image.open(generated_path).convert("RGB").save(path)
                rendered.append(path)
                continue

            if path.exists() and index < 2:
                rendered.append(path)
                continue

            image = self._render_storyboard_slide(entry_id, index, shot, result, poster)
            image.save(path)
            rendered.append(path)
        return rendered

    def _render_video(
        self,
        entry_id: str,
        result: EntryResult,
        image_paths: list[Path],
        source_video: Path | None = None,
    ) -> Path | None:
        if shutil.which("ffmpeg") is None:
            return None

        if source_video is None:
            if not image_paths:
                return None

            segment_paths: list[Path] = []
            total_duration = float(result.videoDirector.targetDurationSeconds)
            for index, image_path in enumerate(image_paths):
                segment_path = self.store.abs_media_path(entry_id, f"segment-{index + 1:02d}.mp4")
                duration_seconds = (
                    result.videoDirector.shots[index].durationSeconds if index < len(result.videoDirector.shots) else 3
                )
                cmd = [
                    "ffmpeg",
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
                    "ffmpeg",
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
        final_path = self.store.abs_media_path(entry_id, "story-video.mp4")
        fade_out_start = max(total_duration - 0.45, 0.1)
        if audio_path and audio_path.exists():
            self._run(
                [
                    "ffmpeg",
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
                        "volume=1.10,"
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
                    "ffmpeg",
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

    def _prepare_sora_request(self, entry_id: str, result: EntryResult) -> Path | None:
        if not self.settings.sora_cli_path.exists():
            return None

        prompt_path = self.store.abs_media_path(entry_id, "sora-prompt.txt")
        prompt_path.write_text(result.videoDirector.soraPrompt, encoding="utf-8")

        mode = self.settings.sora_render_mode.strip().lower()
        if mode not in {"dry_run", "live"}:
            return None

        if mode == "dry_run":
            out_path = self.store.abs_media_path(entry_id, "sora-request.json")
            cmd = [
                "python3",
                str(self.settings.sora_cli_path),
                "create",
                "--model",
                self.settings.sora_model,
                "--prompt-file",
                str(prompt_path),
                "--no-augment",
                "--size",
                "1280x720",
                "--seconds",
                "12",
                "--dry-run",
                "--json-out",
                str(out_path),
            ]
            self._run(cmd, timeout=20)
            return out_path

        create_path = self.store.abs_media_path(entry_id, "sora-create.json")
        job_path = self.store.abs_media_path(entry_id, "sora-job.json")
        video_path = self.store.abs_media_path(entry_id, "sora-video.mp4")
        uv_bin = str(self.settings.uv_bin_path) if self.settings.uv_bin_path.exists() else "uv"
        create_cmd = [
            uv_bin,
            "run",
            "--with",
            "openai",
            "--with",
            "httpx",
            "python",
            str(self.settings.sora_cli_path),
            "create-and-poll",
            "--model",
            self.settings.sora_model,
            "--prompt-file",
            str(prompt_path),
            "--no-augment",
            "--size",
            "1280x720",
            "--seconds",
            "12",
            "--download",
            "--variant",
            "video",
            "--out",
            str(video_path),
            "--json-out",
            str(job_path),
        ]
        env = os.environ.copy()
        if self.settings.openai_api_key:
            env["OPENAI_API_KEY"] = self.settings.openai_api_key
        env.setdefault("UV_CACHE_DIR", "/tmp/uv-cache")
        create_path.write_text(
            json.dumps(
                {
                    "status": "queued",
                    "model": self.settings.sora_model,
                    "seconds": 12,
                    "size": "1280x720",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        try:
            self._run(create_cmd, env=env, timeout=1800)
        except Exception as exc:
            error_payload = {
                "status": "failed",
                "model": self.settings.sora_model,
                "seconds": 12,
                "size": "1280x720",
                "error": str(exc),
            }
            job_path.write_text(
                json.dumps(error_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return job_path if job_path.exists() else create_path

        if video_path.exists():
            return video_path
        if job_path.exists():
            return job_path
        return create_path if create_path.exists() else None

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
        candidates = [
            self.store.abs_media_path(entry_id, "scene-visual.png"),
            self.store.abs_media_path(entry_id, "storyboard-01.png"),
            self.store.abs_media_path(entry_id, "storyboard-02.png"),
        ]
        if index >= 1:
            candidates.insert(0, self.store.abs_media_path(entry_id, f"storyboard-{index:02d}.png"))
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

    def _media_url(self, path: Path) -> str:
        relative = path.relative_to(self.settings.media_mount_dir)
        return f"/media/{relative.as_posix()}"
