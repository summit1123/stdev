#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def review_root(root: Path) -> Path:
    return root / ".codex-loop" / "artifacts" / "pdf-review"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def slugify_stem(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")
    return slug or "submission"


def clean_preview(text: str, max_chars: int = 4000) -> str:
    stripped = (text or "").replace("\f", "\n").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in stripped.splitlines()]
    lines = [line for line in lines if line]
    preview = "\n".join(lines)
    return preview[:max_chars].strip()


def run_optional_command(command: list[str], timeout: int = 15) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except Exception:
        return None


def probe_pdf(path: Path) -> dict[str, Any]:
    binary = shutil.which("pdfinfo")
    if not binary:
        return {"available": False, "method": None, "error": "pdfinfo is not installed."}

    result = run_optional_command([binary, str(path)])
    if result is None:
        return {"available": False, "method": "pdfinfo", "error": "pdfinfo could not be executed."}
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "pdfinfo failed.").strip()
        return {"available": False, "method": "pdfinfo", "error": message}

    parsed: dict[str, str] = {}
    for line in (result.stdout or "").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parsed[key.strip()] = value.strip()

    pages_text = parsed.get("Pages", "")
    try:
        pages = int(pages_text)
    except ValueError:
        pages = None

    return {
        "available": True,
        "method": "pdfinfo",
        "pages": pages,
        "pageSize": parsed.get("Page size"),
        "pdfVersion": parsed.get("PDF version"),
        "creator": parsed.get("Creator"),
        "producer": parsed.get("Producer"),
        "creationDate": parsed.get("CreationDate"),
        "modDate": parsed.get("ModDate"),
    }


def extract_preview_text(path: Path) -> dict[str, Any]:
    binary = shutil.which("pdftotext")
    if not binary:
        return {"available": False, "method": None, "preview": "", "charCount": 0, "error": "pdftotext is not installed."}

    result = run_optional_command([binary, str(path), "-"])
    if result is None:
        return {"available": False, "method": "pdftotext", "preview": "", "charCount": 0, "error": "pdftotext could not be executed."}
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "pdftotext failed.").strip()
        return {"available": False, "method": "pdftotext", "preview": "", "charCount": 0, "error": message}

    preview = clean_preview(result.stdout or "")
    return {
        "available": bool(preview),
        "method": "pdftotext",
        "preview": preview,
        "charCount": len(preview),
        "error": None if preview else "No extractable text was found in the PDF output.",
    }


def build_review(root: Path, pdf_path: Path, max_megabytes: float) -> dict[str, Any]:
    path = pdf_path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    size_bytes = path.stat().st_size
    size_megabytes = round(size_bytes / (1024 * 1024), 3)
    metadata = probe_pdf(path)
    extraction = extract_preview_text(path)

    blockers: list[str] = []
    warnings: list[str] = []

    if path.suffix.lower() != ".pdf":
        blockers.append("Attachment must be a .pdf file for this review gate.")
    if "," in path.name:
        blockers.append("Filename contains a comma. Rename the file before upload to avoid submission errors.")
    if size_megabytes > max_megabytes:
        blockers.append(f"File size is {size_megabytes:.3f} MB, which exceeds the {max_megabytes:.1f} MB limit.")

    if not metadata.get("available"):
        warnings.append(metadata.get("error") or "PDF metadata could not be inspected.")
    if not extraction.get("available"):
        warnings.append(extraction.get("error") or "PDF text preview could not be extracted.")

    next_actions: list[str] = []
    if any("comma" in item.lower() for item in blockers):
        next_actions.append("Rename the attachment so the filename does not contain a comma.")
    if any("exceeds" in item.lower() for item in blockers):
        next_actions.append("Reduce the PDF size below the upload limit before the final submission pass.")
    if warnings:
        next_actions.append("Manually inspect the rendered PDF pages if automated text extraction is incomplete.")
    next_actions.append("Compare the PDF preview against `.codex-loop/prd/PRD.md`, `.codex-loop/prd/SUMMARY.md`, and the submission form before the next Ralph run.")

    return {
        "generatedAt": now_iso(),
        "projectRoot": str(root),
        "file": {
            "path": str(path),
            "name": path.name,
            "sizeBytes": size_bytes,
            "sizeMegabytes": size_megabytes,
            "extension": path.suffix.lower(),
        },
        "constraints": {
            "maxMegabytes": max_megabytes,
            "extensionOk": path.suffix.lower() == ".pdf",
            "filenameSafe": "," not in path.name,
            "sizeOk": size_megabytes <= max_megabytes,
        },
        "metadata": metadata,
        "extraction": extraction,
        "blockers": blockers,
        "warnings": warnings,
        "nextActions": next_actions,
    }


def render_review(review: dict[str, Any]) -> str:
    info = review["file"]
    metadata = review.get("metadata", {})
    extraction = review.get("extraction", {})
    blockers = review.get("blockers", [])
    warnings = review.get("warnings", [])
    preview = extraction.get("preview", "") if isinstance(extraction, dict) else ""
    lines = [
        "# Submission PDF Review",
        "",
        f"- Generated: {review['generatedAt']}",
        f"- File: {info['name']}",
        f"- Path: {info['path']}",
        f"- Size: {info['sizeMegabytes']:.3f} MB",
        f"- Pages: {metadata.get('pages', 'unknown')}",
        f"- PDF version: {metadata.get('pdfVersion', 'unknown')}",
        "",
        "## Blockers",
        *([f"- {item}" for item in blockers] or ["- None"]),
        "",
        "## Warnings",
        *([f"- {item}" for item in warnings] or ["- None"]),
        "",
        "## Suggested Next Actions",
        *([f"- {item}" for item in review.get("nextActions", [])] or ["- None"]),
        "",
        "## Preview",
    ]
    if preview:
        lines.extend(["```text", preview, "```"])
    else:
        lines.append("- No text preview available.")
    lines.append("")
    return "\n".join(lines)


def write_review_files(root: Path, review: dict[str, Any]) -> tuple[Path, Path]:
    name = slugify_stem(Path(review["file"]["name"]).stem)
    out_dir = review_root(root)
    json_path = out_dir / f"{name}-review.json"
    md_path = out_dir / f"{name}-review.md"
    write_json(json_path, review)
    write_text(md_path, render_review(review))
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Review a submission or planning PDF before the next SummitHarness run.")
    parser.add_argument("pdf", help="Path to the PDF file to inspect")
    parser.add_argument("--max-mb", type=float, default=20.0, help="Maximum allowed file size in megabytes")
    parser.add_argument("--stdout-only", action="store_true", help="Print the review instead of writing artifact files")
    args = parser.parse_args()

    root = project_root()
    review = build_review(root, Path(args.pdf), args.max_mb)

    if args.stdout_only:
        print(render_review(review))
    else:
        json_path, md_path = write_review_files(root, review)
        print(f"Wrote submission PDF review to {json_path}")
        print(f"Wrote submission PDF report to {md_path}")
        print(render_review(review))

    return 2 if review.get("blockers") else 0


if __name__ == "__main__":
    raise SystemExit(main())
