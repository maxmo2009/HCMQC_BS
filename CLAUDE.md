# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cardiac Segmentation QC Studio — a Flask web app for reviewing CMR segmentation. Multi-user, per-user QC dataset files, ED/ES phase toggle, 3-panel view (MRI + segmentation + Three.js 3D voxels). README.md covers user-facing features, file layout, and the full API table; this file documents architecture and operational specifics for working on the code.

## Run / Operate

Dependencies (see `requirements.txt`): Flask 3.0.0, numpy 1.24.3, nibabel 5.3.3, Pillow 10.0.0. `pip install -r requirements.txt` for a fresh checkout — no other build step.

This host runs the **production instance** as systemd **user** services (linger enabled, survives SSH logout, auto-restarts on crash, starts on boot):

```bash
systemctl --user status   hcmqc ngrok
systemctl --user restart  hcmqc          # after editing Python
systemctl --user restart  ngrok          # almost never needed
journalctl  --user -u hcmqc -f           # tail Flask logs
journalctl  --user -u ngrok -f           # tail tunnel logs
```

Service unit files: `~/.config/systemd/user/{hcmqc,ngrok}.service`. After editing a unit: `systemctl --user daemon-reload && systemctl --user restart hcmqc`.

Public URL: <https://hcmqc.ngrok.app> → forwards to `localhost:5000`.

**Do not** run `python3 app.py` directly on this host — it will collide with the systemd-managed instance on port 5000. For ad-hoc local testing, stop the service first (`systemctl --user stop hcmqc`) or temporarily change `PORT` in `config.py`.

**Failure mode this actually caused** (worth recognising): a stray manual `python3 app.py` left running holds port 5000, so every `systemctl --user restart hcmqc` fails with `Address already in use` and enters an auto-restart loop (`systemctl --user status hcmqc` shows `activating (auto-restart)`, `MainPID` cycling). Meanwhile the **stale manual process keeps serving old code**, so `curl /health` returns `ok` and edits appear to have "no effect" no matter how many times you restart. Diagnose with `ps -eo pid,etime,cmd | grep '[a]pp.py'` (a long `etime` = the stray one) and `journalctl --user -u hcmqc -n 20` (look for `Address already in use`). Fix: `kill <stray-pid>` → `systemctl --user reset-failed hcmqc` → `systemctl --user restart hcmqc`. **When a code change seems not to take effect, verify *which* process is on :5000 before assuming the edit is wrong.**

### Port note
`config.py` sets `PORT = 5000` on this host, matched to the reserved ngrok tunnel; the README agrees on 5000 (an earlier README revision mentioned `5001` for non-production checkouts — since reconciled).

## Tests

There is no test suite. No `pytest`, no `unittest`, no fixtures. Verify changes by:
1. `systemctl --user restart hcmqc`
2. `curl -s http://localhost:5000/health` → expect `{"status":"ok",...}`
3. Hit the ngrok URL in a browser, log in, click through patients/phases, save a QC decision, confirm it persists in `JSON/users/<user>/<file>.json`

## Architecture

App-factory Flask app with three blueprints and a thin services layer. The split matters because route handlers should stay imports-thin and HTTP-shaped; all I/O and parsing lives in `services/`.

```
app.py            create_app() — registers auth_bp, pages_bp, api_bp
config.py         constants + path helpers (USERS_JSON_PATH, user_dir, ...)
routes/
  auth.py         /login, /logout; login_required + admin_required decorators
  pages.py        /  (HTML),  /docs (doc viewer/editor),  /files + /admin (admin pages),  /health
  api.py          /api/*  (JSON),  /api/fs/* (admin file browse),  /api/admin/* (admin tools),  /api/docs/* (doc list + editing)
services/
  users.py        load users.json, authenticate(), list_qc_files(), account CRUD (add/set_password/delete), admin_overview(), resolve_qc_path() (path-traversal guard)
  qc_store.py     QCStore class — loads one user's JSON file, mutates in memory, persists on save
  nifti_loader.py NIfTI → base64 PNG slices; voxel coords/labels for 3D; load_nifti_voxels() for arbitrary files
  filebrowser.py  FILES_ROOT-confined directory listing + path-traversal guard for the /files browser
  docs.py         /docs backend — list_docs() discovery + doc CRUD (save/create/delete/image), _resolve() traversal guard
  patient.py      get_store_for_session() + build_patient_payload() — orchestrator that ties session → store → loader
templates/
  index.html      Single-page shell. Initial data is Jinja-injected as top-level `const`s in a classic <script> (PATIENT_INDEX, MRI_SLICES, SEG_COORDS, ACTIVE_QC_FILE, ...) and consumed by static/js/app.js
  docs.html       Standalone doc viewer/editor — marked.js render + Toast UI WYSIWYG editing (both CDN); page-specific JS inline
  files.html      Admin File System page — file tree + up to 6 independent 3D segmentation viewers
  admin.html      Admin Tools page — account management + per-user file visibility + QC progress
  login.html      Username + password form
static/
  js/app.js       All frontend logic (Three.js scene, Chart.js stats, slice playback, panel drag, controls)
  js/files.js     File System page logic — lazy file tree + SegViewer class (one 3D scene per pane)
  js/admin.js     Admin Tools page logic (user cards, visibility toggles, account CRUD, delete modal)
  css/app.css     All UI styles (files.html and admin.html keep their page-specific styles inline)
JSON/             gitignored — credentials + per-user QC data
  users.json      {"username": "plaintext_password", ...}
  users/<user>/   *.json QC dataset files (one per dataset)
reports/          gitignored — team docs (markdown + patient-derived PNGs), served AND edited via /docs
tempCMR/          early-development sample NIfTI pair (ED only) — kept for ad-hoc loader testing, not referenced by the running app
```

### Request lifecycle

1. **Auth**: `login_required` (in `routes/auth.py`) gates everything except `/login`, `/logout`, `/health`. HTML routes redirect to `/login`; `/api/*` routes return `401 JSON` — keep this shape consistent when adding new endpoints.
2. **Per-request store**: `services.patient.get_store_for_session(session)` builds a fresh `QCStore` on every request from `(session['username'], session['active_qc_file'])`. There is no caching layer — switching users or files is just a session change. Routes that need a store should use the `_store_or_404()` helper in `routes/api.py` (or the inline check in `routes/pages.py`).
3. **Patient payload**: `build_patient_payload(store, index, phase)` returns `{patient_path, patient_info, mri_slices, seg_slices, seg_coords, seg_labels, seg_shape, seg_spacing, ...}`. Used by both `/` (Jinja-injected) and `/api/patient_data` (JSON).
4. **NIfTI loading**: `services/nifti_loader.py` re-reads the NIfTI files from disk on every request (no `@lru_cache`). For each phase change or patient change, both the MRI volume and segmentation volume are re-loaded, sliced into PNGs, base64-encoded, and either embedded in HTML or returned as JSON. This is the dominant cost of a page load — keep it in mind before adding eager pre-fetch.

### Session state (server-side, signed cookie)

- `username` — set on successful login
- `active_qc_file` — filename within `JSON/users/<username>/`; auto-picked to first file on login if user has any
- `patient_index` — int, wraps modulo `store.count()` on next/prev
- `phase` — `'ED'` or `'ES'`

Patient/phase navigation triggers a **full page reload** (the session is the source of truth, not the URL). Don't try to make these into client-side router transitions without also rethinking how Jinja-injected `const`s feed the page. Concretely the pattern in `static/js/app.js` is always `fetch('/api/...')` → on success `window.location.reload()` (prev/next patient, set_phase, goto_patient, set_qc_file). Any new navigation endpoint should follow the same shape — no client-side state to keep in sync.

### QCStore persistence

`QCStore._persist()` rewrites the entire user JSON file on every `set_comment()` call. Per-user file isolation makes concurrent collisions unlikely but **not impossible** — the same user opening two browser tabs and saving in parallel can race. There is no file lock.

### Patient paths

Two JSON schemas coexist transparently — `QCStore` handles both:

- **v1 (legacy)**: top-level keys are **absolute** filesystem paths to the patient directory (e.g. `/mnt/storage/.../patient_001`). `store.path_at(i)` and `store.resolved_path(i)` return the same string.
- **v2 (current)**: file carries a reserved `__meta__: {dataset_root, schema_version}` entry at the top; remaining keys are **relative** to `dataset_root` (just the patient directory name, e.g. `patient001`). `store.path_at(i)` returns the relative key; `store.resolved_path(i)` joins `dataset_root + key`.

Callers (`services/patient.py`, `routes/api.py`'s `patient_list` aggregation) must use **`store.resolved_path(i)`** when talking to the NIfTI loaders — that path works regardless of schema. Use `store.path_at(i)` only for `patient_data[key]` lookups (which is what `info_at`/`set_comment` already do internally).

`__meta__` is filtered out of `patient_data` on load and re-emitted **first** on `_persist()` so patient indexing (`session['patient_index']` is positional) stays stable across save/reload. Migrating an existing file from v1 → v2 is a one-shot `python3 tools/migrate_qc_to_relative.py --apply` — it computes the common path of all keys, strips the prefix, writes `__meta__`, and leaves a `.bak`. Idempotent (already-v2 files skipped). The legacy `BASE_PATH` in `config.py` is now unused — `_seg_file/_mri_file` in `nifti_loader.py` still prepend it for backward compat, but it stays `''`.

Per-patient files under `resolved_path(i)`: `lvsa_SR_{ED,ES}.nii.gz`, `seg_lvsa_SR_{ED,ES}.nii.gz`, and (when fitted) `vtks/F_<region>_<phase>.vtk`.

### Degenerate sform — use qform for any affine-based geometry

**Most dataset NIfTIs have a broken sform.** `nib.load(f).affine` (which prefers the sform) comes back with unit/degenerate scale — diagonal `[1,1,1]` (or `[0,0,0]` for savioli) — so the **z spacing is lost** (recorded 1 mm vs the true 10 mm). The real geometry survives in **`get_qform()`** and in `header.get_zooms()` (`(1.5625, 1.5625, 10.0)`). Affected: sabotaged_acdc, gpt-5.5, mnms2, savioli — basically everything **except `rulebase_fixed`**.

Consequences and where it's handled:
- **Image/segmentation rendering is safe**: `nifti_loader.py` derives `spacing` from `header.get_zooms()` (never the affine), so `SEG_SPACING` already carries the true 10 mm z, and the viewer places voxels at `(idx - center) * spacing` correctly.
- **Mesh overlay was NOT**: `mesh_loader.py` mapped mesh world-mm verts → voxel via `nib.load().affine` (the bad sform), so the mesh landed **~10× too long in z** over the segmentation. Fixed by `services.mesh_loader._corrected_affine(img)`: if the affine's column norms don't match `header.get_zooms()`, fall back to `get_qform()` (validated against zooms) — mirroring the `_affine_with_spacing` logic the meshes were fitted with, so mesh and image share one coordinate system. `rulebase_fixed` (consistent sform) is returned unchanged.
- **Any future affine-based geometry** (volumes, distances, slice localization) must route through the same qform-fallback, not `nib.load().affine` directly. Quick check: `slices × zooms[2]` should be ~80–100 mm; if you compute ~9 mm you've hit the bad sform.

### Auth model

Plaintext passwords in `JSON/users.json` (read on every login attempt — no restart needed to add users). Sessions are server-side via Flask's signed cookie, secret in `config.py:SECRET_KEY`, lifetime 3 days rolling. Accounts are managed from **Admin Tools** (see below) — add user, change password, delete user — or still by hand (edit `users.json`, `mkdir JSON/users/<name>`, drop dataset `.json` files). Passwords stay **plaintext** by design — `authenticate()` does a plaintext compare, so don't introduce hashing in one place without the other.

**Admin gating**: there is no role system — "admin" is simply `username == 'admin'`. The `admin_required` decorator (in `routes/auth.py`) enforces it: 403 JSON for `/api/*`, `abort(403)` otherwise. Two features use it: File System (`/files`, `/api/fs/*`) and Admin Tools (`/admin`, `/api/admin/*`). UI elements that should be admin-only are *also* gated in the template (e.g. the "File System" / "Admin Tools" dropdown items render as a disabled `<span class="dropdown-item disabled">` for non-admins) — but always enforce server-side too; the template check is cosmetic.

### Color map

`LABEL_COLOR_MAP` in `config.py` is the single source of truth: `0=bg`, `1=LV (red)`, `2=RV (green)`, `3=myocardium (blue)`. Both `nifti_loader.py` (server-side PNG render) and `static/js/app.js` (Three.js InstancedMesh per label) must agree — frontend has its own copy keyed by `parseInt(label)` because NIfTI labels can come back as floats (`1.00000002`) and are rounded server-side before transit.

**The label toggle UI shows the raw label *number* (1/2/3), not anatomical names.** The `LV/RV/Myocardium` names were removed from `buildLabelToggles` (app.js) and `addLegend` (files.js): they were hardcoded `1=LV/2=RV/3=Myo`, which is wrong for datasets using other conventions (ACDC is `1=RV/2=Myo/3=LV`, and conventions differ across datasets). Colors stay (from `LABEL_COLOR_MAP`); only the misleading names were dropped. Don't re-introduce anatomical names unless they're derived per-dataset.

### QC comment encoding

`{ED,ES}_Comments` fields are stored as `"<decision>:<free-text>"`. `services.qc_store.parse_decision()` extracts the decision; `QC_DECISIONS = ('accept', 'reject', 'finetune', 'unclassified')` in `config.py` is the allowed set. Empty string → `'-'`; non-matching prefix → `'unknown'`.

### Document viewer (`/docs`)

A "Useful Document" feature surfaces pre-generated markdown reports inside the app, with a **document switcher** so multiple reports can coexist. Pieces:
- **Top-bar dropdown** in `templates/index.html` (`#nav-menu`, toggled by a small block at the bottom of `app.js`) → links to `/docs`.
- **`services/docs.py`** — `list_docs()` walks `reports/` for every `.md` (skipping hidden + `imgs/` folders) and returns `{title, file, dir}` per doc: `title` is the file's first H1 (fallback: folder/filename), `file` is the reports-relative path (`hulei_acdc_discussion/report.md`), `dir` is its reports-relative folder (used to resolve that doc's `imgs/`). **Adding a document is zero-code**: drop `reports/<name>/report.md` + an `imgs/` folder; it appears in the switcher.
- **`/api/docs`** (`routes/api.py`, `@login_required`) → `{docs: [...]}` from `list_docs()`.
- **`/docs`** renders `templates/docs.html`, a standalone page that fetches `/api/docs`, populates the `#doc-select` switcher (hidden when only one doc), then `fetch`es the chosen doc's markdown and renders it **client-side with marked.js (CDN)** — deliberately no server-side markdown dependency. It rewrites that doc's relative `src="imgs/..."` → `src="/docs/file/<doc.dir>/imgs/..."` (folder-scoped — **not** a bare `/docs/file/imgs/`, since each doc has its own `imgs/`), then runs the result through **DOMPurify (CDN)** before `innerHTML`. Marked v12 dropped its built-in `sanitize` option, so without DOMPurify any `<script>` or `<img onerror>` in a report would execute in the reviewer's authenticated session. **Keep that sanitiser** if you swap the markdown source. The last-viewed doc persists per-user as `docsActiveFile::<user>` in localStorage.
- **`/docs/file/<path:filename>`** serves any document's markdown + image assets via `send_from_directory(DOCS_ROOT, ...)` (`= reports/`, from `services/docs.py`), `@login_required`. `filename` is reports-relative; `send_from_directory`'s `safe_join` blocks path traversal (verified: `../config.py` → 404).

**In-browser editing** (`templates/docs.html` toolbar — **any logged-in user**, since docs are shared). The editor is **Toast UI Editor (CDN, pinned 3.2.2, dark theme)** in WYSIWYG mode (a Markdown/WYSIWYG mode-switch tab sits at the bottom). Created on *Edit* / destroyed on *Save/Cancel* (`enterEdit`/`destroyEditor` — never stack two instances). **Image path round-trip**: stored markdown keeps doc-relative `imgs/...`, but the editor needs absolute URLs to display them — `absImgPaths()` rewrites on load, `relImgPaths()` reverses on save (covers both `src="` and `](` forms). Toolbar-insert / paste / drag-drop images all funnel through `hooks.addImageBlobHook` → `/api/docs/image` (pasted blobs get a `pasted.png` fallback name). Caveat: a WYSIWYG round-trip **normalises raw HTML** — inline `style=` attributes are stripped on save (this once ate the DOCX-derived image sizing). Two mitigations are in place: (1) docs whose markdown contains styled raw HTML are auto-opened in **Markdown mode** (`hasStyledHtml` check in `enterEdit`; the hint line warns that the WYSIWYG tab would still mangle them), and (2) the DOCX-derived doc was regenerated to be WYSIWYG-safe — images **pixel-resized on disk** to their intended display width (Pillow, from `source.docx`'s `width:…in` × 96) and referenced as plain `![](imgs/…)`; `#doc-content img` renders natural size (`width:auto; max-width:100%` — do **not** reintroduce `width:100%`, it stretches small thumbnails). Prefer this pattern (resize the file, plain markdown ref) over inline-style sizing for any future imported doc.

**User-facing image sizing** — `![alt](imgs/x.png){width=400}` (bare number → px) or `{width=50%}`. `applyImageWidth()` in `docs.html` rewrites this to `<img src=… style="width:…">` on the raw markdown **before** `marked.parse()` (so the `src="imgs/` → login-gated path rewrite still matches, and DOMPurify keeps the inline width). Because the `{width=…}` marker is plain text that a WYSIWYG round-trip would mangle, docs containing it are **auto-opened in Markdown mode** — the `enterEdit` gate is `needsMd = hasStyledHtml || hasImgWidth` (regex `/\]\([^)\s]+\)\{\s*width\s*=/`). Tell users to size images from the **Markdown** tab; leaving `{width=…}` off renders the image at natural size.

Four `@login_required` endpoints in `routes/api.py`, all backed by `services/docs.py`:
- **`/api/docs/save`** (POST `{file, content}`) → `save_doc()`: overwrites an **existing** reports-relative `.md` (≤ `MAX_MD_BYTES` = 2 MB).
- **`/api/docs/create`** (POST `{title}`) → `create_doc()`: makes `reports/<slug>/report.md` (seeded with `# <title>`) + empty `imgs/`. Folder = `_slugify(title)` (non-`[A-Za-z0-9_.-]` → `_`); a non-ASCII title like `分割判断` slugs to empty → falls back to `doc`, then `doc_2`… on collision. The H1 carries the real (possibly unicode) title, so the dropdown still shows it.
- **`/api/docs/delete`** (POST `{dir}`) → `delete_doc()`: `rmtree`s a doc folder — only a **direct child** of `reports/` (`os.path.dirname(full) == DOCS_ROOT`).
- **`/api/docs/image`** (POST multipart `dir`, `image`) → `save_doc_image()`: writes into `<dir>/imgs/`, allowlisted raster ext (`IMG_EXTS`, no SVG), ≤ `MAX_IMG_BYTES` = 12 MB, `secure_filename` + numeric-suffix de-dupe; returns `imgs/<name>` for the editor to insert as `![](…)`.

**The single guard** for all four is `services.docs._resolve(rel)` — `realpath`-confines a client-supplied reports-relative path to `DOCS_ROOT` (rejects `..`, absolute paths, NUL). **Route every filesystem path from an edit request through `_resolve()`.** Stored markdown is still rendered through DOMPurify, so a user typing `<script>`/`<img onerror>` into the editor is neutralised at render time for every viewer — the sanitiser is load-bearing now that content is user-writable, not just generated.

Docs are shown to **every logged-in user** (not scoped per-user) and are equally writable by every logged-in user — there is no per-doc ownership and no version history (a Save overwrites; a Delete is final). Content arrives two ways: generated **outside the app** (ad-hoc scripts / pandoc DOCX conversion) and dropped into `reports/`, or created/edited **in the page** via the toolbar. `reports/` is gitignored because the images are patient-derived.

### 3D per-category visibility

`createPointCloud()` in `app.js` stores each label's `THREE.InstancedMesh` in the module-level `labelMeshes` map, and `buildLabelToggles()` renders one checkbox per *present* label into `#label-toggles` (in the 3D "Controls" panel). Toggling a box sets `mesh.visible` — show/hide is purely client-side, no reload.

The state persists in `localStorage` so it survives the page reload that every patient/phase change triggers. The key is **scoped by user**: `LABEL_VIS_KEY = 'labelVisibility::' + CURRENT_USER`. Without this scope, a shared workstation leaks User A's hidden-myocardium preference into User B's session (localStorage is origin-scoped, not session-scoped). When adding new global preferences, follow the same `'<feature>::' + CURRENT_USER` pattern.

A separate **3D segmentation-voxel opacity** slider (`#seg-opacity`, in the same `#label-toggles` block as the show/hide checkboxes) mirrors the mesh-overlay opacity: `getSegOpacity()`/`applySegOpacity()` set each `labelMeshes[*].material.opacity` (default 1.0 = solid; `transparent`/`depthWrite` only flip below 100% to avoid sort artifacts), persisted per-user in `VIEWER_PREFS_KEY` under `seg3dOpacity`. `createPointCloud()` reads it for the initial material and `buildLabelToggles()` seeds the slider, so it survives the patient/phase reload without a `restoreViewerPrefs()` entry.

**Other viewer preferences** — Show Overlay, overlay transparency, zoom, and the **Hide MRI panel** toggle — share one per-user JSON object under `VIEWER_PREFS_KEY = 'viewerPrefs::' + CURRENT_USER`, restored by `restoreViewerPrefs()` **before the first render** so the initial draw already reflects them (it only touches DOM/state, never the not-yet-initialised 3D). *Hide MRI panel* (`hideMriPanel`, a checkbox under the Control Panel's "View" section) sets `#left-panel` to `display:none`; the flex `#main-container` then re-flows the middle (segmentation) + right (3D) panels wider, and the handler calls `onWindowResize()` so the 3D canvas re-fits.

### File System (`/files`, admin-only)

An admin-only NIfTI browser + multi-pane 3D viewer, reached via the top-bar dropdown. Two API endpoints (both `@admin_required`, in `routes/api.py`):
- **`/api/fs/list?path=<rel>`** → `services.filebrowser.list_dir()` returns subdirectories + NIfTI files (dotfiles and non-NIfTI files hidden), confined to `FILES_ROOT` (`config.py`, currently `/home/maxmo2009`). `filebrowser.resolve()` is the path-traversal guard — it `realpath`s the joined path, catches `ValueError`/`OSError` (e.g. NUL-byte inputs), and rejects anything outside `FILES_ROOT`. **Always route filesystem paths through `resolve()`.** `list_dir` is also per-entry tolerant: one unreadable file/dir is skipped rather than nuking the whole listing.
- **`/api/fs/nifti?path=<rel>`** → `nifti_loader.load_nifti_voxels()` returns voxel `coords/labels/shape/spacing/labels_present`. It guards against non-segmentation and oversized input, returning HTTP 422 with an `error` key. The full error vocabulary (also handled in `files.js:describeError`): `not_found`, `not_3d`, `too_large` (header-only size gate runs **before** `get_fdata` so a misclicked intensity volume can't OOM the server — see `MAX_VOXELS_BEFORE_LOAD`), `empty`, `not_segmentation` (counts **nonzero** unique labels > `MAX_SEGMENTATION_LABELS=50`, not including background), and `load_failed` (corrupt/truncated NIfTI — `fs_nifti` wraps the loader in `try/except` so a `nib.ImageFileError` becomes a structured 422, never a 500 HTML page). The loader also normalises NaN voxels (`np.nan_to_num`) before rounding, so a NaN-rich float volume can't silently leak `INT_MIN` "phantom labels" via `np.round(NaN).astype(int)`. **`spacing` is paired with the axes that survive `np.squeeze`** (tracked via `kept_axes`), so a 4D NIfTI like `(X, Y, 1, T)` renders with the correct physical scale on the kept axes — not the original-axis zooms.

Frontend (`static/js/files.js`): lazy file tree (folders expand on click, NIfTI files open on click). Each opened file gets a `SegViewer` instance — an **independent** scene/camera/renderer/OrbitControls + per-pane `ResizeObserver` and animation loop (mirrors `app.js`'s 3D setup; auto-frames the camera to the volume's bounding sphere). Max **6 panes**; grid columns adapt to pane count. Each pane has a "Visibility" checkbox per present label (per-pane `mesh.visible`). `files.html` carries its own page-specific CSS inline (it does not share the index layout).

Things to preserve when editing `files.js`:
- **All filename/path interpolation into `innerHTML` must go through `esc()`.** `entry.name` and `entry.path` come from `os.listdir` and are filesystem-controlled — a file named `<img onerror=...>.nii.gz` would inject HTML into the admin session. There are currently three sites: `openFile` (pane header), `makeEntryNode` dir row, and `makeEntryNode` file row.
- **`openFile` uses `AbortController`; `closePane` aborts and the `.then` re-checks `openByPath.get(path) === pane` before constructing the viewer.** This prevents a SegViewer with a runaway RAF loop being instantiated on a detached DOM node when the user closes the pane mid-load.
- **`SegViewer.dispose()` must call `this.controls.dispose()`** before disposing the renderer. OrbitControls registers ~8 DOM listeners on the canvas; without dispose those listeners keep the whole scene graph alive across pane open/close cycles.

### Admin Tools (`/admin`, admin-only)

A second admin-only page (Menu → *Admin Tools*; disabled `<span>` for non-admins, exactly like File System). Routes: `/admin` in `routes/pages.py`, `/api/admin/*` in `routes/api.py` — all `@admin_required`. Frontend: `templates/admin.html` + `static/js/admin.js` (all filename/user interpolation goes through `esc()`).

- **`/api/admin/overview`** → `services.users.admin_overview()`: every user + their QC files, each file carrying `visible` (bool) and `progress` (`{total, ed, es}`).
- **`/api/admin/visibility`** (POST `{username, filename, visible}`) → `set_file_visibility()`.
- **`/api/admin/user`** (POST `{username, password}`) → `add_user()`: creates the credential + an empty `JSON/users/<name>/` folder.
- **`/api/admin/user/password`** (POST `{username, password}`) → `set_password()`.
- **`/api/admin/user/delete`** (POST `{username, delete_data}`) → `delete_user()`: removes the credential + its `file_visibility.json` entries; if `delete_data` is true, also `shutil.rmtree`s the data folder (confined to `USERS_DIR`). The **`admin` account is protected** (can't be deleted).

**Account management** — usernames double as folder names, so `valid_username()` (`services/users.py`) requires a single safe path segment (`^[A-Za-z0-9][A-Za-z0-9_.\-]{0,63}$` — must start alphanumeric, blocking `.`/`..`/dotfiles/traversal). `_save_users()` rewrites `users.json` (indent=2, `ensure_ascii=False`). Frontend: the `#acct-bar` add-user form + per-card *Change Password* / *Delete* buttons in `static/js/admin.js` (page UI is English). **Delete uses a confirm modal** (`#del-modal`) with a *also delete data folder* checkbox → `delete_data` in the POST. Changing a user's password does **not** invalidate their existing session (sessions store only the username, not the password).

**Per-user file visibility** — stored in `JSON/file_visibility.json` as `{username: [hidden_filename, ...]}` (gitignored, like all of `JSON/`). `list_qc_files(username)` filters these out for non-admins, so a hidden file vanishes from that user's dataset dropdown (the file on disk is untouched). **Admin is never filtered** (`username == 'admin'` short-circuits) and can't hide its own files. `_list_files_raw()` is the unfiltered variant the admin overview uses.

**QC progress** — `_file_progress()` counts a phase as done only when its comment is a *real reviewer decision*: `parse_decision(comment) in QC_DECISIONS`. A bare `CardiacAgent: …` note parses to `'unknown'` and is **not** counted, so agent-fixed datasets don't show false 100% progress. `static/js/admin.js` renders `ED x/N · ES y/N` per file plus a **progress bar** (fill = combined `(ed+es)/(total*2)`, turns `--ok` green when complete).

### Top-bar dropdown & floating panels

The **Menu** dropdown (`#nav-menu`, toggled + wired in `app.js`) holds: *Useful Document* (`/docs`), *File System* (`/files`), *Admin Tools* (`/admin`) — the latter two admin-only, rendered as disabled `<span>`s for non-admins — and **⟲ Reset Panel Positions**.

Two panels are drag-positioned in `app.js` and persisted to `localStorage`: the Control Panel (`#floating-qc-panel`, anchored **top-left** at `top:62 left:440` — just right of QC Statistics — dragged via CSS `transform: translate`, keys `panelPosX/Y`) and the QC Statistics panel (`#floating-stats-panel`, anchored top-left, dragged via inline `left/top`, keys `statsPanelPosX/Y`); each also persists a `*Minimized` flag (`panelMinimized`, `statsPanelMinimized`, `infoPanelMinimized` for the 3D Controls). `resetPanelPositions()` clears positions AND the minimized flags AND restores the in-DOM minimize state (removes `.minimized`/`.hidden`, flips the toggle text from `＋` back to `－`) — without that last step, a panel minimized + dragged off-screen comes back as an unfindable tiny strip. The 3D `#info` ("Controls") panel is collapsible but **fixed-position** (not draggable, so it can't be lost).

**Both floating panels are uniformly scalable** via a bottom-right resize handle (`#panel-resize-handle` / `#stats-resize-handle`): drag to set a `scale()` (clamped 0.6–1.8), persisted per-user as `panelScale::<user>` / `statsPanelScale::<user>`. Both use `transform-origin: top left` so the handle follows the cursor (top-left fixed, panel grows toward bottom-right) — which is *why* the Control Panel was re-anchored from its old bottom-right corner to top-left: it needs bottom-right room to grow. A one-time `panelAnchorTL` flag drops the now-meaningless old `panelPosX/Y` offsets on first load after the move. The Control Panel's transform is thus `translate(x,y) scale(s)` (drag + zoom combined); the Stats panel drags via `left/top`, leaving `transform` free for a plain `scale(s)`. Resize handles `stopPropagation` on mousedown so they don't start a panel drag, and are also listed in `dragStart`'s skip set.

The Control Panel's drag handler (`dragStart` in `app.js`) skips elements where `closest('label')` matches, in addition to button/input/textarea/select. This is required for the `<span class="kbd">1/2/S</span>` hint chips inside Accept/Reject labels — without the label check, clicking the chip triggers `preventDefault()` on `mousedown` and suppresses the label-to-checkbox click activation.

## Editing tips

- **Backend Python change** → `systemctl --user restart hcmqc`. Flask runs with `DEBUG=False`, so there's no auto-reload.
- **Template change** (`templates/*.html`) → restart Flask (templates are cached when `DEBUG=False`). Note `docs.html` carries ALL its page CSS **and JS** inline (including the whole editor logic), and `files.html`/`admin.html` carry their page CSS inline — changing that "frontend" code is a template change and needs the restart (their JS in `static/` does not).
- **Static change** (`static/js/app.js`, `static/css/app.css`) → no restart, just hard-refresh the browser (Ctrl-Shift-R) — Flask serves static files directly.
- **Injecting server values into `index.html`** → they become top-level `const`s in the inline `<script>` that `app.js` reads. **String values MUST use `| tojson`** (e.g. `const QC_COMMENT = {{ qc_comment | tojson }};`), never bare `"{{ ... }}"`. QC comments can contain newlines or quotes (e.g. multi-line CardiacAgent notes appended after the decision); injected raw, a newline/quote breaks the entire inline script → every `const` is undefined → `app.js` throws → the page silently fails to load (this exact bug froze a reviewer's app). Arrays/objects are pre-`json.dumps`'d in `routes/pages.py` and injected with `|safe`.
- **Adding a new `/api/*` route** → put it in `routes/api.py`, decorate with `@login_required` (or `@admin_required` for admin-only), use `_store_or_404()` if it needs the active dataset. Keep business logic in `services/`. Any client-supplied filesystem path must go through the matching confinement guard: `services.filebrowser.resolve()` (FILES_ROOT), `services.docs._resolve()` (reports/), or `services.users.valid_username()`/`resolve_qc_path()` (JSON/users/).
- **`JSON/` is fully gitignored** — never commit credentials or patient data. Verify with `git check-ignore -v JSON/whatever`.
- **Keyboard shortcuts** live in a single `keydown` listener at the bottom of `static/js/app.js`: `1`=accept, `2`=reject, `S`=save, `←`/`→`=prev/next patient. Suppressed when focus is in an `<input>`/`<textarea>`/**`<select>`** (without the select check, typing `S` to typeahead-jump in the dataset dropdown silently saves QC, and arrow keys would reload the page) or any modifier (Ctrl/Meta/Alt) is held, so `Ctrl+S` still does the browser default. Hint chips render via `<span class="kbd">` in `templates/index.html`, styled in `static/css/app.css`.

## GitHub

- Repo: `git@github.com:maxmo2009/HCMQC_BS.git`
- **`master` is the active branch.** Recent work (File System feature, the 15-fix security/correctness pass, QC store v2 migration, README refresh) was committed and pushed straight to `master`. `beta` has fallen several commits behind and is **not** currently tracking `master` — despite an earlier "experimental work on beta first" convention, current practice is `master` directly. If you resume the beta workflow, fast-forward `beta` to `master` first.
