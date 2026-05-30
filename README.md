# Cardiac Segmentation QC Studio

A multi-user web application for reviewing cardiac MRI (CMR) segmentation results. Reviewers step through patients and both cardiac phases (End-Diastole / End-Systole), score each segmentation (accept / reject / fine-tune / unclassified), and persist decisions to their own JSON file.

![Lab Logo](https://images.squarespace-cdn.com/content/v1/611bce9f0ec5ff43949b98ea/068036ac-5a6f-4da8-869f-520764bdaaaa/still_v023_frame_0103_photoshop_layer_logo_LMS.png?format=300w)

## Features

### Multi-User
- Username + password login (credentials in `JSON/users.json`)
- Each reviewer's QC annotations are fully isolated under `JSON/users/<username>/`
- Session-based auth with 3-day rolling lifetime

### Dataset Management
- Each user can maintain any number of QC dataset files side-by-side
- A dataset dropdown in the stats panel switches the active file without re-login
- Dataset format: top-level dict keyed by patient path, values hold `ED_Comments` / `ES_Comments` (plus an optional `__meta__` block — see [Data Format](#data-format))

### 3-Panel Visualization (per cardiac phase)
- **Left panel** — MRI slices with optional color-coded segmentation overlay (zoom + transparency sliders)
- **Middle panel** — Color-coded segmentation slices
- **Right panel** — Three.js 3D InstancedMesh rendering (~50K voxels) with OrbitControls (rotate / pan / zoom)

### QC Decisions
- Four mutually exclusive decisions: **Accept ✓**, **Reject ✗**, **Fine-tune ⚙**, **Unclassified ?**
- Free-text reviewer comments per patient + phase
- Chart.js pie chart of decision distribution for the active dataset

### Slice Navigation
- Auto-play at 5 FPS, plus manual prev/next
- All three panels stay synchronized on the same slice

### Medical Imaging Support
- Reads NIfTI (`.nii.gz`) for both MRI and segmentation
- Voxel spacing taken from NIfTI header for correct physical dimensions
- Multi-label color map: label 1 = LV (red), 2 = RV (green), 3 = myocardium (blue)

### Keyboard Shortcuts
- `1` accept · `2` reject · `S` save · `←` / `→` previous / next patient
- Automatically suppressed while typing in a text field or a dropdown, so they never fire by accident

### 3D Category Toggles
- Show / hide each label (LV / RV / myocardium) independently in the 3D view
- The choice is remembered **per user** and survives patient / phase changes

### Floating Panels
- The QC controls and statistics panels can be dragged anywhere and minimized
- Positions persist per browser; **Menu → ⟲ Reset Panel Positions** recovers a panel dragged off-screen

### Useful Document (`/docs`)
- In-app viewer for a pre-generated team report (Markdown), reached from the top-bar **Menu**
- Rendered client-side and sanitized with DOMPurify before display

### File System (admin only)
- The `admin` user gets a **File System** browser at `/files`, reached from the top-bar **Menu**
- Walk the server's NIfTI tree and open up to **6 segmentations side-by-side**, each in its own interactive 3D viewer
- Non-segmentation, oversized, or corrupt files are rejected with a clear message instead of freezing the browser

## Installation

```bash
git clone git@github.com:maxmo2009/HCMQC_BS.git
cd HCMQC_BS
pip install -r requirements.txt
```

## Running

```bash
python3 app.py
```

Server binds to **http://localhost:5000** (`DEBUG=False`). On the production host the app runs as a systemd user service exposed via ngrok at <https://hcmqc.ngrok.app> — **don't** run `python3 app.py` there, it collides with the managed instance on port 5000.

See `CLAUDE.md` for the systemd unit layout and ngrok tunnel recipes.

## Adding Users

Three manual steps — no CLI helper, no auto-seeding:

1. Edit `JSON/users.json`:
   ```json
   {
     "admin": "cardiacMRI",
     "alice": "alicepassword"
   }
   ```
2. Create the folder: `mkdir JSON/users/alice`
3. Drop one or more QC dataset `.json` files into that folder

No server restart needed — users.json is re-read on each login and the folder is scanned per request.

> **Admin:** the account literally named `admin` is the only privileged user — it alone can open the File System browser (`/files` and the `/api/fs/*` endpoints). There is no other role system; everyone else sees that menu item disabled.

## Expected File Layout (per patient, on disk)

```
{patient_path}/
├── lvsa_SR_ED.nii.gz      # ED-phase MRI
├── lvsa_SR_ES.nii.gz      # ES-phase MRI
├── seg_lvsa_SR_ED.nii.gz  # ED-phase segmentation
└── seg_lvsa_SR_ES.nii.gz  # ES-phase segmentation
```

Each dataset JSON references patients by directory. Two schemas are supported transparently: **legacy** files key patients by absolute path; **current** files carry a `__meta__.dataset_root` and key patients by a path *relative* to it, so the whole dataset can be relocated by editing one line. Convert legacy files in place with `python3 tools/migrate_qc_to_relative.py --apply` (idempotent, writes a `.bak` per file).

## Tech Stack

### Backend (modular Flask app)
- Flask 3.0.0 — app factory + blueprints (`routes/auth.py`, `routes/pages.py`, `routes/api.py`)
- nibabel 5.3.3 — NIfTI parsing
- numpy 1.24.3 — array ops
- Pillow 10.0.0 — slice → PNG

### Frontend (vanilla, no bundler)
- Three.js r128 — WebGL 3D scene with 5-point lighting
- OrbitControls — camera interaction
- Chart.js 4.4.0 — statistics pie chart
- HTML5 Canvas — MRI + overlay compositing
- marked.js 12 + DOMPurify 3 — client-side Markdown render + sanitize for `/docs`

All frontend libraries load from CDNs; there is no build step.

## Project Structure

```
HCMQC_BS/
├── app.py                      # Flask app factory (create_app) + entrypoint
├── config.py                   # Constants + path helpers (USERS_JSON_PATH, FILES_ROOT, ...)
├── requirements.txt
├── CLAUDE.md                   # Architecture notes + operational recipes for Claude Code
├── README.md                   # This file
│
├── routes/                     # Flask blueprints
│   ├── auth.py                 #   /login, /logout, login_required + admin_required
│   ├── pages.py                #   /, /docs, /files (admin), /health
│   └── api.py                  #   /api/* (JSON) + /api/fs/* (admin file browse + nifti)
│
├── services/                   # Business logic (no Flask dependency)
│   ├── users.py                #   auth + per-user dataset file listing + path-traversal guard
│   ├── qc_store.py             #   QCStore (v1/v2 schema, JSON-backed) + parse_decision
│   ├── nifti_loader.py         #   MRI/seg slices → base64 PNG, 3D voxels, load_nifti_voxels
│   ├── filebrowser.py          #   FILES_ROOT-confined listing + path-traversal guard (/files)
│   └── patient.py              #   get_store_for_session + build_patient_payload orchestrator
│
├── templates/
│   ├── index.html              # Main page (3 panels + floating QC/stats panels + Menu)
│   ├── docs.html               # Useful Document viewer (client-side Markdown)
│   ├── files.html              # File System page (admin NIfTI browser + 3D panes)
│   └── login.html              # Username + password form
│
├── static/
│   ├── css/app.css             # All UI styles
│   ├── js/app.js               # Main-page frontend (Three.js, Chart.js, controls, shortcuts)
│   ├── js/files.js             # File System page (lazy tree + per-pane 3D SegViewer)
│   ├── left_placeholder.png
│   └── right_placeholder.png
│
├── tools/
│   └── migrate_qc_to_relative.py   # One-shot v1→v2 dataset migration (idempotent, .bak)
│
├── reports/                    # gitignored — team docs served read-only by /docs
│
└── JSON/                       # gitignored — contains credentials + patient data
    ├── users.json              #   {"username": "plaintext_password", ...}
    └── users/
        └── <username>/
            └── *.json           #     Per-user QC dataset files
```

Nothing under `JSON/` is committed — both credentials and patient data stay local.

## API Endpoints

All routes except `/health` require auth (`/api/*` returns `401 JSON`; HTML pages redirect to `/login`). Most `/api/*` routes also require an active dataset (set automatically on first visit, or via `/api/set_qc_file`). Routes marked **admin** require the `admin` user (`403` otherwise).

| Method | Path | Notes |
|---|---|---|
| GET | `/login` | Username + password form |
| GET | `/logout` | Clears session |
| GET | `/` | Main page |
| GET | `/docs` | Useful Document viewer |
| GET | `/docs/file/<path>` | Serve the report Markdown + image assets |
| GET | `/files` | **Admin** — File System page |
| GET | `/health` | Health check (no auth) |
| GET | `/api/list_qc_files` | Files available to this user |
| GET | `/api/set_qc_file/<filename>` | Switch active dataset |
| GET | `/api/set_phase/<phase>` | `ED` or `ES` |
| GET | `/api/next_patient` / `/api/prev_patient` / `/api/goto_patient/<id>` | Navigation |
| GET | `/api/patient_data` | Current patient payload (slices + voxels) |
| GET | `/api/patient_list` | Patients in active dataset + per-phase decisions |
| GET | `/api/qc_statistics` | Counts + percentages |
| POST | `/api/save_qc` | Persist one decision + comment |
| GET | `/api/download_json` | Download the active dataset |
| GET | `/api/fs/list?path=` | **Admin** — list dirs + NIfTI files under `FILES_ROOT` |
| GET | `/api/fs/nifti?path=` | **Admin** — load one NIfTI's voxels for the 3D viewer |

## Data Format

### NIfTI inputs
- MRI: grayscale intensity values
- Segmentation: integer labels (0 = background, 1 = LV, 2 = RV, 3 = myocardium)
- Voxel spacing read from NIfTI header (typically ~1.25 × 1.25 × 8.0 mm)

### QC comment encoding
Each saved decision is encoded as `"<decision>:<free-text>"` in the `ED_Comments` or `ES_Comments` field:
```json
{
  "ED_Comments": "accept:Good segmentation quality",
  "ES_Comments": "reject:Poor myocardium boundary"
}
```

### Dataset schema (v1 / v2)
The QC store reads two layouts interchangeably:

**v1 (legacy)** — patient keys are absolute paths:
```json
{
  "/abs/path/to/patient001": { "ED_Comments": "...", "ES_Comments": "..." }
}
```

**v2 (current)** — a `__meta__` header lifts the shared prefix; keys become relative:
```json
{
  "__meta__": { "schema_version": 2, "dataset_root": "/abs/path/to/dataset" },
  "patient001": { "ED_Comments": "...", "ES_Comments": "..." }
}
```
Relocating the dataset is then a one-line `dataset_root` edit. Migrate legacy files with `python3 tools/migrate_qc_to_relative.py --apply`.

### Full patient entry
Every patient value is an object. **The app only reads and writes the two `*_Comments` strings**; the optional `ED` / `ES` objects hold per-phase metadata specific to how the dataset was generated, and are passed straight through to the page without modification.

```json
{
  "patient001": {
    "ED": { },
    "ES": { },
    "ED_Comments": "reject:apex incomplete, a few slices misaligned",
    "ES_Comments": "accept:looks good"
  }
}
```

| Field | Written by | Meaning |
|---|---|---|
| `ED` / `ES` | dataset pipeline | Optional per-phase metadata, specific to the dataset; shown for context, never modified by the app |
| `ED_Comments` / `ES_Comments` | **the app** | Reviewer decision `"<decision>:<free-text>"`; the only fields the app writes, absent until the reviewer's first save |

## Development Notes

- Backend logic is split across `routes/` and `services/`; `config.py` centralizes constants
- CSS and JS live under `static/` (no bundler, no framework) — edit and hard-refresh the browser
- `DEBUG=False` — Flask caches templates, so restart Flask after editing `templates/*.html`
- JSON-on-disk storage is not safe for concurrent writes; per-user isolation reduces risk but same-user parallel writes can still collide
- The File System browser is confined to `FILES_ROOT` (`config.py`); every path goes through `services/filebrowser.py:resolve()`, a `realpath`-based traversal guard
- Convert legacy absolute-path datasets to the relocatable v2 layout with `tools/migrate_qc_to_relative.py`

For deeper architecture notes and operational recipes, see `CLAUDE.md`.

## License

Private repository — all rights reserved.

## Acknowledgments

Built with assistance from Claude Code (claude.com/code).
