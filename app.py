from flask import Flask, render_template, jsonify
import os
import nibabel as nib
import numpy as np
import json
import base64
from io import BytesIO
from PIL import Image

app = Flask(__name__)

# Load MRI slices
def load_mri_slices():
    """Load MRI volume and extract slices as base64 encoded images"""
    mri_img = nib.load('tempCMR/lvsa_SR_ED.nii.gz')
    mri_data = mri_img.get_fdata()

    print(f"MRI shape: {mri_data.shape}")

    # Extract slices along Z axis
    num_slices = mri_data.shape[2]
    slices_base64 = []

    for z in range(num_slices):
        slice_data = mri_data[:, :, z]

        # Normalize to 0-255
        slice_min = slice_data.min()
        slice_max = slice_data.max()
        if slice_max > slice_min:
            slice_norm = ((slice_data - slice_min) / (slice_max - slice_min) * 255).astype(np.uint8)
        else:
            slice_norm = np.zeros_like(slice_data, dtype=np.uint8)

        # Convert to PIL Image
        img = Image.fromarray(slice_norm, mode='L')

        # Convert to base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        slices_base64.append(f"data:image/png;base64,{img_str}")

    print(f"Extracted {len(slices_base64)} MRI slices")
    return slices_base64

# Load segmentation slices
def load_segmentation_slices():
    """Load segmentation volume and extract slices as base64 encoded images with color coding"""
    seg_img = nib.load('tempCMR/seg_lvsa_SR_ED.nii.gz')
    seg_data = seg_img.get_fdata()

    print(f"Segmentation shape: {seg_data.shape}")

    # Extract slices along Z axis
    num_slices = seg_data.shape[2]
    seg_slices_base64 = []

    # Color map for labels: 1=red, 2=green, 3=blue
    color_map = {
        0: (0, 0, 0),       # Background - black
        1: (255, 0, 0),     # Label 1 - red (LV)
        2: (0, 255, 0),     # Label 2 - green (RV)
        3: (0, 136, 255)    # Label 3 - blue (Myocardium)
    }

    for z in range(num_slices):
        slice_data = seg_data[:, :, z].astype(np.uint8)

        # Create RGB image
        rgb_image = np.zeros((slice_data.shape[0], slice_data.shape[1], 3), dtype=np.uint8)

        for label, color in color_map.items():
            mask = slice_data == label
            rgb_image[mask] = color

        # Convert to PIL Image
        img = Image.fromarray(rgb_image, mode='RGB')

        # Convert to base64
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        seg_slices_base64.append(f"data:image/png;base64,{img_str}")

    print(f"Extracted {len(seg_slices_base64)} segmentation slices")
    return seg_slices_base64

# Load segmentation data at startup
def load_segmentation_data():
    """Load NIfTI segmentation file and extract non-zero coordinates"""
    seg_img = nib.load('tempCMR/seg_lvsa_SR_ED.nii.gz')
    seg_data = seg_img.get_fdata()

    # Get voxel spacing from header
    spacing = seg_img.header.get_zooms()

    # Get coordinates where segmentation is non-zero
    coords = np.argwhere(seg_data != 0)

    # Get the labels for each coordinate
    labels = seg_data[coords[:, 0], coords[:, 1], coords[:, 2]]

    print(f"Loaded segmentation: {seg_data.shape}")
    print(f"Voxel spacing: {spacing[:3]} mm")
    print(f"Non-zero voxels: {len(coords)}")
    print(f"Unique labels: {np.unique(labels)}")

    return coords.tolist(), labels.tolist(), seg_data.shape, [float(spacing[0]), float(spacing[1]), float(spacing[2])]

# Load data once at startup
MRI_SLICES = load_mri_slices()
SEG_SLICES = load_segmentation_slices()
SEG_COORDS, SEG_LABELS, SEG_SHAPE, SEG_SPACING = load_segmentation_data()

@app.route('/')
def index():
    """Serve the main visualization page"""
    # Pass segmentation data and MRI slices to template
    return render_template('index.html',
                          mri_slices=json.dumps(MRI_SLICES),
                          seg_slices=json.dumps(SEG_SLICES),
                          seg_coords=json.dumps(SEG_COORDS),
                          seg_labels=json.dumps(SEG_LABELS),
                          seg_shape=list(SEG_SHAPE),
                          seg_spacing=SEG_SPACING)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'CMR Segmentation QC Web App is running',
        'voxels': len(SEG_COORDS)
    })

if __name__ == '__main__':
    print("=" * 60)
    print("CMR Segmentation QC Web App")
    print("=" * 60)
    print("Starting server...")
    print("Open your browser and navigate to: http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
