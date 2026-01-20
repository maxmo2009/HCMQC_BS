from flask import Flask, render_template, jsonify, request, session, send_file
import os
import nibabel as nib
import numpy as np
import json
import base64
from io import BytesIO
from PIL import Image

app = Flask(__name__)
app.secret_key = 'cmr_qc_secret_key_12345'  # Required for session management

# Base path to prepend to patient paths
BASE_PATH = '/mnt/storage/home/ym1413'
# BASE_PATH = ''

# Global variables
PATIENT_LIST = []
PATIENT_DATA = {}

def load_patient_database():
    """Load patient database from QC_logs.json"""
    json_path = os.path.join(os.path.dirname(__file__), 'JSON', 'QC_logs.json')

    with open(json_path, 'r') as f:
        data = json.load(f)

    # Get list of patient paths
    patient_paths = list(data.keys())

    print(f"Loaded {len(patient_paths)} patients from QC_logs.json")

    return patient_paths, data

# Load patient database at startup
PATIENT_LIST, PATIENT_DATA = load_patient_database()

def load_mri_slices(patient_path, phase='ED'):
    """Load MRI volume and extract slices as base64 encoded images"""
    mri_path = os.path.join(BASE_PATH + patient_path, f'lvsa_SR_{phase}.nii.gz')

    if not os.path.exists(mri_path):
        print(f"MRI file not found: {mri_path}")
        return []

    mri_img = nib.load(mri_path)
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

def load_segmentation_slices(patient_path, phase='ED'):
    """Load segmentation volume and extract slices as base64 encoded images with color coding"""
    seg_path = os.path.join(BASE_PATH + patient_path, f'seg_lvsa_SR_{phase}.nii.gz')

    if not os.path.exists(seg_path):
        print(f"Segmentation file not found: {seg_path}")
        return []

    seg_img = nib.load(seg_path)
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

def load_segmentation_data(patient_path, phase='ED'):
    """Load NIfTI segmentation file and extract non-zero coordinates"""
    seg_path = os.path.join(BASE_PATH + patient_path, f'seg_lvsa_SR_{phase}.nii.gz')

    if not os.path.exists(seg_path):
        print(f"Segmentation file not found: {seg_path}")
        return [], [], (0, 0, 0), [1.0, 1.0, 1.0]

    seg_img = nib.load(seg_path)
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

def load_patient_data(patient_index, phase='ED'):
    """Load all data for a specific patient"""
    if patient_index < 0 or patient_index >= len(PATIENT_LIST):
        return None

    patient_path = PATIENT_LIST[patient_index]

    # Load patient metadata
    patient_info = PATIENT_DATA.get(patient_path, {})

    # Load MRI and segmentation data
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
        'total_patients': len(PATIENT_LIST)
    }

@app.route('/')
def index():
    """Serve the main visualization page"""
    # Initialize session if not exists
    if 'patient_index' not in session:
        session['patient_index'] = 0
    if 'phase' not in session:
        session['phase'] = 'ED'

    # Load current patient data
    patient_data = load_patient_data(session['patient_index'], session['phase'])

    if patient_data is None:
        return "Error: No patient data available", 500

    # Get the appropriate comment based on phase
    comment_key = f"{patient_data['phase']}_Comments"
    qc_comment = patient_data['patient_info'].get(comment_key, '')

    # Pass data to template
    return render_template('index.html',
                          patient_index=patient_data['patient_index'],
                          patient_path=patient_data['patient_path'],
                          patient_info=json.dumps(patient_data['patient_info']),
                          phase=patient_data['phase'],
                          qc_comment=qc_comment,
                          mri_slices=json.dumps(patient_data['mri_slices']),
                          seg_slices=json.dumps(patient_data['seg_slices']),
                          seg_coords=json.dumps(patient_data['seg_coords']),
                          seg_labels=json.dumps(patient_data['seg_labels']),
                          seg_shape=patient_data['seg_shape'],
                          seg_spacing=patient_data['seg_spacing'],
                          total_patients=patient_data['total_patients'])

@app.route('/api/next_patient')
def next_patient():
    """Navigate to next patient"""
    current_index = session.get('patient_index', 0)
    new_index = (current_index + 1) % len(PATIENT_LIST)
    session['patient_index'] = new_index

    return jsonify({
        'status': 'success',
        'patient_index': new_index,
        'total_patients': len(PATIENT_LIST)
    })

@app.route('/api/prev_patient')
def prev_patient():
    """Navigate to previous patient"""
    current_index = session.get('patient_index', 0)
    new_index = (current_index - 1) % len(PATIENT_LIST)
    session['patient_index'] = new_index

    return jsonify({
        'status': 'success',
        'patient_index': new_index,
        'total_patients': len(PATIENT_LIST)
    })

@app.route('/api/set_phase/<phase>')
def set_phase(phase):
    """Set current cardiac phase (ED or ES)"""
    if phase in ['ED', 'ES']:
        session['phase'] = phase
        return jsonify({
            'status': 'success',
            'phase': phase
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'Invalid phase. Must be ED or ES'
        }), 400

@app.route('/api/patient_data')
def get_patient_data():
    """Get current patient data"""
    patient_data = load_patient_data(session.get('patient_index', 0), session.get('phase', 'ED'))

    if patient_data is None:
        return jsonify({'status': 'error', 'message': 'Patient data not found'}), 404

    return jsonify({
        'status': 'success',
        'data': patient_data
    })

@app.route('/api/patient_list')
def get_patient_list():
    """Get list of all patient paths with comment status"""
    patient_list_with_status = []

    for patient_path in PATIENT_LIST:
        patient_info = PATIENT_DATA.get(patient_path, {})
        ed_comment = patient_info.get('ED_Comments', '')
        es_comment = patient_info.get('ES_Comments', '')

        # Extract QC decisions from comments
        ed_decision = ''
        es_decision = ''

        if ed_comment and ed_comment.strip():
            if ed_comment.startswith('accept:'):
                ed_decision = 'accept'
            elif ed_comment.startswith('reject:'):
                ed_decision = 'reject'
            elif ed_comment.startswith('finetune:'):
                ed_decision = 'finetune'
            elif ed_comment.startswith('unclassified:'):
                ed_decision = 'unclassified'
            else:
                ed_decision = 'unknown'
        else:
            ed_decision = '-'

        if es_comment and es_comment.strip():
            if es_comment.startswith('accept:'):
                es_decision = 'accept'
            elif es_comment.startswith('reject:'):
                es_decision = 'reject'
            elif es_comment.startswith('finetune:'):
                es_decision = 'finetune'
            elif es_comment.startswith('unclassified:'):
                es_decision = 'unclassified'
            else:
                es_decision = 'unknown'
        else:
            es_decision = '-'

        # Count how many phases have comments
        comment_count = 0
        if ed_comment and ed_comment.strip():
            comment_count += 1
        if es_comment and es_comment.strip():
            comment_count += 1

        patient_list_with_status.append({
            'path': patient_path,
            'comment_status': f"{comment_count}/2",
            'ed_decision': ed_decision,
            'es_decision': es_decision
        })

    return jsonify({
        'status': 'success',
        'patients': patient_list_with_status,
        'total': len(PATIENT_LIST)
    })

@app.route('/api/qc_statistics')
def get_qc_statistics():
    """Get QC decision statistics for all patients"""
    stats = {
        'accept': 0,
        'reject': 0,
        'finetune': 0,
        'unclassified': 0,
        'no_decision': 0  # No comment at all
    }

    for patient_path in PATIENT_LIST:
        patient_info = PATIENT_DATA.get(patient_path, {})

        # Check both ED and ES phases
        for phase in ['ED', 'ES']:
            comment_key = f"{phase}_Comments"
            comment = patient_info.get(comment_key, '')

            if not comment or not comment.strip():
                stats['no_decision'] += 1
            elif comment.startswith('accept:'):
                stats['accept'] += 1
            elif comment.startswith('reject:'):
                stats['reject'] += 1
            elif comment.startswith('finetune:'):
                stats['finetune'] += 1
            elif comment.startswith('unclassified:'):
                stats['unclassified'] += 1
            else:
                # If format is unexpected, count as no decision
                stats['no_decision'] += 1

    # Calculate total and percentages
    total = sum(stats.values())
    percentages = {k: round((v / total * 100), 1) if total > 0 else 0 for k, v in stats.items()}

    return jsonify({
        'status': 'success',
        'statistics': stats,
        'percentages': percentages,
        'total': total
    })

@app.route('/api/goto_patient/<int:patient_index>')
def goto_patient(patient_index):
    """Jump to a specific patient by index"""
    if 0 <= patient_index < len(PATIENT_LIST):
        session['patient_index'] = patient_index
        return jsonify({
            'status': 'success',
            'patient_index': patient_index,
            'total_patients': len(PATIENT_LIST)
        })
    else:
        return jsonify({
            'status': 'error',
            'message': f'Invalid patient index. Must be between 0 and {len(PATIENT_LIST) - 1}'
        }), 400

@app.route('/api/save_qc', methods=['POST'])
def save_qc():
    """Save QC decision and comments to JSON file"""
    try:
        data = request.get_json()
        qc_comment = data.get('qc_comment', '')
        phase = data.get('phase', 'ED')

        # Get current patient
        patient_index = session.get('patient_index', 0)
        if patient_index < 0 or patient_index >= len(PATIENT_LIST):
            return jsonify({'status': 'error', 'message': 'Invalid patient index'}), 400

        patient_path = PATIENT_LIST[patient_index]
        comment_key = f"{phase}_Comments"

        # Update in-memory data
        if patient_path in PATIENT_DATA:
            PATIENT_DATA[patient_path][comment_key] = qc_comment
        else:
            return jsonify({'status': 'error', 'message': 'Patient not found in database'}), 404

        # Save to JSON file
        json_path = os.path.join(os.path.dirname(__file__), 'JSON', 'QC_logs.json')
        with open(json_path, 'w') as f:
            json.dump(PATIENT_DATA, f, indent=4)

        print(f"Saved QC comment for patient {patient_index} ({phase}): {qc_comment}")

        return jsonify({
            'status': 'success',
            'message': 'QC data saved successfully',
            'patient_index': patient_index,
            'phase': phase
        })

    except Exception as e:
        print(f"Error saving QC data: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'Error saving QC data: {str(e)}'
        }), 500

@app.route('/api/download_json')
def download_json():
    """Download the QC_logs.json file"""
    try:
        json_path = os.path.join(os.path.dirname(__file__), 'JSON', 'QC_logs.json')
        return send_file(
            json_path,
            mimetype='application/json',
            as_attachment=True,
            download_name='QC_logs.json'
        )
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error downloading JSON file: {str(e)}'
        }), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'CMR Segmentation QC Web App is running',
        'total_patients': len(PATIENT_LIST)
    })

if __name__ == '__main__':
    print("=" * 60)
    print("CMR Segmentation QC Web App")
    print("=" * 60)
    print("Starting server...")
    print("Open your browser and navigate to: http://localhost:5000")
    print("=" * 60)
    app.run(debug=False, host='0.0.0.0', port=5000)
