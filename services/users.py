import json
import os
import re
import shutil

from config import QC_DECISIONS, USERS_JSON_PATH, USERS_DIR, VISIBILITY_PATH, user_dir
from services.qc_store import parse_decision


def load_users():
    """Load username→password map from users.json (plaintext passwords)."""
    with open(USERS_JSON_PATH, 'r') as f:
        return json.load(f)


def _save_users(users):
    with open(USERS_JSON_PATH, 'w') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


# Usernames double as folder names (JSON/users/<name>/), so they must be a
# single safe path segment: start alphanumeric (blocks '.', '..', '-rf', dotfiles)
# then alphanumeric / _ . -. No separators, no traversal.
_SAFE_USERNAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.\-]{0,63}$')


def valid_username(name):
    return bool(name) and bool(_SAFE_USERNAME.match(name))


def add_user(username, password):
    """Create a user + their (empty) QC data folder. Returns (ok, message)."""
    if not valid_username(username):
        return False, 'invalid username (use letters, digits, _ . - ; start alphanumeric)'
    if not password:
        return False, 'password required'
    users = load_users()
    if username in users:
        return False, 'user already exists'
    users[username] = password
    _save_users(users)
    os.makedirs(user_dir(username), exist_ok=True)
    return True, 'created'


def set_password(username, password):
    """Change an existing user's password. Returns (ok, message)."""
    if not password:
        return False, 'password required'
    users = load_users()
    if username not in users:
        return False, 'user not found'
    users[username] = password
    _save_users(users)
    return True, 'updated'


def delete_user(username, delete_data=False):
    """Remove a user's credentials (+ visibility entries). If delete_data, also
    rmtree their data folder. The 'admin' account is protected. Returns (ok, msg)."""
    if username == 'admin':
        return False, 'cannot delete the admin account'
    users = load_users()
    if username not in users:
        return False, 'user not found'
    del users[username]
    _save_users(users)
    # Drop any per-user file-visibility entries so a recreated same-name user
    # doesn't inherit stale hidden-file state.
    vis = load_visibility()
    if username in vis:
        vis.pop(username, None)
        _save_visibility(vis)
    if delete_data:
        folder = user_dir(username)
        # Confine the rmtree strictly inside USERS_DIR (defense-in-depth even
        # though valid_username already blocks traversal).
        users_root = os.path.realpath(USERS_DIR)
        real = os.path.realpath(folder)
        if os.path.isdir(real) and real.startswith(users_root + os.sep):
            shutil.rmtree(real, ignore_errors=True)
    return True, 'deleted'


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
