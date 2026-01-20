# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

HCM QC Tool - A Flask-based web application for quality control review of Cardiac MRI (CMR) segmentation results. Provides real-time visualization of 2650 patient scans with both End-Diastole (ED) and End-Systole (ES) phases.

## Running the Application

```bash
# Install dependencies (only needed once)
pip install -r requirements.txt

# Start development server
python app.py

# Server runs on http://localhost:5000 with debug mode enabled
```

## Architecture

### Critical Path Configuration
- **BASE_PATH**: `/mnt/storage/home/ym1413/` - Hardcoded in app.py:14, prepended to all patient paths from JSON
- **Data Loading**: `JSON/QC_logs.json` (4.3MB) loaded into memory at startup containing 2650 patient records
- **File Structure per Patient**:
  ```
  {patient_path}/
    ├── lvsa_SR_ED.nii.gz      # ED phase MRI
    ├── lvsa_SR_ES.nii.gz      # ES phase MRI
    ├── seg_lvsa_SR_ED.nii.gz  # ED segmentation
    └── seg_lvsa_SR_ES.nii.gz  # ES segmentation
  ```

### Backend API Endpoints

```python
# Patient Navigation
GET /api/next_patient      # Updates session['patient_index'], triggers page reload
GET /api/prev_patient      # Updates session['patient_index'], triggers page reload
GET /api/goto_patient/<id> # Jump to specific patient by index

# Phase Control
GET /api/set_phase/<phase> # Switch between 'ED' and 'ES'

# Data Access
GET /api/patient_data      # Returns current patient's full dataset as JSON
GET /api/patient_list      # Returns all patients with QC decisions (ed_decision, es_decision)
GET /api/qc_statistics     # Returns QC decision statistics and percentages

# QC Management
POST /api/save_qc          # Saves QC decision and comments to JSON
                          # Body: {qc_comment: "<choice>:<comments>", phase: "ED/ES"}
                          # Choices: accept, reject, finetune, unclassified

GET /api/download_json     # Downloads QC_logs.json file
GET /health               # Health check (returns voxel count)
```

### Frontend Architecture

**Layout Structure**:
- **Top Bar** (`#top-bar`): Fixed header displaying "HCM QC Tool" at 50px height
- **Three-Panel Layout**: Each panel is (100vh - 52px) square
  - **Left Panel** (`#left-panel`): MRI with overlay canvas
  - **Middle Panel** (`#middle-panel`): Color-coded segmentation
  - **Right Panel** (`#right-panel`): Three.js 3D visualization

**Floating Panels**:
- **QC Control Panel** (`#floating-qc-panel`): Draggable panel with QC decisions, z-index: 2000
- **Statistics Panel** (`#floating-stats-panel`): Draggable panel with live pie chart, z-index: 2000

**Key JavaScript Variables**:
```javascript
MRI_SLICES     // Base64 PNG array
SEG_SLICES     // Base64 RGB PNG array
SEG_COORDS     // [[x,y,z], ...] voxel positions
SEG_LABELS     // [1,2,3, ...] corresponding labels
SEG_SHAPE      // [width, height, depth]
SEG_SPACING    // [x_mm, y_mm, z_mm] voxel dimensions
```

### UI Features

**Patient Dropdown Display**:
- Format: `{index}. {patient_id} (ed_decision, es_decision)`
- Example: `1. patient_1234 (accept, reject)`
- Shows QC decisions for both ED and ES phases inline

**QC Comment Format**:
Comments in JSON follow the pattern `<choice>:<comments>`:
```json
{
  "ED_Comments": "accept:Good segmentation quality",
  "ES_Comments": "reject:Poor myocardium boundary"
}
```

### Session Management
Flask sessions track `patient_index` and `phase` (ED/ES). Sessions are initialized on first visit and stored server-side with filesystem storage. Patient navigation triggers full page reload.

### Color Mapping
Segmentation labels use consistent colors across backend and frontend:
```python
# Backend (app.py:96-100)
color_map = {
    0: (0, 0, 0),       # Background
    1: (255, 0, 0),     # LV - Red
    2: (0, 255, 0),     # RV - Green
    3: (0, 136, 255)    # Myocardium - Blue
}
```

### Performance Optimizations
- 10-patient LRU cache for image data (functools.lru_cache in load_patient_data)
- InstancedMesh for 3D rendering (handles ~50K voxels efficiently)
- Base64 encoding for image transmission (avoids static file serving)

## Testing Commands

```bash
# Test API endpoints
curl http://localhost:5000/api/patient_list   # Get all patients with QC decisions
curl http://localhost:5000/api/patient_data   # Get current patient data
curl http://localhost:5000/api/qc_statistics  # Get QC statistics
curl http://localhost:5000/health             # Health check

# Test QC save endpoint
curl -X POST http://localhost:5000/api/save_qc \
  -H "Content-Type: application/json" \
  -d '{"qc_comment": "accept:Good segmentation", "phase": "ED"}'
```

## Development Notes

### Key Files to Modify
- **Patient Data Path**: Update `BASE_PATH` in app.py:14
- **Cache Size**: Modify `maxsize` parameter in @lru_cache decorator
- **Session Config**: Update `app.secret_key` in app.py:11
- **Port/Host**: Change in `app.run()` at bottom of app.py

### Data Flow
1. Startup loads JSON database into memory
2. Session tracks current patient/phase
3. API calls trigger NIfTI file loading via nibabel
4. Images converted to base64 PNG
5. 3D coordinates extracted for WebGL rendering
6. Frontend receives JSON with all visualization data

### Important Constraints
- Patient navigation requires full page reload (session-based state)
- All image data transmitted as base64 (no static file serving)
- Three.js renderer attached to `#right-panel` despite middle visual position
- QC decisions are mutually exclusive checkboxes
- Floating panels positioned to avoid top bar overlap (min 70px from top)
- Panel positions persisted in localStorage

## GitHub Configuration
- Repository: `git@github.com:maxmo2009/HCMQC_BS.git`
- User email: `maxmo2009@gmail.com`