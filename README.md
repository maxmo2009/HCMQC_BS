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
- Dataset format: top-level dict keyed by patient path, values hold `ED_Comments` / `ES_Comments`

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

Server binds to **http://localhost:5000** (`DEBUG=False`). On the production host the app is run as a systemd user service and exposed via ngrok at <https://hcmqc.ngrok.app>.

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

## Expected File Layout (per patient, on disk)

```
{patient_path}/
├── lvsa_SR_ED.nii.gz      # ED-phase MRI
├── lvsa_SR_ES.nii.gz      # ES-phase MRI
├── seg_lvsa_SR_ED.nii.gz  # ED-phase segmentation
└── seg_lvsa_SR_ES.nii.gz  # ES-phase segmentation
```

The `{patient_path}` is stored as a full absolute path in each dataset JSON.

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

## Project Structure

```
HCMQC_BS/
├── app.py                      # Flask app factory (create_app) + entrypoint
├── config.py                   # Constants + path helpers (USERS_JSON_PATH, user_dir, ...)
├── requirements.txt
├── CLAUDE.md                   # Architecture notes + operational recipes for Claude Code
├── README.md                   # This file
│
├── routes/                     # Flask blueprints
│   ├── auth.py                 #   /login, /logout, login_required decorator
│   ├── pages.py                #   /  (main page) and /health
│   └── api.py                  #   all /api/* endpoints
│
├── services/                   # Business logic (no Flask dependency)
│   ├── users.py                #   auth + per-user dataset file listing + path-traversal guard
│   ├── qc_store.py             #   QCStore class (per-request, JSON-backed) + parse_decision
│   ├── nifti_loader.py         #   MRI/segmentation slice loading → base64 PNG, 3D voxel extraction
│   └── patient.py              #   get_store_for_session + build_patient_payload orchestrator
│
├── templates/
│   ├── index.html              # Main page skeleton (3 panels + floating QC/stats panels)
│   └── login.html              # Username + password form
│
├── static/
│   ├── css/app.css             # All UI styles
│   ├── js/app.js               # All frontend logic (Three.js, Chart.js, controls)
│   ├── left_placeholder.png
│   └── right_placeholder.png
│
└── JSON/                       # gitignored — contains credentials + patient data
    ├── users.json              #   {"username": "plaintext_password", ...}
    └── users/
        └── <username>/
            └── *.json           #     Per-user QC dataset files
```

Nothing under `JSON/` is committed — both credentials and patient data stay local.

## API Endpoints

All `/` and `/api/*` routes require auth. Most `/api/*` routes also require an active dataset (set automatically on first visit, or via `/api/set_qc_file`).

| Method | Path | Notes |
|---|---|---|
| GET | `/login` | Username + password form |
| GET | `/logout` | Clears session |
| GET | `/` | Main page |
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

## Development Notes

- Backend logic is split across `routes/` and `services/`; `config.py` centralizes constants
- CSS and JS live under `static/` (no bundler, no framework) — edit and hard-refresh the browser
- `DEBUG=False` — Flask caches templates, so restart Flask after editing `templates/*.html`
- JSON-on-disk storage is not safe for concurrent writes; per-user isolation reduces risk but same-user parallel writes can still collide

For deeper architecture notes and operational recipes, see `CLAUDE.md`.

## License

Private repository — all rights reserved.

## Acknowledgments

Built with assistance from Claude Code (claude.com/code).
