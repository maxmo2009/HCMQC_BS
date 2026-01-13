# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CMR Segmentation QC Web Application - A Flask-based tool for quality control review of Cardiac MRI (CMR) segmentation results. Provides real-time visualization of 2650 patient scans with both End-Diastole (ED) and End-Systole (ES) phases.

## Running the Application

```bash
# Install dependencies (only needed once)
pip install -r requirements.txt

# Start development server
python app.py

# Server configuration:
# - URL: http://localhost:5000
# - Debug mode: Enabled (auto-reload on file changes)
# - Host: 0.0.0.0 (accessible from network)
# - Port: 5000

# Health check endpoint
curl http://localhost:5000/health
```

## Architecture

### Data Flow
1. **Startup**: Loads `JSON/QC_logs.json` (4.3MB) containing 2650 patient records into memory
2. **Session Management**: Flask sessions track current `patient_index` and `phase` (ED/ES)
3. **NIfTI Loading**: Reads `.nii.gz` files from patient directories using nibabel
4. **Image Processing**: Converts to base64 PNG for web display
5. **3D Extraction**: Extracts non-zero voxel coordinates for WebGL rendering

### Critical Path Configuration
- **BASE_PATH**: `/mnt/storage/home/ym1413/` - Hardcoded in app.py:31, prepended to all patient paths from JSON
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
GET /api/patient_list      # Returns all patients with comment status [0/2, 1/2, 2/2]

# QC Management
POST /api/save_qc          # Saves QC decision and comments to JSON
                          # Body: {qc_comment: "<choice>:<comments>", phase: "ED/ES"}
                          # Choices: accept, reject, finetune, unclassified

GET /api/download_json     # Downloads QC_logs.json file
```

### Frontend Architecture (templates/index.html)

**Panel Layout** (100vh × 100vh squares):
- **Left Panel** (`#left-panel`): MRI with overlay canvas
- **Middle Panel** (`#middle-panel`): Color-coded segmentation
- **Right Panel** (`#right-panel`): Three.js 3D visualization

**Key JavaScript Variables**:
```javascript
MRI_SLICES     // Base64 PNG array
SEG_SLICES     // Base64 RGB PNG array
SEG_COORDS     // [[x,y,z], ...] voxel positions
SEG_LABELS     // [1,2,3, ...] corresponding labels
SEG_SHAPE      // [width, height, depth]
SEG_SPACING    // [x_mm, y_mm, z_mm] voxel dimensions
```

**Three.js Rendering** (attached to `#right-panel`):
- InstancedMesh per label for performance
- Color mapping: 1=Red (LV), 2=Green (RV), 3=Blue (Myocardium)
- OrbitControls for interaction

### Control Panel Features

**Draggable Panel** (`#floating-qc-panel`):
- Drag from any background area (not buttons/inputs)
- Minimize/expand functionality
- Position persisted in localStorage

**Patient Selector Dropdown**:
- Shows all 2650 patients with format: `{index}. {patient_id} [comment_status]`
- Comment status shows `[0/2]`, `[1/2]`, or `[2/2]` for ED/ES completion

**QC Decision System**:
- Mutually exclusive checkboxes (Accept/Reject/Fine-tune/Unclassified)
- Comments stored as `<choice>:<comment_text>` in JSON
- Auto-loads existing decisions when navigating patients

**Interactive Controls**:
- Zoom slider (50%-300%) - affects both MRI and segmentation panels
- Transparency slider (0-100%) - for segmentation overlay on MRI
- Play/Pause for automatic slice cycling at 5 FPS

## Key Implementation Details

### Session Initialization
Sessions must be initialized on first visit:
```python
if 'patient_index' not in session:
    session['patient_index'] = 0
if 'phase' not in session:
    session['phase'] = 'ED'
```

### QC Comment Format
Comments in JSON follow the pattern `<choice>:<comments>`:
```json
{
  "ED_Comments": "accept:Good segmentation quality",
  "ES_Comments": "reject:Poor myocardium boundary"
}
```

### Canvas Overlay System
Left panel uses HTML5 Canvas for compositing:
1. Draw MRI image scaled to zoom level
2. If overlay enabled, draw segmentation with global alpha
3. Redraw triggered by zoom/transparency changes

### LocalStorage Keys
- `panelPosX`, `panelPosY` - Control panel position
- `panelMinimized` - Panel minimized state ('true'/'false')
- `zoomLevel` - Current zoom level
- `overlayTransparency` - Overlay transparency value

### Voxel Spacing Usage
Critical for accurate 3D representation:
```javascript
const scaledX = (x - midX) * SEG_SPACING[0] * 0.01;
const scaledY = (y - midY) * SEG_SPACING[1] * 0.01;
const scaledZ = (z - midZ) * SEG_SPACING[2] * 0.01;
```

## Development Notes

### Adding New Features
- Patient navigation triggers full page reload (cannot use pure client-side state)
- All image data transmitted as base64 to avoid static file serving
- Three.js renderer must reference `#right-panel` despite middle visual position

### Modifying Segmentation Colors
Update both locations to maintain consistency:
```python
# Backend (app.py)
color_map = {
    0: (0, 0, 0),       # Background
    1: (255, 0, 0),     # LV - Red
    2: (0, 255, 0),     # RV - Green
    3: (0, 136, 255)    # Myocardium - Blue
}

# Frontend (index.html)
const colors = {
    1: 0xff0000,  // Red
    2: 0x00ff00,  // Green
    3: 0x0088ff   // Blue
};
```

### Performance Considerations
- 2650 patients loaded into memory at startup (~4.3MB)
- Image caching implemented with 10-patient LRU cache (app.py:36-38)
- InstancedMesh used for 3D rendering (handles ~50K voxels efficiently)
- Flask sessions stored server-side with filesystem storage

## Testing and Development

### Manual Testing
```bash
# Test API endpoints
curl http://localhost:5000/api/patient_list   # Get all patients
curl http://localhost:5000/api/patient_data   # Get current patient data
curl http://localhost:5000/health             # Health check (returns voxel count)
```

### Common Development Tasks
- **Modifying Patient Data Path**: Update `BASE_PATH` in app.py:31
- **Changing Cache Size**: Modify `maxsize` in app.py:36-38
- **Adjusting Session Config**: Update `SESSION_TYPE` and related settings in app.py:22-25

## GitHub Configuration
- Repository: `git@github.com:maxmo2009/HCMQC_BS.git`
- User email: `maxmo2009@gmail.com`

## Project Dependencies
- Flask 3.0.0 - Web framework
- numpy 1.24.3 - Array operations
- nibabel 5.3.3 - NIfTI file reading
- Pillow 10.0.0 - Image processing