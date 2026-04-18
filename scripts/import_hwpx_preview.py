#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path


def clean_preview_text(raw: str) -> str:
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"<([^<>]+)>", lambda m: m.group(1).strip(), text)
    text = text.replace("<>", "")
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: import_hwpx_preview.py <file.hwpx>", file=sys.stderr)
        return 2

    path = Path(sys.argv[1]).expanduser()
    if not path.exists():
        print(f"missing file: {path}", file=sys.stderr)
        return 2

    with zipfile.ZipFile(path) as archive:
        preview = archive.read("Preview/PrvText.txt").decode("utf-8", errors="ignore")

    print(clean_preview_text(preview))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
