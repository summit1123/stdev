#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


DEFAULT_REGISTRY = {'assets': [], 'updatedAt': None}


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec='seconds')


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def registry_path(root: Path) -> Path:
    return root / '.codex-loop' / 'assets' / 'registry.json'


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return DEFAULT_REGISTRY.copy()
    return json.loads(path.read_text(encoding='utf-8'))


def write_registry(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def cmd_init() -> int:
    path = registry_path(project_root())
    payload = load_registry(path)
    payload.setdefault('assets', [])
    payload['updatedAt'] = now_iso()
    write_registry(path, payload)
    print(f'Initialized asset registry at {path}')
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    root = project_root()
    path = registry_path(root)
    payload = load_registry(path)
    assets = payload.setdefault('assets', [])
    assets.append(
        {
            'id': f"asset-{len(assets) + 1:03d}",
            'kind': args.kind,
            'title': args.title,
            'path': args.path,
            'source': args.source,
            'status': args.status,
            'role': args.role,
            'approvedFor': args.approved_for,
            'styleFamily': args.style_family,
            'notes': args.notes,
            'createdAt': now_iso(),
        }
    )
    payload['updatedAt'] = now_iso()
    write_registry(path, payload)
    print(f'Registered asset in {path}')
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    payload = load_registry(registry_path(project_root()))
    assets = payload.get('assets', []) if isinstance(payload, dict) else []
    if args.status:
        assets = [item for item in assets if str(item.get('status', '')).lower() == args.status.lower()]
    if args.json:
        print(json.dumps(assets, ensure_ascii=False, indent=2))
        return 0
    if not assets:
        print('No matching assets.')
        return 0
    for asset in assets:
        label = asset.get('title') or asset.get('path')
        role = f" role={asset.get('role')}" if asset.get('role') else ''
        approved_for = f" approved-for={asset.get('approvedFor')}" if asset.get('approvedFor') else ''
        print(f"- {asset.get('id')} [{asset.get('status')}] {asset.get('kind')} {label}{role}{approved_for}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Track approved and reference assets for SummitHarness.')
    subparsers = parser.add_subparsers(dest='command', required=True)

    init_cmd = subparsers.add_parser('init', help='Create the asset registry if missing')
    init_cmd.set_defaults(func=lambda args: cmd_init())

    add_cmd = subparsers.add_parser('add', help='Register a new asset')
    add_cmd.add_argument('--kind', choices=['image', 'video', 'gif', 'figma', 'screenshot', 'reference'], required=True)
    add_cmd.add_argument('--title', help='Human-readable asset title')
    add_cmd.add_argument('--path', required=True, help='Workspace path or remote URL')
    add_cmd.add_argument('--source', required=True, help='imagegen, sora, figma, manual, etc.')
    add_cmd.add_argument('--status', default='draft', choices=['draft', 'reference', 'selected', 'approved', 'rejected'])
    add_cmd.add_argument('--role', choices=['evidence', 'explainer', 'product-ui', 'decorative', 'reference'], default='reference')
    add_cmd.add_argument('--approved-for', choices=['proposal', 'app', 'both', 'research'], default='both')
    add_cmd.add_argument('--style-family', help='Optional visual family or preset name')
    add_cmd.add_argument('--notes', help='Optional notes')
    add_cmd.set_defaults(func=cmd_add)

    list_cmd = subparsers.add_parser('list', help='List known assets')
    list_cmd.add_argument('--status', help='Filter by status')
    list_cmd.add_argument('--json', action='store_true')
    list_cmd.set_defaults(func=cmd_list)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    raise SystemExit(main())
