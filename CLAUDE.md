# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Cardiac MRI (CMR) Segmentation Quality Check** web application. The app provides a 3-panel interface for reviewing cardiac segmentation quality with 3D visualization capabilities.

## Running the Application

Start the Flask development server:
```bash
python app.py
```

Access the app at: `http://localhost:5000`

The server runs in debug mode with auto-reload enabled, so changes to templates and Python files are reflected automatically.

## Architecture

### Backend (Flask)
- **app.py**: Minimal Flask server with two routes:
  - `/` - Serves the main visualization page
  - `/health` - Health check endpoint

### Frontend (Single-Page Application)
- **templates/index.html**: Complete application in a single HTML file containing:
  - CSS styling (inline `<style>` block)
  - HTML structure (3-panel layout)
  - JavaScript logic (Three.js visualization, UI interactions)

### Key Frontend Architecture

**3-Panel Layout:**
- All three panels are **square** (`width: 100vh`, `height: 100vh`)
- Left panel: Placeholder for cardiac image views (short-axis slices)
- Middle panel: Interactive 3D visualization using Three.js
- Right panel: Placeholder for additional cardiac image views (long-axis slices)

**3D Visualization (Middle Panel):**
- Uses **Three.js** for WebGL rendering
- Uses **OrbitControls** for camera manipulation
- Currently displays a procedurally-generated 3D ball (256×256×256 voxel space, radius 60)
- Ball is rendered using **InstancedMesh** with small cubes for each voxel
- Lighting setup: 1 ambient light + 3 directional lights + 2 point lights
- Ball generation happens client-side in JavaScript (no external data files)

**Draggable QC Panel:**
- Floating panel positioned at bottom-right by default
- Contains "Accept" and "Reject" buttons for quality control decisions
- Drag functionality implemented with vanilla JavaScript (mousedown/mousemove/mouseup)
- Drag the panel by clicking the header bar
- Status messages appear at top center after button clicks

**Important Implementation Details:**
1. The 3D object is generated in JavaScript, NOT loaded from JSON/files
2. Camera controls use OrbitControls (left-click rotate, right-click pan, scroll zoom)
3. Panel dimensions must maintain square aspect ratio for proper layout
4. Window resize handler updates renderer and camera aspect ratio based on middle panel dimensions

## Static Assets

- `static/left_placeholder.png`: Placeholder image for left panel
- `static/right_placeholder.png`: Placeholder image for right panel

These are currently simple gray placeholder images with text. In a production CMR QC system, these would display actual cardiac MRI slices.

## Future Development Notes

This is designed as a CMR segmentation QC tool. Expected future additions:
- DICOM/NIfTI file upload and parsing
- Replace 3D ball with actual cardiac anatomy (LV, RV, myocardium segmentation)
- Slice navigation and viewing in left/right panels
- Segmentation overlay toggle
- Backend API for saving QC decisions
- Multi-case navigation

When adding medical imaging features, maintain the current 3-panel square layout and draggable QC panel pattern.

## Lab Logo
https://images.squarespace-cdn.com/content/v1/611bce9f0ec5ff43949b98ea/068036ac-5a6f-4da8-869f-520764bdaaaa/still_v023_frame_0103_photoshop_layer_logo_LMS.png?format=1500w