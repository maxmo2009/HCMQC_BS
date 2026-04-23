import json
import os
import re

from config import USERS_JSON_PATH, USERS_DIR, user_dir


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


def list_qc_files(username):
    """Return sorted list of *.json filenames in a user's folder.

    Returns [] if the folder doesn't exist. Skips anything that isn't a plain
    .json filename (no subdirs, no traversal).
    """
    folder = user_dir(username)
    if not os.path.isdir(folder):
        return []
    return sorted(
        name for name in os.listdir(folder)
        if _SAFE_NAME.match(name) and os.path.isfile(os.path.join(folder, name))
    )


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
