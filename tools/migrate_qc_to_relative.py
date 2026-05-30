#!/usr/bin/env python3
"""Migrate every JSON/users/<user>/*.json from v1 (absolute patient keys) to
v2 (relative keys + __meta__.dataset_root).

Run from the repo root:
    python3 tools/migrate_qc_to_relative.py           # dry-run, prints plan
    python3 tools/migrate_qc_to_relative.py --apply   # actually rewrites files

Safe to re-run: files that already carry `__meta__` are skipped.
Each modified file gets a `<name>.bak` sibling before rewriting.

Why: v1 stored absolute paths like
    "/home/maxmo2009/AQC_dataset/.../patient_001": {...}
in every key. Moving the dataset directory (`/home/maxmo2009/AQC_dataset` →
`/mnt/data/AQC_dataset`) silently invalidates every QC entry. v2 lifts the
common prefix to one place:
    {"__meta__": {"dataset_root": "/home/maxmo2009/AQC_dataset/...",
                  "schema_version": 2},
     "patient_001": {...},
     "patient_002": {...}}
After migration, moving the dataset is a one-line edit per file.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

# Add the repo root so we can import services.qc_store (META_KEY constant).
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from services.qc_store import META_KEY  # noqa: E402


def find_qc_files(users_dir: Path) -> list[Path]:
    return sorted(users_dir.glob('*/*.json'))


def plan_migration(path: Path) -> tuple[str, dict | None, str]:
    """Return (status, new_data, message) for one JSON file.

    status ∈ {'SKIP', 'MIGRATE', 'ERROR'}
    """
    try:
        with path.open('r') as f:
            data = json.load(f)
    except Exception as exc:
        return ('ERROR', None, f'cannot parse: {exc}')

    if not isinstance(data, dict):
        return ('ERROR', None, 'top-level is not a dict')

    if META_KEY in data:
        return ('SKIP', None, 'already has __meta__ (v2)')

    keys = list(data.keys())
    if not keys:
        return ('SKIP', None, 'empty file (no patients)')

    # Require ALL keys to look like absolute paths — refuse to guess otherwise.
    if not all(k.startswith('/') for k in keys):
        return ('ERROR', None, 'mixed absolute/relative keys; refusing to guess')

    common = os.path.commonpath(keys)
    # commonpath of [single path] returns the path itself — that would yield
    # an empty relative key. Fall back to the dirname.
    if common in keys:
        common = os.path.dirname(common)
    if not common or common == '/':
        return ('ERROR', None, f'common prefix too shallow ({common!r})')

    # Build the new dict, preserving original patient order (Python 3.7+ dict
    # preserves insertion order — critical because session.patient_index is
    # positional).
    new_data: dict = {
        META_KEY: {
            'schema_version': 2,
            'dataset_root': common,
        }
    }
    for k in keys:
        rel = os.path.relpath(k, common)
        if rel.startswith('..'):
            return ('ERROR', None, f"key {k!r} escapes common prefix")
        new_data[rel] = data[k]

    return ('MIGRATE', new_data, f'{len(keys)} patients, root={common}')


def apply_migration(path: Path, new_data: dict) -> None:
    bak = path.with_suffix(path.suffix + '.bak')
    if not bak.exists():
        shutil.copy2(path, bak)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w') as f:
        json.dump(new_data, f, indent=4)
    os.replace(tmp, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true',
                        help='Actually rewrite the files (default: dry-run)')
    parser.add_argument('--users-dir',
                        default=str(REPO_ROOT / 'JSON' / 'users'),
                        help='Path to JSON/users/ (default: repo JSON/users/)')
    args = parser.parse_args()

    users_dir = Path(args.users_dir)
    if not users_dir.is_dir():
        print(f'ERROR: {users_dir} is not a directory', file=sys.stderr)
        return 2

    files = find_qc_files(users_dir)
    if not files:
        print(f'No QC files found under {users_dir}')
        return 0

    print(f'{"DRY-RUN" if not args.apply else "APPLYING"} '
          f'across {len(files)} file(s) under {users_dir}\n')

    counts = {'SKIP': 0, 'MIGRATE': 0, 'ERROR': 0}
    for path in files:
        rel = path.relative_to(users_dir)
        status, new_data, msg = plan_migration(path)
        counts[status] += 1
        marker = {'SKIP': '·', 'MIGRATE': '→', 'ERROR': '✗'}[status]
        print(f'  {marker} {rel}  [{status}]  {msg}')
        if status == 'MIGRATE' and args.apply:
            try:
                apply_migration(path, new_data)
                print(f'     written; backup at {path.name}.bak')
            except Exception as exc:
                print(f'     FAILED to write: {exc}')
                counts['ERROR'] += 1

    print(f'\nSummary: {counts["MIGRATE"]} to migrate, '
          f'{counts["SKIP"]} already-v2, {counts["ERROR"]} error(s)')
    if not args.apply and counts['MIGRATE']:
        print('\nRe-run with --apply to write changes.')
    return 0 if counts['ERROR'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
