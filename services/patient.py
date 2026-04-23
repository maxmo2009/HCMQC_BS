from services.nifti_loader import (
    load_mri_slices,
    load_segmentation_slices,
    load_segmentation_data,
)
from services.qc_store import QCStore
from services.users import resolve_qc_path


def get_store_for_session(session):
    """Return a QCStore for the active (username, file) in session, or None.

    None means the user has no active QC file selected yet, or the selection
    references a file that no longer exists.
    """
    username = session.get('username')
    filename = session.get('active_qc_file')
    if not username or not filename:
        return None
    path = resolve_qc_path(username, filename)
    if path is None:
        return None
    return QCStore(path)


def build_patient_payload(store, patient_index, phase='ED'):
    """Assemble the full payload for a patient: metadata + slices + 3D voxel data.

    Returns None if the index is out of range.
    """
    patient_path = store.path_at(patient_index)
    if patient_path is None:
        return None

    patient_info = store.info_at(patient_index) or {}

    mri_slices = load_mri_slices(patient_path, phase)
    seg_slices = load_segmentation_slices(patient_path, phase)
    seg_coords, seg_labels, seg_shape, seg_spacing = load_segmentation_data(patient_path, phase)

    return {
        'patient_index': patient_index,
        'patient_path': patient_path,
        'patient_info': patient_info,
        'phase': phase,
        'mri_slices': mri_slices,
        'seg_slices': seg_slices,
        'seg_coords': seg_coords,
        'seg_labels': seg_labels,
        'seg_shape': list(seg_shape),
        'seg_spacing': seg_spacing,
        'total_patients': store.count(),
    }
