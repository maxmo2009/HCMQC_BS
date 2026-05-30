import os

from config import FILES_ROOT

_ROOT = os.path.realpath(FILES_ROOT)


def is_nifti(name):
    n = name.lower()
    return n.endswith('.nii') or n.endswith('.nii.gz')


def resolve(rel_path):
    """Resolve a path given relative to FILES_ROOT.

    Returns the absolute real path, or None if it escapes FILES_ROOT.
    `realpath` collapses `..` and symlinks, so traversal attempts are caught.
    A NUL byte (or any other malformed path) makes realpath raise ValueError —
    treat that as 'invalid path' rather than letting it become a 500.
    """
    rel_path = (rel_path or '').strip().lstrip('/')
    try:
        target = os.path.realpath(os.path.join(_ROOT, rel_path))
    except (ValueError, OSError):
        return None
    if target == _ROOT or target.startswith(_ROOT + os.sep):
        return target
    return None


def rel_of(abs_path):
    """Path relative to FILES_ROOT using forward slashes; '' for the root itself."""
    rel = os.path.relpath(abs_path, _ROOT)
    return '' if rel == '.' else rel.replace(os.sep, '/')


def list_dir(rel_path):
    """List subdirectories and NIfTI files under rel_path (dotfiles skipped).

    Returns {path, parent, entries:[{name,type,path[,size]}]} or None if the
    path is invalid / not a directory. Dirs first, then files, case-insensitive.
    """
    abs_path = resolve(rel_path)
    if abs_path is None or not os.path.isdir(abs_path):
        return None
    try:
        names = sorted(os.listdir(abs_path), key=str.lower)
    except OSError:
        return None
    dirs, files = [], []
    for name in names:
        if name.startswith('.'):
            continue
        full = os.path.join(abs_path, name)
        # Per-entry try/except: one unreadable file shouldn't hide its siblings.
        try:
            if os.path.isdir(full):
                dirs.append({'name': name, 'type': 'dir', 'path': rel_of(full)})
            elif os.path.isfile(full) and is_nifti(name):
                files.append({
                    'name': name, 'type': 'file', 'path': rel_of(full),
                    'size': os.path.getsize(full),
                })
        except OSError:
            continue
    return {
        'path': rel_of(abs_path),
        'parent': None if abs_path == _ROOT else rel_of(os.path.dirname(abs_path)),
        'entries': dirs + files,
    }
