# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Cardiac MRI (CMR) Segmentation Quality Check** web application. The app provides a 3-panel interface for reviewing cardiac segmentation quality across multiple patients with 3D visualization, MRI slice viewing, and QC decision tracking.

## Running the Application

Start the Flask development server:
```bash
python app.py
```

Access the app at: `http://localhost:5000`

The server runs in debug mode with auto-reload enabled, so changes to templates and Python files are reflected automatically.

## Architecture Overview

### Backend (Flask + Session Management)
- **app.py**: Flask application with session-based patient tracking
  - Loads 2650 patients from `JSON/QC_logs.json` at startup
  - Session variables track current patient index and cardiac phase (ED/ES)
  - Base path: `/mnt/storage/home/ym1413/` prepended to all patient paths from JSON

### Patient Data Structure
- **Patient Database**: `JSON/QC_logs.json` contains 2650 patient records
  - Keys are patient directory paths (relative to BASE_PATH)
  - Each patient has metadata: SHARE_id, Sex, Age, Race, volumes, wall thickness stats, etc.
  - Each patient folder contains 4 NIfTI files:
    - `lvsa_SR_ED.nii.gz` - End-Diastole MRI
    - `lvsa_SR_ES.nii.gz` - End-Systole MRI
    - `seg_lvsa_SR_ED.nii.gz` - End-Diastole segmentation
    - `seg_lvsa_SR_ES.nii.gz` - End-Systole segmentation

### Frontend (Single HTML File)
- **templates/index.html**: Complete SPA (~1300 lines) containing:
  - CSS styling (inline `<style>` block)
  - HTML structure (3-panel layout + floating control panel)
  - JavaScript (Three.js 3D rendering, canvas overlay, patient navigation)

## Key API Endpoints

- `GET /` - Main visualization page (loads current patient/phase from session)
- `GET /health` - Health check endpoint
- `GET /api/next_patient` - Navigate to next patient, update session
- `GET /api/prev_patient` - Navigate to previous patient, update session
- `GET /api/set_phase/<phase>` - Switch between ED/ES phases (phase = 'ED' or 'ES')
- `GET /api/patient_data` - Get current patient data as JSON

## Frontend Architecture

### 3-Panel Layout (Left to Right)
1. **Left Panel**: MRI slices with overlay controls
   - Canvas-based rendering for MRI + segmentation overlay
   - Overlay checkbox and transparency slider
   - Zoom slider (50%-300%) affects both left and middle panels

2. **Middle Panel**: Color-coded segmentation slices
   - RGB images with color-mapped labels
   - Synchronized with left panel slice navigation
   - Same zoom level as left panel

3. **Right Panel**: 3D visualization
   - Three.js WebGL renderer attached to this panel
   - InstancedMesh rendering of segmentation voxels
   - OrbitControls for camera (left-click rotate, right-click pan, scroll zoom)
   - Lab logo positioned at bottom-right (absolute positioning within panel)

### Panel Dimensions
- All panels are **square**: `width: 100vh`, `height: 100vh`
- Three.js renderer dimensions pulled from `#right-panel` (not middle-panel!)
- Window resize handler updates renderer based on right panel dimensions

### Data Loading Flow
1. Backend loads NIfTI files (MRI + segmentation) for current patient/phase
2. MRI slices converted to base64 PNG images (grayscale)
3. Segmentation slices converted to base64 PNG images (RGB color-coded)
4. 3D segmentation extracted as coordinate arrays with labels
5. All data passed to template via Jinja2 variables
6. JavaScript receives: `MRI_SLICES`, `SEG_SLICES`, `SEG_COORDS`, `SEG_LABELS`, `SEG_SHAPE`, `SEG_SPACING`

### 3D Visualization Details
- **Color Map**:
  - Label 1 (Red): Left Ventricle
  - Label 2 (Green): Right Ventricle
  - Label 3 (Blue): Myocardium
- **Rendering**: InstancedMesh with separate meshes per label
- **Scaling**: Uses voxel spacing from NIfTI header for proper aspect ratio
- **Centering**: Coordinates centered around segmentation shape midpoint

### Slice Navigation
- **Manual**: ⏪ Prev / Next ⏩ buttons navigate through Z-axis slices
- **Auto-play**: ▶ Play button cycles through slices at 5 FPS
- **Synchronized**: All panels (left MRI, middle seg, right 3D) stay in sync

### Patient Navigation
- **← Prev / Next →** buttons navigate through 2650 patients
- Calls `/api/prev_patient` or `/api/next_patient`
- Page reloads after navigation to load new patient data
- Session persists patient index across page reloads

### Cardiac Phase Switching
- **ED / ES buttons** in control panel switch between End-Diastole and End-Systole
- Calls `/api/set_phase/<phase>` endpoint
- Page reloads to load new phase data
- Active button highlighted with blue gradient

### Floating Control Panel
- **Draggable**: Click header to drag anywhere on screen
- **Persistent Position**: Panel position saved to localStorage
- **Contains**:
  - Patient info display (ID, index, phase, path)
  - ED/ES phase switcher buttons
  - Patient comments textarea
  - Overlay transparency slider (0-100%)
  - QC Decision checkboxes (Accept, Reject, Fine-tune, Unclassified - mutually exclusive)
  - Slice navigation buttons (⏪ ⏩)
  - Play/Pause button
  - Patient navigation buttons (← Prev, Next →)
  - Save button

### Zoom Control
- **Location**: Bottom-right of left panel
- **Range**: 50% to 300%
- **Default**: 170%
- **Affects**: Both left panel (MRI canvas) and middle panel (segmentation image)
- **Implementation**:
  - Left panel: Canvas scale via `zoomLevel` variable
  - Middle panel: CSS transform `scale(zoomLevel)` on `#seg-slice-img`

### Overlay System
- **Canvas-based**: Left panel uses HTML5 Canvas for compositing
- **Two layers**: MRI (grayscale) drawn first, segmentation (RGB) drawn on top with alpha
- **Controls**:
  - Checkbox to toggle overlay on/off
  - Slider to adjust transparency (0-100%)
- **Real-time**: Both zoom and transparency changes trigger immediate canvas redraw

## Important Implementation Notes

1. **Session Management**: Flask sessions track patient_index and phase. Must be initialized on first visit.

2. **Panel ID Confusion**: Despite being in middle position, segmentation is in `#middle-panel` div. 3D visualization is in `#right-panel`. JavaScript references `rightPanel` for Three.js renderer.

3. **Data Size**: With 2650 patients, JSON file is 4.3MB. Patient database loaded once at startup into memory.

4. **File Paths**: Patient paths in JSON are relative. BASE_PATH (`/mnt/storage/home/ym1413/`) must be prepended to access files.

5. **Image Encoding**: All image data transmitted as base64-encoded data URLs to avoid serving static files. MRI slices normalized to 0-255 range.

6. **Segmentation Label Colors**: Hardcoded in both backend (for slice images) and frontend (for 3D rendering). Keep consistent:
   - 0: Black (background)
   - 1: Red (LV)
   - 2: Green (RV)
   - 3: Blue (Myocardium)

7. **LocalStorage**: Panel position saved to localStorage with keys `panelPosX` and `panelPosY`. Restored on page load.

8. **Voxel Spacing**: Critical for 3D visualization accuracy. Read from NIfTI header and applied as scaling factors in Three.js coordinate calculations.

9. **Page Reloads**: Patient and phase navigation trigger full page reloads. Cannot use client-side state management due to need to load new image data from backend.

10. **GitHub Account**: User's GitHub is `maxmo2009@gmail.com` (from global CLAUDE.md).

## Lab Logo
The lab logo appears at bottom-right of right panel (3D visualization):
- Position: `absolute` (not `fixed`)
- URL: `https://images.squarespace-cdn.com/content/v1/611bce9f0ec5ff43949b98ea/068036ac-5a6f-4da8-869f-520764bdaaaa/still_v023_frame_0103_photoshop_layer_logo_LMS.png?format=1500w`
- Z-index: 150 (below control panel at 200)

## Common Development Tasks

### Modifying 3D Visualization
- Edit JavaScript in `templates/index.html` starting at `function init()`
- Renderer attached to `#right-panel`, not `#middle-panel`
- Update `onWindowResize()` if panel IDs change

### Adding New Patient Metadata
- Data sourced from `JSON/QC_logs.json`
- Access via `PATIENT_DATA[patient_path]` in backend
- Pass to template via `patient_info` variable

### Changing Panel Layout
- Panel order controlled by HTML structure in `<div id="main-container">`
- CSS IDs (`#left-panel`, `#middle-panel`, `#right-panel`) have specific styling
- Update JavaScript references to panel IDs for Three.js rendering

### Adding New API Endpoints
- Session-based, use `session['patient_index']` and `session['phase']`
- Call `load_patient_data(index, phase)` to get full patient dataset
- Return JSON with `jsonify()` or reload page for new visualizations
