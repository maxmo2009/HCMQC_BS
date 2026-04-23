# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cardiac Segmentation QC Studio — A Flask-based web application for quality control review of Cardiac MRI (CMR) segmentation results. Provides real-time visualization of patient scans with both End-Diastole (ED) and End-Systole (ES) phases. Multi-user; each reviewer has their own QC datasets under `JSON/users/<username>/`.

## Running the Application

Beta binds to **port 5001**. Port 5000 belongs to a separate non-beta/production instance — **never use 5000 here**, it will collide and kill the production server.

```bash
# Install dependencies (only needed once)
pip install -r requirements.txt

# Foreground (blocks terminal until Ctrl+C)
python3 app.py
```

### Run beta + external tunnel together (background)

```bash
# 1. Flask (writes log to /tmp/beta.log)
python3 app.py > /tmp/beta.log 2>&1 &

# 2. Wait for it to accept requests
until curl -sf http://localhost:5001/health > /dev/null; do sleep 1; done

# 3. ngrok tunnel → https://hcmqcbeta.ngrok.app
ngrok http --url=hcmqcbeta.ngrok.app 5001 > /tmp/ngrok-beta.log 2>&1 &

# 4. Verify external
curl https://hcmqcbeta.ngrok.app/health
```

### Stop everything

```bash
pkill -f "python3 app.py"
pkill -f "ngrok http --url=hcmqcbeta"
# Do NOT pkill "ngrok" alone — it would also kill the production tunnel (hcmqc.ngrok.app → 5000).
```

### ngrok domains

| Instance   | Local port | ngrok URL                      |
|------------|-----------:|--------------------------------|
| beta       |       5001 | https://hcmqcbeta.ngrok.app    |
| production |       5000 | https://hcmqc.ngrok.app        |

## Datasets

Each logged-in user has their own folder at `JSON/users/<username>/` containing any number of QC dataset `.json` files. Scale depends on which file is active:
- `acdc_qc_dataset_seed42_ratio0.5_shift5.json` → 150 patients × 2 phases = 300 decisions
- `mnms2_qc_dataset_seed42_ratio0.5_shift5.json` → 360 patients × 2 phases = 720 decisions

`/api/qc_statistics` total reflects the currently active file in session (`session['active_qc_file']`).

## Testing Commands

```bash
# Health check (no auth required)
curl http://localhost:5001/health

# Authenticate: username + password (plaintext match against JSON/users.json)
curl -c cookie.txt -X POST http://localhost:5001/login \
  -d 'username=admin&password=cardiacMRI'

# Most /api/* calls also need an active dataset selected in session.
# Either the main page auto-picks the first file on login, or set it explicitly:
curl -b cookie.txt -c cookie.txt \
  http://localhost:5001/api/set_qc_file/acdc_qc_dataset_seed42_ratio0.5_shift5.json

# Authenticated API calls
curl -b cookie.txt http://localhost:5001/api/list_qc_files    # User's available datasets
curl -b cookie.txt http://localhost:5001/api/patient_list     # Patients in active dataset
curl -b cookie.txt http://localhost:5001/api/qc_statistics    # Stats for active dataset

# Save a QC decision (writes to active dataset only)
curl -b cookie.txt -X POST http://localhost:5001/api/save_qc \
  -H "Content-Type: application/json" \
  -d '{"qc_comment": "accept:Good segmentation", "phase": "ED"}'
```

## Architecture

### Key Files
- **app.py** — Flask app factory (`create_app()`) + blueprint registration + entrypoint
- **config.py** — Constants: `SECRET_KEY`, `BASE_PATH`, `PORT`, `LABEL_COLOR_MAP`, `QC_DECISIONS`, `USERS_JSON_PATH`, `USERS_DIR`, plus `user_dir()` / `user_qc_file()` path helpers
- **routes/auth.py** — `/login` (username + password form), `/logout`, `login_required` decorator (redirects HTML routes, returns 401 JSON for `/api/*`)
- **routes/pages.py** — `/` (main page, auto-picks first dataset if none active) and `/health`
- **routes/api.py** — All `/api/*` endpoints; every one guarded by `@login_required` and resolves the per-user store via `_store_or_404()`
- **services/users.py** — Loads `users.json`, authenticates credentials, lists a user's `.json` files, resolves filenames safely (blocks path traversal)
- **services/qc_store.py** — `QCStore` class (constructed per-request with an explicit file path; no singleton) + `parse_decision()` helper
- **services/nifti_loader.py** — MRI/segmentation slice loading, 3D voxel extraction, base64 encoding
- **services/patient.py** — `get_store_for_session()` (resolves session → QCStore) + `build_patient_payload()` (assembles the full patient JSON for rendering)
- **templates/index.html** — Page skeleton with top bar (user info + logout), three-panel layout, floating QC/stats panels (stats panel has the dataset dropdown), inline Jinja constants block, links to `static/css/app.css` and `static/js/app.js`
- **templates/login.html** — Login form (username + password)
- **static/css/app.css** — All UI styles
- **static/js/app.js** — All frontend logic (Three.js 3D, Chart.js, slice viewer, dataset dropdown, patient/phase controls, draggable panels)
- **JSON/users.json** — `{"<username>": "<plaintext password>", ...}`
- **JSON/users/<username>/*.json** — That user's QC dataset files (keys = patient paths, values have `ED_Comments` / `ES_Comments`)

### Authentication
- Per-user login. Credentials in `JSON/users.json` as `{username: plaintext_password}`. No hashing by user's explicit request — keep the file access-controlled at the OS level.
- Session-based auth with 3-day rolling lifetime (Flask refreshes expiry on each request).
- Session state: `username`, `active_qc_file`, `patient_index`, `phase`.
- `login_required` decorator: **all `/` and `/api/*` routes are guarded.** For `/api/*` paths it returns `401 JSON`; for HTML paths it redirects to `/login`.
- Filename validation in `services/users.resolve_qc_path()` via a strict regex (`^[A-Za-z0-9_.\-]+\.json$`) plus `os.path.isfile` check — blocks `../` traversal and symlink shenanigans.

### Critical Path Configuration
- **BASE_PATH**: in config.py, prepended to all patient paths from JSON (currently empty — JSON keys contain full absolute paths)
- **File Structure per Patient**:
  ```
  {patient_path}/
    ├── lvsa_SR_ED.nii.gz      # ED phase MRI
    ├── lvsa_SR_ES.nii.gz      # ES phase MRI
    ├── seg_lvsa_SR_ED.nii.gz  # ED segmentation
    └── seg_lvsa_SR_ES.nii.gz  # ES segmentation
  ```

### Backend API Endpoints

All `/` and `/api/*` routes require auth. Most `/api/*` routes additionally require an active dataset (`session['active_qc_file']`) and return 404 `No active dataset selected` otherwise.

```
GET  /login                      # Login page (GET=form, POST=username+password)
GET  /logout                     # Clear session and redirect to login
GET  /                           # Main page; auto-picks first dataset if none active
GET  /health                     # Health check (no auth)

GET  /api/list_qc_files          # {files: [...], active: "..."} — scans user's folder
GET  /api/set_qc_file/<filename> # Set active dataset, reset patient_index to 0
GET  /api/next_patient           # Increment session patient_index
GET  /api/prev_patient           # Decrement session patient_index
GET  /api/goto_patient/<id>      # Jump to patient by index
GET  /api/set_phase/<phase>      # Switch between 'ED' and 'ES'
GET  /api/patient_data           # Current patient's full dataset as JSON
GET  /api/patient_list           # Patients with QC decisions (ed_decision, es_decision)
GET  /api/qc_statistics          # QC decision counts and percentages
POST /api/save_qc                # {qc_comment: "<choice>:<comments>", phase: "ED/ES"}
GET  /api/download_json          # Serve the currently active dataset file
```

### Frontend Architecture

**Three-Panel Layout** (top bar is 44px, each panel is `(100vh - 44px)` square):
- **Left Panel** (`#left-panel`): MRI canvas with segmentation overlay, zoom/transparency sliders
- **Middle Panel** (`#middle-panel`): Color-coded segmentation image
- **Right Panel** (`#right-panel`): Three.js 3D InstancedMesh visualization (~50K voxels)

**Collapsible Panels** — three panels share the same minimize pattern (click the `－ / ＋` header button to toggle `.hidden` on the content wrapper + `.minimized` on the panel; state persisted to localStorage):
- **QC Control Panel** (`#floating-qc-panel`, z-index 2000, draggable): Patient dropdown, ED/ES toggle, QC decisions (accept / reject / finetune / unclassified), comments, navigation. Child ids: `#panel-content`, `#minimize-btn`.
- **Statistics Panel** (`#floating-stats-panel`, z-index 2000, draggable): Dataset dropdown + Chart.js pie chart. Child ids: `#stats-panel-content`, `#stats-minimize-btn`.
- **3D Controls/Stats Panel** (`#info`, pinned top-left of the right viewport, NOT draggable): Three.js input hints + voxel count / dimensions / spacing. Child ids: `#info-content`, `#info-minimize-btn`. Added late — the 3D panel's `#stats` block (populated by `loadBallData()` in app.js) lives inside `#info-content` and collapses with it.

**Visual design language — "radiology workstation"** (don't regress this):
- **Palette** lives in CSS variables on `:root` in `static/css/app.css`. Use the vars, never raw hex:
  - Surfaces `--bg-0` (deepest) → `--bg-3` (elevated), plus `--bg-hover`
  - Rules `--line` / `--line-mid` / `--line-strong` (always 1px, squared)
  - Text `--text-0` (primary) → `--text-3` (faint)
  - Accent cyan `--accent` / `--accent-hi` / `--accent-dim` / `--accent-bg`
  - QC semantics `--ok` / `--no` / `--warn` / `--neut` (each with a `*-dim` companion)
- **Typography**: `--font-mono` = IBM Plex Mono, loaded via Google Fonts `<link>` in both templates. All UI text is mono + uppercase with wide letter-spacing. Numbers use `font-variant-numeric: tabular-nums`.
- **Forbidden patterns** (these are exactly what the theme replaces):
  - Bootstrap hex (`#007bff / #28a745 / #dc3545 / #ffc107 / #6c757d`) or `linear-gradient(135deg, ...)` buttons
  - `border-radius` above 0, or `transform: translateY(-2px)` hover lifts
  - Emoji icons in button labels or status text (`💾 📥 ⚙ ✓ ✗ ⏳ ❌`). `▶` and `◀◀` as play/slice glyphs are intentionally kept.

**Status message convention** — `#status-message` is styled via CSS class, NOT inline background. JS sets one of: `status-accepted` / `status-rejected` / `status-success` / `status-error` / `status-info` / `status-warn` / `status-neut` (all `!important`, each painting a 2px left border + semantic text color on dark bg). When swapping class on a div that previously had inline styles, clear them explicitly: `statusDiv.style.background = ''; statusDiv.style.color = '';` — otherwise the inline wins over the class. The `#play-pause-btn` follows the same idea via a `.playing` class toggle.

**Key JS Variables** (top-level `const` declared in the inline `<script>` block of templates/index.html, visible to static/js/app.js via the shared script-scope global lexical environment):
```javascript
// Session / user context
CURRENT_USER       // Logged-in username
QC_FILES           // Array of dataset filenames available to this user
ACTIVE_QC_FILE     // Currently selected dataset filename

// Patient context (for the active dataset + current patient)
PATIENT_INDEX, PATIENT_PATH, TOTAL_PATIENTS, CURRENT_PHASE, QC_COMMENT

// Slice + 3D data for the current patient + phase
MRI_SLICES     // Base64 PNG array — MRI slices
SEG_SLICES     // Base64 RGB PNG array — segmentation slices
SEG_COORDS     // [[x,y,z], ...] voxel positions for 3D
SEG_LABELS     // [1,2,3, ...] corresponding labels (integers)
SEG_SHAPE      // [width, height, depth]
SEG_SPACING    // [x_mm, y_mm, z_mm] voxel dimensions
```

### Data Flow
1. Startup: `create_app()` registers blueprints only. No data is loaded until a request arrives — there is no startup singleton.
2. Login writes `session['username']` after matching against `JSON/users.json`.
3. First request to `/`: if `session['active_qc_file']` is empty, the page handler lists files in `JSON/users/<username>/` and auto-selects the first one. If the stored selection references a now-deleted file, it's cleared.
4. For any request that needs data, `services/patient.get_store_for_session()` resolves `(username, active_qc_file)` into a fresh `QCStore` reading that file from disk (no caching; 225–600 KB reads are cheap).
5. `build_patient_payload()` orchestrates NIfTI loading via `services/nifti_loader.py` → base64 PNG conversion + voxel coordinate extraction.
6. Frontend preloads slice images, builds Three.js scene, populates controls. Dataset dropdown lives in the stats panel and switches the active file via `/api/set_qc_file/<filename>` then reloads the page.
7. Patient/phase navigation updates session, then full page reload.
8. `POST /api/save_qc` calls `QCStore.set_comment(index, phase, comment)` which updates the in-memory dict and writes the file back to disk (`store.json_path`). Only the active dataset is modified — other files in the user's folder are untouched, and other users' folders are never touched.

### Color Mapping (consistent across backend and frontend)
```
Label 0: (0, 0, 0)       — Background
Label 1: (255, 0, 0)     — LV (Red)
Label 2: (0, 255, 0)     — RV (Green)
Label 3: (0, 136, 255)   — Myocardium (Blue)
```

### QC Comment Format
Comments in JSON follow `<choice>:<comments>`:
```json
{
  "ED_Comments": "accept:Good segmentation quality",
  "ES_Comments": "reject:Poor myocardium boundary"
}
```

## Adding a new user

Three manual steps — no CLI helper, no auto-seeding:

```bash
# 1. Add the credential (plaintext password)
# edit JSON/users.json to include a line like:
#   "alice": "their_password"

# 2. Create the user's folder
mkdir JSON/users/alice

# 3. Put one or more QC dataset .json files in there.
#    Copy an existing dataset if they should start with the same patient list:
cp JSON/users/admin/acdc_qc_dataset_seed42_ratio0.5_shift5.json JSON/users/alice/
```

No server restart needed — `users.json` is re-read on each login, and the dataset folder is scanned per request.

## Development Notes

### Important Constraints
- Patient/phase navigation requires full page reload (session-based state)
- Slice/segmentation PNGs are inlined as base64 in the JSON payload; CSS and JS assets are served from `/static/` via Flask's `url_for`
- QC decisions are mutually exclusive (enforced via JS, not backend)
- Floating panel positions persisted in localStorage (keys: `panelPosX/Y`, `statsPanelPosX/Y`, `panelMinimized`, `statsPanelMinimized`, `infoPanelMinimized`)
- NIfTI files are loaded fresh each request (no caching)
- JSON file-based storage is not safe for concurrent writes
- Segmentation labels from NIfTI files may be floats (e.g. 1.00000002) — backend rounds to int before sending to frontend
- **Flask runs with `DEBUG=False`, so templates are cached.** After editing `templates/*.html` or Jinja-injected variables you must restart Flask (`pkill -f "python3 app.py"` then start again) for changes to show up. CSS/JS under `static/` are served directly and only need a browser refresh.

### 3D Visualization Details
- Three.js with 5-point lighting setup optimized for cardiac structure visibility
- OrbitControls with damping, screen-space panning
- Separate InstancedMesh per label with MeshPhongMaterial
- Voxel spacing applied for correct physical dimensions
- Slice playback at 5 FPS default
- Label-to-color lookup uses `parseInt()` on Object.keys to match integer color map

## GitHub Configuration
- Repository: `git@github.com:maxmo2009/HCMQC_BS.git`
- Active branch: **`beta`** — holds the modular refactor + multi-user auth. `master` still has the single-user monolithic version; do not push beta changes to master without review.
- User email: `maxmo2009@gmail.com`
