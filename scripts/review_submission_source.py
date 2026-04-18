#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


PLACEHOLDER_PATTERNS = [
    r'\bTODO\b',
    r'\bTBD\b',
    r'\bFIXME\b',
    r'\bReplace\b',
    r'작성해주세요',
    r'추후 작성',
    r'lorem ipsum',
]
ASSISTANT_TONE_PATTERNS = [
    r'본 문서는',
    r'이 문서는',
    r'이 페이지는',
    r'보여줍니다',
    r'설명합니다',
    r'다음과 같습니다',
    r'this document',
    r'this page',
]


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec='seconds')


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8') if path.exists() else ''


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + '\n')


def review_root(root: Path) -> Path:
    return root / '.codex-loop' / 'artifacts' / 'source-review'


def slugify_stem(name: str) -> str:
    slug = re.sub(r'[^A-Za-z0-9._-]+', '-', name).strip('-')
    return slug or 'document'


def extract_preset(design_text: str) -> str:
    match = re.search(r'(?mi)^Preset:\s*([A-Za-z0-9_-]+)\s*$', design_text or '')
    return match.group(1).strip().lower() if match else 'document-editorial'


def extract_reference_pack(design_text: str) -> str:
    match = re.search(r'(?mi)^Reference-Pack:\s*([A-Za-z0-9_-]+)\s*$', design_text or '')
    return match.group(1).strip().lower() if match else ''


def load_reference_pack(root: Path, name: str) -> str:
    if not name:
        return ''
    return read_text(root / '.codex-loop' / 'design' / 'reference-packs' / f'{name}.md')


def canonical_mode(mode: str) -> str:
    lowered = (mode or '').strip().lower()
    if lowered in {'proposal', 'submission', 'planning', 'contest', 'deck'}:
        return 'proposal'
    if lowered in {'prd', 'spec'}:
        return 'prd'
    if lowered in {'product-ui', 'ui', 'ux', 'design'}:
        return 'product-ui'
    return 'implementation'


def detect_mode(root: Path, explicit_mode: str | None) -> str:
    if explicit_mode:
        return canonical_mode(explicit_mode)
    config_path = root / '.codex-loop' / 'config.json'
    if config_path.exists():
        try:
            payload = json.loads(config_path.read_text(encoding='utf-8'))
            return canonical_mode(str(payload.get('loop', {}).get('mode', 'implementation')))
        except Exception:
            pass
    return 'proposal'


def first_heading(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('# '):
            return stripped[2:].strip()
    return ''


def section_headings(text: str) -> list[str]:
    return [line.strip()[3:].strip() for line in text.splitlines() if line.strip().startswith('## ')]


def table_count(text: str) -> int:
    count = 0
    lines = text.splitlines()
    pattern = r'\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?'
    for index in range(len(lines) - 1):
        if '|' in lines[index] and re.fullmatch(pattern, lines[index + 1].strip()):
            count += 1
    return count


def word_count(text: str) -> int:
    words = re.findall(r'[A-Za-z0-9가-힣]+', text)
    return len(words)


def detect_patterns(text: str, patterns: list[str]) -> list[str]:
    hits: list[str] = []
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            hits.append(pattern)
    return hits


def concept_coverage(text: str) -> dict[str, bool]:
    lowered = text.lower()
    checks = {
        'problem': ['문제', '배경', '리스크', 'problem'],
        'solution': ['해결', '솔루션', '구조', 'solution'],
        'feasibility': ['실현', '근거', 'proof', '데모', 'feasibility'],
        'business': ['사업', '수익', '도입', 'buyer', 'business'],
        'impact': ['효과', '기대', '활용', 'impact', 'effect'],
    }
    return {key: any(token in lowered for token in tokens) for key, tokens in checks.items()}


def build_review(root: Path, source_path: Path, mode: str, design_path: Path) -> dict[str, Any]:
    path = source_path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    design_text = read_text(design_path)
    text = read_text(path)
    title = first_heading(text)
    sections = section_headings(text)
    words = word_count(text)
    tables = table_count(text)
    placeholder_hits = detect_patterns(text, PLACEHOLDER_PATTERNS)
    assistant_hits = detect_patterns(text, ASSISTANT_TONE_PATTERNS)
    coverage = concept_coverage(text)
    mode_name = canonical_mode(mode)
    preset = extract_preset(design_text)
    reference_pack = extract_reference_pack(design_text)
    reference_pack_text = load_reference_pack(root, reference_pack)
    image_refs = text.count('![')
    link_refs = len(re.findall(r'\[[^\]]+\]\([^)]+\)', text))

    blockers: list[str] = []
    warnings: list[str] = []
    next_actions: list[str] = []

    if path.suffix.lower() != '.md':
        blockers.append('Source gate expects a Markdown document as the source of truth.')
    if not title:
        blockers.append('The source is missing a single H1 title.')
    if placeholder_hits:
        blockers.append('Placeholder or template markers remain in the source document.')
    if not design_text:
        warnings.append('No design contract was found. Add .codex-loop/design/DESIGN.md so layout decisions stay intentional.')
    if reference_pack and not reference_pack_text:
        warnings.append(f'Selected reference pack `{reference_pack}` was not found under .codex-loop/design/reference-packs/.')
    if assistant_hits:
        warnings.append('The source still contains assistant-style narration. Rewrite it in reviewer-facing language.')

    if mode_name == 'proposal':
        if words < 600:
            blockers.append('Proposal source is too thin. Expand the actual substance before relying on layout.')
        elif words < 1000:
            warnings.append('Proposal source is still light. Add more evidence, comparison, or operational detail.')
        if len(sections) < 5:
            blockers.append('Proposal source needs more structured sections for problem, solution, feasibility, business path, and effect.')
        if tables < 1:
            blockers.append('Proposal source needs at least one real comparison or structure table.')
        if sum(1 for value in coverage.values() if value) < 4:
            warnings.append('Proposal source is missing one or more core narrative blocks such as feasibility, business path, or expected effect.')
        if preset != 'document-editorial':
            warnings.append('Proposal mode should normally use the document-editorial preset.')
        if not reference_pack:
            warnings.append('Proposal mode should usually select a reference pack so the visual direction is explicit.')
        if link_refs < 1:
            warnings.append('Consider adding source-backed evidence links or references for reviewer trust.')
    elif mode_name == 'prd':
        if words < 500:
            blockers.append('PRD source is too short to drive execution truthfully.')
        if len(sections) < 5:
            blockers.append('PRD needs sections for users, scope, requirements, constraints, and acceptance.')
        lowered = text.lower()
        for keyword, label in [('user', 'users'), ('requirement', 'requirements'), ('acceptance', 'acceptance criteria')]:
            if keyword not in lowered and label not in lowered and label.replace(' ', '') not in lowered:
                warnings.append(f'PRD may be missing an explicit {label} section.')
    elif mode_name == 'product-ui':
        if preset != 'product-ops':
            warnings.append('Product UI mode should usually use the product-ops preset.')
        if not reference_pack:
            warnings.append('Product UI mode should select a reference pack before visual polishing begins.')
        if image_refs < 1 and 'assets/' not in text and 'registry' not in text.lower():
            blockers.append('Product UI source should reference actual assets, screenshots, or approved visual inputs.')
        if len(sections) < 4:
            warnings.append('Product UI source needs clearer sections for flow, screen structure, assets, and verification.')
    else:
        if words < 250:
            warnings.append('Implementation mode source notes are still very short. Keep code as truth, but tighten supporting docs.')

    if blockers:
        next_actions.append('Fix the Markdown source first; do not treat PDF output as the primary artifact.')
    if mode_name == 'proposal':
        next_actions.append('Run python3 scripts/render_markdown_submission.py after the source review passes.')
    next_actions.append('Refresh the context packet so Ralph sees the latest source truth.')

    preview_lines = [line.rstrip() for line in text.splitlines()[:40] if line.strip()]

    return {
        'generatedAt': now_iso(),
        'projectRoot': str(root),
        'mode': mode_name,
        'file': {
            'path': str(path),
            'name': path.name,
            'extension': path.suffix.lower(),
        },
        'design': {
            'path': str(design_path.resolve()),
            'preset': preset,
            'referencePack': reference_pack,
            'referencePackLoaded': bool(reference_pack_text),
            'present': bool(design_text),
        },
        'stats': {
            'wordCount': words,
            'sectionCount': len(sections),
            'tableCount': tables,
            'imageRefs': image_refs,
            'linkRefs': link_refs,
        },
        'structure': {
            'title': title,
            'sections': sections,
            'conceptCoverage': coverage,
        },
        'preview': '\n'.join(preview_lines),
        'blockers': blockers,
        'warnings': warnings,
        'nextActions': next_actions,
    }


def render_review(review: dict[str, Any]) -> str:
    lines = [
        '# Submission Source Review',
        '',
        f"- Generated: {review['generatedAt']}",
        f"- Mode: {review['mode']}",
        f"- File: {review['file']['name']}",
        f"- Design preset: {review['design']['preset']}",
        f"- Reference pack: {review['design'].get('referencePack') or 'none'}",
        f"- Word count: {review['stats']['wordCount']}",
        f"- Sections: {review['stats']['sectionCount']}",
        f"- Tables: {review['stats']['tableCount']}",
        '',
        '## Blockers',
        *([f'- {item}' for item in review.get('blockers', [])] or ['- None']),
        '',
        '## Warnings',
        *([f'- {item}' for item in review.get('warnings', [])] or ['- None']),
        '',
        '## Suggested Next Actions',
        *([f'- {item}' for item in review.get('nextActions', [])] or ['- None']),
        '',
        '## Preview',
    ]
    preview = review.get('preview', '')
    if preview:
        lines.extend(['```text', preview, '```'])
    else:
        lines.append('- No preview available.')
    lines.append('')
    return '\n'.join(lines)


def write_review_files(root: Path, review: dict[str, Any]) -> tuple[Path, Path]:
    name = slugify_stem(Path(review['file']['name']).stem)
    out_dir = review_root(root)
    json_path = out_dir / f'{name}-review.json'
    md_path = out_dir / f'{name}-review.md'
    write_json(json_path, review)
    write_text(md_path, render_review(review))
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description='Review Markdown document source before rendering or final submission packaging.')
    parser.add_argument('source', nargs='?', default='docs/submissions/proposal.md', help='Markdown source file to review')
    parser.add_argument('--mode', help='Override document mode')
    parser.add_argument('--design', default='.codex-loop/design/DESIGN.md', help='Design contract file')
    parser.add_argument('--stdout-only', action='store_true', help='Print the review instead of writing artifact files')
    args = parser.parse_args()

    root = project_root()
    source_path = (root / args.source).resolve()
    design_path = (root / args.design).resolve()
    mode = detect_mode(root, args.mode)
    review = build_review(root, source_path, mode, design_path)

    if args.stdout_only:
        print(render_review(review))
    else:
        json_path, md_path = write_review_files(root, review)
        print(f'Wrote source review to {json_path}')
        print(f'Wrote source review report to {md_path}')
        print(render_review(review))

    return 2 if review.get('blockers') else 0


if __name__ == '__main__':
    raise SystemExit(main())
