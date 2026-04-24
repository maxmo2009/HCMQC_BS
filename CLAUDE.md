# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cardiac Segmentation QC Studio — a Flask web app for reviewing CMR segmentation. Multi-user, per-user QC dataset files, ED/ES phase toggle, 3-panel view (MRI + segmentation + Three.js 3D voxels). README.md covers user-facing features, file layout, and the full API table; this file documents architecture and operational specifics for working on the code.

## Run / Operate

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

### Port note
`config.py` sets `PORT = 5000` on this host. The README mentions `5001` — that's for non-production checkouts; on this host it was switched to 5000 to match the reserved ngrok tunnel.

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
  auth.py         /login, /logout, login_required decorator
  pages.py        /  (HTML)  and /health
  api.py          /api/*  (JSON)
services/
  users.py        load users.json, authenticate(), list_qc_files(), resolve_qc_path() (path-traversal guard)
  qc_store.py     QCStore class — loads one user's JSON file, mutates in memory, persists on save
  nifti_loader.py NIfTI → base64 PNG slices + non-zero voxel coords/labels for 3D
  patient.py      get_store_for_session() + build_patient_payload() — orchestrator that ties session → store → loader
templates/
  index.html      Single-page shell. Initial data is Jinja-injected as top-level `const`s in a classic <script> (PATIENT_INDEX, MRI_SLICES, SEG_COORDS, ACTIVE_QC_FILE, ...) and consumed by static/js/app.js
  login.html      Username + password form
static/
  js/app.js       All frontend logic (Three.js scene, Chart.js stats, slice playback, panel drag, controls)
  css/app.css     All UI styles
JSON/             gitignored — credentials + per-user QC data
  users.json      {"username": "plaintext_password", ...}
  users/<user>/   *.json QC dataset files (one per dataset)
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

Patient/phase navigation triggers a **full page reload** (the session is the source of truth, not the URL). Don't try to make these into client-side router transitions without also rethinking how Jinja-injected `const`s feed the page.

### QCStore persistence

`QCStore._persist()` rewrites the entire user JSON file on every `set_comment()` call. Per-user file isolation makes concurrent collisions unlikely but **not impossible** — the same user opening two browser tabs and saving in parallel can race. There is no file lock.

### Patient paths

Keys in the per-user JSON are **full absolute filesystem paths** to the patient directory (e.g. `/mnt/storage/.../patient_001`). `BASE_PATH` in `config.py` is intentionally empty — it's prepended to the JSON key before `os.path.join`, so any value other than `''` will break path resolution unless the JSON keys are made relative. Per-patient files (`lvsa_SR_{ED,ES}.nii.gz`, `seg_lvsa_SR_{ED,ES}.nii.gz`) must exist under that path.

### Auth model

Plaintext passwords in `JSON/users.json` (read on every login attempt — no restart needed to add users). Sessions are server-side via Flask's signed cookie, secret in `config.py:SECRET_KEY`, lifetime 3 days rolling. There is **no** registration UI — adding a user is a manual three-step process: edit `users.json`, `mkdir JSON/users/<name>`, drop dataset `.json` files in that folder. See README "Adding Users".

### Color map

`LABEL_COLOR_MAP` in `config.py` is the single source of truth: `0=bg`, `1=LV (red)`, `2=RV (green)`, `3=myocardium (blue)`. Both `nifti_loader.py` (server-side PNG render) and `static/js/app.js` (Three.js InstancedMesh per label) must agree — frontend has its own copy keyed by `parseInt(label)` because NIfTI labels can come back as floats (`1.00000002`) and are rounded server-side before transit.

### QC comment encoding

`{ED,ES}_Comments` fields are stored as `"<decision>:<free-text>"`. `services.qc_store.parse_decision()` extracts the decision; `QC_DECISIONS = ('accept', 'reject', 'finetune', 'unclassified')` in `config.py` is the allowed set. Empty string → `'-'`; non-matching prefix → `'unknown'`.

## Editing tips

- **Backend Python change** → `systemctl --user restart hcmqc`. Flask runs with `DEBUG=False`, so there's no auto-reload.
- **Template change** (`templates/*.html`) → restart Flask (templates are cached when `DEBUG=False`).
- **Static change** (`static/js/app.js`, `static/css/app.css`) → no restart, just hard-refresh the browser (Ctrl-Shift-R) — Flask serves static files directly.
- **Adding a new `/api/*` route** → put it in `routes/api.py`, decorate with `@login_required`, use `_store_or_404()` if it needs the active dataset. Keep business logic in `services/`.
- **`JSON/` is fully gitignored** — never commit credentials or patient data. Verify with `git check-ignore -v JSON/whatever`.

## GitHub

- Repo: `git@github.com:maxmo2009/HCMQC_BS.git`
- `master` and `beta` branches are currently in sync (master was fast-forwarded to beta). New experimental work goes on `beta` first.
