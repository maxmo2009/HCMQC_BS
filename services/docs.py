"""Discovery of the markdown documents surfaced by the /docs viewer.

Each subfolder of `reports/` is a self-contained document bundle: a `.md`
file plus a sibling `imgs/` folder it references with relative `src="imgs/..."`
paths. `list_docs()` enumerates every markdown under `reports/` so the viewer
can offer a switcher; dropping a new `reports/<name>/report.md` + `imgs/` is all
it takes to add a document (no code change).
"""
import os
import re
import shutil

from werkzeug.utils import secure_filename

from config import PROJECT_ROOT

# Root holding the generated team documents (markdown + image assets).
DOCS_ROOT = os.path.join(PROJECT_ROOT, 'reports')

# Editing limits + allowlists (all edit endpoints are login-gated but writeable
# by ANY logged-in user, so confinement + validation are the real guards).
MAX_MD_BYTES = 2 * 1024 * 1024          # 2 MB of markdown text
MAX_IMG_BYTES = 12 * 1024 * 1024        # 12 MB per uploaded image
IMG_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}


def _read_title(md_path, fallback):
    """First markdown H1 heading in the file, else `fallback`."""
    try:
        with open(md_path, 'r', encoding='utf-8') as f:
            for line in f:
                s = line.strip()
                if s.startswith('# '):
                    return s[2:].strip()
                if s.startswith('#'):  # any other heading before an H1
                    break
    except OSError:
        pass
    return fallback


def list_docs():
    """Every markdown document under `reports/`, sorted by title.

    Returns a list of ``{'title', 'file', 'dir'}`` where ``file`` is the
    reports-relative path to the ``.md`` (e.g. ``hulei_acdc_discussion/report.md``)
    and ``dir`` is its reports-relative folder (``''`` for a top-level file),
    used by the viewer to resolve that doc's relative ``imgs/`` paths.
    """
    docs = []
    if not os.path.isdir(DOCS_ROOT):
        return docs
    for root, dirs, files in os.walk(DOCS_ROOT):
        # Skip hidden and image folders — they hold no documents.
        dirs[:] = sorted(d for d in dirs if not d.startswith('.') and d != 'imgs')
        for fn in sorted(files):
            if not fn.lower().endswith('.md'):
                continue
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, DOCS_ROOT)
            rel_dir = os.path.relpath(root, DOCS_ROOT)
            rel_dir = '' if rel_dir == '.' else rel_dir
            fallback = rel_dir or os.path.splitext(fn)[0]
            docs.append({
                'title': _read_title(full, fallback),
                'file': rel.replace(os.sep, '/'),
                'dir': rel_dir.replace(os.sep, '/'),
            })
    docs.sort(key=lambda d: d['title'].lower())
    return docs


# ── Editing (create / save / delete docs + image upload) ────────────────────
# Every filesystem path from the client passes through _resolve(), which
# realpath-confines it to DOCS_ROOT — the single guard that keeps writes,
# deletes, and uploads from escaping reports/.
def _resolve(rel):
    """Join `rel` under DOCS_ROOT, realpath it, and return the absolute path
    only if it stays inside DOCS_ROOT. Returns None otherwise (traversal,
    absolute path, NUL byte, …). Works for not-yet-existing paths too."""
    if not rel or not isinstance(rel, str):
        return None
    base = os.path.realpath(DOCS_ROOT)
    try:
        full = os.path.realpath(os.path.join(base, rel))
    except (ValueError, OSError):
        return None
    if full == base or full.startswith(base + os.sep):
        return full
    return None


def _slugify(name):
    """Reduce a doc title to a safe single-segment folder name."""
    s = re.sub(r'[^A-Za-z0-9_.\-]+', '_', (name or '').strip())
    return s.strip('_.')[:64]


def _doc_record(slug):
    full = os.path.join(DOCS_ROOT, slug, 'report.md')
    return {'title': _read_title(full, slug), 'file': f'{slug}/report.md', 'dir': slug}


def save_doc(file_rel, content):
    """Overwrite an existing document's markdown. `file_rel` must be a reports-
    relative path to an existing .md file. Returns (ok, message)."""
    if not isinstance(content, str):
        return False, 'content must be text'
    if len(content.encode('utf-8')) > MAX_MD_BYTES:
        return False, 'document too large'
    if not file_rel or not file_rel.lower().endswith('.md'):
        return False, 'invalid file'
    full = _resolve(file_rel)
    if full is None or not os.path.isfile(full):
        return False, 'file not found'
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content)
    return True, 'saved'


def create_doc(title):
    """Create reports/<slug>/report.md (+ empty imgs/) seeded with an H1 = title.
    The folder name is a slug of the title; collisions get a numeric suffix.
    Returns (ok, doc_record_or_message)."""
    title = ' '.join((title or '').split())   # collapse whitespace / drop newlines
    if not title:
        return False, 'title required'
    base = _slugify(title) or 'doc'
    slug, i = base, 2
    while os.path.exists(os.path.join(DOCS_ROOT, slug)):
        slug, i = f'{base}_{i}', i + 1
    folder = _resolve(slug)
    if folder is None:
        return False, 'invalid name'
    os.makedirs(os.path.join(folder, 'imgs'), exist_ok=True)
    with open(os.path.join(folder, 'report.md'), 'w', encoding='utf-8') as f:
        f.write(f'# {title}\n\n')
    return True, _doc_record(slug)


def delete_doc(dir_rel):
    """Remove a top-level document folder (must be a direct child of reports/).
    Returns (ok, message)."""
    full = _resolve(dir_rel)
    base = os.path.realpath(DOCS_ROOT)
    if full is None or full == base or not os.path.isdir(full):
        return False, 'not found'
    if os.path.dirname(full) != base:        # only direct doc folders, not nested
        return False, 'invalid folder'
    shutil.rmtree(full, ignore_errors=True)
    return True, 'deleted'


def save_doc_image(dir_rel, filename, data):
    """Save an uploaded image into reports/<dir>/imgs/. Returns (ok, rel_or_msg)
    where `rel` is the doc-relative path ('imgs/<name>') to reference in markdown."""
    folder = _resolve(dir_rel)
    if folder is None or not os.path.isdir(folder):
        return False, 'document folder not found'
    if not data:
        return False, 'empty file'
    if len(data) > MAX_IMG_BYTES:
        return False, 'image too large'
    ext = os.path.splitext(filename or '')[1].lower()
    if ext not in IMG_EXTS:
        return False, 'unsupported image type'
    safe = secure_filename(filename or '') or ('image' + ext)
    if not safe.lower().endswith(ext):       # secure_filename may strip the ext
        safe += ext
    imgs_dir = os.path.join(folder, 'imgs')
    os.makedirs(imgs_dir, exist_ok=True)
    # Avoid clobbering an existing image of the same name.
    name, base_ext = os.path.splitext(safe)
    final, i = safe, 2
    while os.path.exists(os.path.join(imgs_dir, final)):
        final, i = f'{name}_{i}{base_ext}', i + 1
    with open(os.path.join(imgs_dir, final), 'wb') as f:
        f.write(data)
    return True, f'imgs/{final}'
