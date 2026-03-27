# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

HCM QC Tool - A Flask-based web application for quality control review of Cardiac MRI (CMR) segmentation results. Provides real-time visualization of patient scans with both End-Diastole (ED) and End-Systole (ES) phases.

## Running the Application

```bash
# Install dependencies (only needed once)
pip install -r requirements.txt

# Start development server
python3 app.py

# Server runs on http://localhost:5000 (debug mode off, binds 0.0.0.0)
```

## Testing Commands

```bash
curl http://localhost:5000/health             # Health check
curl http://localhost:5000/api/patient_list   # All patients with QC decisions
curl http://localhost:5000/api/patient_data   # Current patient data
curl http://localhost:5000/api/qc_statistics  # QC statistics

# Save a QC decision
curl -X POST http://localhost:5000/api/save_qc \
  -H "Content-Type: application/json" \
  -d '{"qc_comment": "accept:Good segmentation", "phase": "ED"}'
```

## Architecture

### Key Files
- **app.py** (~468 lines) — Flask backend: all routes, NIfTI loading, image processing, QC persistence
- **templates/index.html** (~2040 lines) — Single-page app: Three.js 3D visualization, Chart.js statistics, slice viewer, QC controls
- **JSON/QC_logs.json** — Patient database (JSON with patient paths as keys, loaded into memory at startup)

### Critical Path Configuration
- **BASE_PATH**: `/mnt/storage/home/ym1413/` — Hardcoded in app.py:14, prepended to all patient paths from JSON
- **File Structure per Patient**:
  ```
  {BASE_PATH}/{patient_path}/
    ├── lvsa_SR_ED.nii.gz      # ED phase MRI
    ├── lvsa_SR_ES.nii.gz      # ES phase MRI
    ├── seg_lvsa_SR_ED.nii.gz  # ED segmentation
    └── seg_lvsa_SR_ES.nii.gz  # ES segmentation
  ```

### Backend API Endpoints

```
GET  /                        # Main page — loads patient data, renders index.html
GET  /api/next_patient        # Increment session patient_index, returns JSON
GET  /api/prev_patient        # Decrement session patient_index, returns JSON
GET  /api/goto_patient/<id>   # Jump to patient by index
GET  /api/set_phase/<phase>   # Switch between 'ED' and 'ES'
GET  /api/patient_data        # Current patient's full dataset as JSON
GET  /api/patient_list        # All patients with QC decisions (ed_decision, es_decision)
GET  /api/qc_statistics       # QC decision counts and percentages
POST /api/save_qc             # Save QC decision: {qc_comment: "<choice>:<comments>", phase: "ED/ES"}
GET  /api/download_json       # Download QC_logs.json
GET  /health                  # Health check
```

### Frontend Architecture

**Three-Panel Layout** (each panel is `(100vh - 52px)` square):
- **Left Panel** (`#left-panel`): MRI canvas with segmentation overlay, zoom/transparency sliders
- **Middle Panel** (`#middle-panel`): Color-coded segmentation image
- **Right Panel** (`#right-panel`): Three.js 3D InstancedMesh visualization (~50K voxels)

**Floating Panels** (z-index: 2000, draggable, minimizable, positions saved to localStorage):
- **QC Control Panel**: Patient dropdown, ED/ES toggle, QC decisions (accept/reject/finetune/unclassified), comments, navigation
- **Statistics Panel**: Chart.js pie chart with QC decision distribution

**Key JS Variables** (embedded from Flask template):
```javascript
MRI_SLICES     // Base64 PNG array — MRI slices
SEG_SLICES     // Base64 RGB PNG array — segmentation slices
SEG_COORDS     // [[x,y,z], ...] voxel positions for 3D
SEG_LABELS     // [1,2,3, ...] corresponding labels
SEG_SHAPE      // [width, height, depth]
SEG_SPACING    // [x_mm, y_mm, z_mm] voxel dimensions
```

### Data Flow
1. Startup loads `QC_logs.json` into `PATIENT_LIST` and `PATIENT_DATA` globals
2. Session tracks `patient_index` and `phase` (ED/ES)
3. Page load triggers NIfTI file loading via nibabel → base64 PNG conversion + voxel coordinate extraction
4. Frontend preloads all slice images, builds Three.js 3D scene, populates controls
5. Patient/phase navigation updates session then triggers full page reload
6. QC save writes to in-memory data and persists to `QC_logs.json` on disk

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

## Development Notes

### Key Configuration Points
- **Patient Data Path**: `BASE_PATH` in app.py:14
- **Session Secret**: `app.secret_key` in app.py:11
- **Port/Host**: `app.run()` at bottom of app.py (currently `0.0.0.0:5000`, debug=False)

### Important Constraints
- Patient/phase navigation requires full page reload (session-based state)
- All image data transmitted as base64 (no static file serving)
- QC decisions are mutually exclusive (enforced via JS, not backend)
- Floating panel positions persisted in localStorage (keys: panelPosX/Y, statsPanelPosX/Y, panelMinimized, statsPanelMinimized)
- No @lru_cache in current code despite prior documentation — NIfTI files are loaded fresh each request
- JSON file-based storage is not safe for concurrent writes

### 3D Visualization Details
- Three.js with 5-point lighting setup optimized for cardiac structure visibility
- OrbitControls with damping, screen-space panning
- Separate InstancedMesh per label with MeshPhongMaterial
- Voxel spacing applied for correct physical dimensions
- Slice playback at 5 FPS default

## GitHub Configuration
- Repository: `git@github.com:maxmo2009/HCMQC_BS.git`
- User email: `maxmo2009@gmail.com`
