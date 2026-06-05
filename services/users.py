import json
import os
import re

from config import QC_DECISIONS, USERS_JSON_PATH, USERS_DIR, VISIBILITY_PATH, user_dir
from services.qc_store import parse_decision


def load_users():
    """Load username→password map from users.json (plaintext passwords)."""
    with open(USERS_JSON_PATH, 'r') as f:
        return json.load(f)


def authenticate(username, password):
    """Return True if username exists and password matches."""
    if not username or not password:
        return False
    users = load_users()
    return users.get(username) == password


_SAFE_NAME = re.compile(r'^[A-Za-z0-9_.\-]+\.json$')


def _list_files_raw(username):
    """All *.json filenames in a user's folder — no visibility filtering."""
    folder = user_dir(username)
    if not os.path.isdir(folder):
        return []
    return sorted(
        name for name in os.listdir(folder)
        if _SAFE_NAME.match(name) and os.path.isfile(os.path.join(folder, name))
    )


def list_qc_files(username):
    """Visible *.json files for a user. Admin sees everything; for other users,
    files hidden by admin (in file_visibility.json) are filtered out."""
    files = _list_files_raw(username)
    if username == 'admin':
        return files
    hidden = set(load_visibility().get(username, []))
    return [f for f in files if f not in hidden]


# ── Admin: list users + per-user QC-file visibility ─────────────────────────
def list_all_users():
    """All usernames from users.json, sorted."""
    return sorted(load_users().keys())


def load_visibility():
    """Load {username: [hidden_filename, ...]} from file_visibility.json."""
    try:
        with open(VISIBILITY_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def _save_visibility(v):
    with open(VISIBILITY_PATH, 'w') as f:
        json.dump(v, f, indent=2, ensure_ascii=False)


def set_file_visibility(username, filename, visible):
    """Show/hide one of a user's QC files. Returns False if the file doesn't
    exist in that user's folder."""
    if filename not in _list_files_raw(username):
        return False
    v = load_visibility()
    hidden = set(v.get(username, []))
    hidden.discard(filename) if visible else hidden.add(filename)
    if hidden:
        v[username] = sorted(hidden)
    else:
        v.pop(username, None)
    _save_visibility(v)
    return True


def _file_progress(username, filename):
    """QC progress for one file. A phase counts as 'QC'd' when its comment is
    non-empty. Returns {total, ed, es} (patient counts)."""
    path = os.path.join(user_dir(username), filename)
    try:
        with open(path) as f:
            d = json.load(f)
    except (OSError, ValueError):
        return {'total': 0, 'ed': 0, 'es': 0}
    total = ed = es = 0
    for k, v in d.items():
        if k == '__meta__' or not isinstance(v, dict):
            continue
        total += 1
        # Only a real reviewer decision counts — a bare "CardiacAgent: …" note
        # (no accept/reject/… prefix) parses to 'unknown' and is NOT counted.
        if parse_decision(v.get('ED_Comments', '')) in QC_DECISIONS:
            ed += 1
        if parse_decision(v.get('ES_Comments', '')) in QC_DECISIONS:
            es += 1
    return {'total': total, 'ed': ed, 'es': es}


def admin_overview():
    """[{username, files:[{name, visible, progress}]}] across all users — for the
    admin UI. `progress` = {total, ed, es}: patients QC'd (= has a comment) per phase."""
    vis = load_visibility()
    out = []
    for u in list_all_users():
        hidden = set(vis.get(u, []))
        files = [
            {'name': f, 'visible': f not in hidden, 'progress': _file_progress(u, f)}
            for f in _list_files_raw(u)
        ]
        out.append({'username': u, 'files': files})
    return out


def resolve_qc_path(username, filename):
    """Validate filename belongs to the user's folder and return absolute path.

    Returns None if the filename is unsafe or the file doesn't exist. This
    prevents path traversal via '../' or absolute paths.
    """
    if not filename or not _SAFE_NAME.match(filename):
        return None
    path = os.path.join(user_dir(username), filename)
    if not os.path.isfile(path):
        return None
    return path
