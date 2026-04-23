import os
import base64
from io import BytesIO

import nibabel as nib
import numpy as np
from PIL import Image

from config import BASE_PATH, LABEL_COLOR_MAP


def _pil_to_base64_png(img):
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    encoded = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{encoded}"


def _seg_file(patient_path, phase):
    return os.path.join(BASE_PATH + patient_path, f'seg_lvsa_SR_{phase}.nii.gz')


def _mri_file(patient_path, phase):
    return os.path.join(BASE_PATH + patient_path, f'lvsa_SR_{phase}.nii.gz')


def load_mri_slices(patient_path, phase='ED'):
    """Load MRI volume and return slices as base64 PNGs along Z axis."""
    mri_path = _mri_file(patient_path, phase)

    if not os.path.exists(mri_path):
        print(f"MRI file not found: {mri_path}")
        return []

    mri_img = nib.load(mri_path)
    mri_data = mri_img.get_fdata()
    print(f"MRI shape: {mri_data.shape}")

    slices_base64 = []
    for z in range(mri_data.shape[2]):
        slice_data = mri_data[:, :, z]
        slice_min = slice_data.min()
        slice_max = slice_data.max()
        if slice_max > slice_min:
            slice_norm = ((slice_data - slice_min) / (slice_max - slice_min) * 255).astype(np.uint8)
        else:
            slice_norm = np.zeros_like(slice_data, dtype=np.uint8)

        img = Image.fromarray(slice_norm, mode='L')
        slices_base64.append(_pil_to_base64_png(img))

    print(f"Extracted {len(slices_base64)} MRI slices")
    return slices_base64


def load_segmentation_slices(patient_path, phase='ED'):
    """Load segmentation volume and return color-coded slices as base64 PNGs along Z axis."""
    seg_path = _seg_file(patient_path, phase)

    if not os.path.exists(seg_path):
        print(f"Segmentation file not found: {seg_path}")
        return []

    seg_img = nib.load(seg_path)
    seg_data = seg_img.get_fdata()
    print(f"Segmentation shape: {seg_data.shape}")

    seg_slices_base64 = []
    for z in range(seg_data.shape[2]):
        slice_data = seg_data[:, :, z].astype(np.uint8)
        rgb_image = np.zeros((slice_data.shape[0], slice_data.shape[1], 3), dtype=np.uint8)
        for label, color in LABEL_COLOR_MAP.items():
            rgb_image[slice_data == label] = color

        img = Image.fromarray(rgb_image, mode='RGB')
        seg_slices_base64.append(_pil_to_base64_png(img))

    print(f"Extracted {len(seg_slices_base64)} segmentation slices")
    return seg_slices_base64


def load_segmentation_data(patient_path, phase='ED'):
    """Return non-zero voxel coords, labels, volume shape, and voxel spacing."""
    seg_path = _seg_file(patient_path, phase)

    if not os.path.exists(seg_path):
        print(f"Segmentation file not found: {seg_path}")
        return [], [], (0, 0, 0), [1.0, 1.0, 1.0]

    seg_img = nib.load(seg_path)
    seg_data = seg_img.get_fdata()
    spacing = seg_img.header.get_zooms()

    coords = np.argwhere(seg_data != 0)
    labels = np.round(seg_data[coords[:, 0], coords[:, 1], coords[:, 2]]).astype(int)

    print(f"Loaded segmentation: {seg_data.shape}")
    print(f"Voxel spacing: {spacing[:3]} mm")
    print(f"Non-zero voxels: {len(coords)}")
    print(f"Unique labels: {np.unique(labels)}")

    return (
        coords.tolist(),
        labels.tolist(),
        seg_data.shape,
        [float(spacing[0]), float(spacing[1]), float(spacing[2])],
    )
