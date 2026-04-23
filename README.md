# Cardiac Segmentation QC Studio

A web-based quality control tool for reviewing Cardiac MRI (CMR) segmentation results. This application provides an interactive 3-panel interface for visualizing MRI slices, 3D segmentation, and overlay comparisons.

![Lab Logo](https://images.squarespace-cdn.com/content/v1/611bce9f0ec5ff43949b98ea/068036ac-5a6f-4da8-869f-520764bdaaaa/still_v023_frame_0103_photoshop_layer_logo_LMS.png?format=300w)

## Features

### 3-Panel Layout
- **Left Panel**: MRI slices with optional segmentation overlay
- **Middle Panel**: Interactive 3D visualization of cardiac segmentation
- **Right Panel**: Color-coded segmentation slices

### Interactive Visualization
- **3D Cardiac Structures**:
  - Red: Left Ventricle (LV)
  - Green: Right Ventricle (RV)
  - Blue: Myocardium
- **Camera Controls**: Rotate (left-click drag), Pan (right-click drag), Zoom (scroll)
- **Proper Aspect Ratio**: Uses voxel spacing from NIfTI headers

### Slice Navigation
- **Play/Pause**: Automatic slice playback at 5 FPS
- **Manual Navigation**: Previous (⏪) and Next (⏩) buttons
- **Synchronized Views**: All panels update together

### Overlay Controls
- **Toggle Overlay**: Checkbox to show/hide segmentation overlay on MRI
- **Transparency Slider**: Adjust overlay transparency (0-100%)
- **Real-time Updates**: Instant visual feedback

### Quality Control
- **QC Decision**: Accept ✓ or Reject ✗ checkboxes (mutually exclusive)
- **Patient Comments**: Text area for reviewer notes
- **Save Function**: Store QC decisions and comments
- **Draggable Control Panel**: Reposition controls anywhere on screen

### Medical Imaging Support
- **NIfTI Format**: Loads .nii.gz files for both MRI and segmentation
- **Voxel Spacing**: Accurate physical dimensions from header metadata
- **Multi-label Support**: Color-coded visualization of different cardiac structures

## Installation

1. Clone the repository:
```bash
git clone https://github.com/maxmo2009/HCMQC_BS.git
cd HCMQC_BS
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

1. Start the Flask server:
```bash
python app.py
```

2. Open your browser and navigate to:
```
http://localhost:5000
```

The server runs in debug mode with auto-reload enabled.

## Project Structure

```
HCMQC_BS/
├── app.py                          # Flask backend
├── templates/
│   └── index.html                  # Single-page application
├── tempCMR/
│   ├── lvsa_SR_ED.nii.gz          # MRI volume data
│   └── seg_lvsa_SR_ED.nii.gz      # Segmentation data
├── static/
│   ├── left_placeholder.png        # Placeholder images
│   └── right_placeholder.png
├── requirements.txt                # Python dependencies
├── CLAUDE.md                       # Development documentation
└── README.md                       # This file
```

## API Endpoints

- `GET /` - Main visualization page
- `GET /health` - Health check endpoint returning voxel count

## Tech Stack

### Backend
- **Flask 3.0.0**: Web framework
- **nibabel 5.3.3**: NIfTI file reading
- **numpy 1.24.3**: Array operations
- **Pillow 10.0.0**: Image processing

### Frontend
- **Three.js**: WebGL 3D rendering
- **OrbitControls**: Camera manipulation
- **HTML5 Canvas**: MRI/segmentation overlay
- **Vanilla JavaScript**: UI interactions

## Usage

### Viewing Data
1. The application loads MRI and segmentation data on startup
2. Use the overlay checkbox to toggle segmentation visibility
3. Adjust transparency with the slider for optimal viewing
4. Navigate slices manually or use auto-play

### Making QC Decisions
1. Review the MRI slices, segmentation, and 3D visualization
2. Check "Accept" or "Reject" based on segmentation quality
3. Add comments in the text area
4. Click "Save" to store your decision

### 3D Visualization
- The middle panel shows the cardiac segmentation in 3D
- Rotate to view from different angles
- Color coding helps identify different structures
- Real-time rendering of 51,185 voxels

## Data Format

The application expects NIfTI (.nii.gz) files with:
- **MRI Data**: Grayscale intensity values
- **Segmentation Data**: Integer labels (0=background, 1=LV, 2=RV, 3=Myocardium)
- **Voxel Spacing**: Stored in NIfTI header (typically ~1.25 × 1.25 × 8.0 mm)

## Development

This project uses:
- Flask development server with auto-reload
- Single-file frontend architecture (templates/index.html)
- Client-side data processing for interactive performance
- Base64-encoded images for efficient data transfer

For development guidance, see `CLAUDE.md`.

## License

Private repository - All rights reserved

## Acknowledgments

Built with assistance from Claude Code (claude.com/code)
