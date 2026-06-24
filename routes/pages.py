import json

from flask import Blueprint, jsonify, render_template, send_from_directory, session

from routes.auth import admin_required, login_required
from services.docs import DOCS_ROOT
from services.patient import build_patient_payload, get_store_for_session
from services.users import list_qc_files

pages_bp = Blueprint('pages', __name__)


def _empty_render(username, files, active):
    """Render index.html with empty data when no dataset is active yet."""
    return render_template(
        'index.html',
        username=username,
        qc_files=json.dumps(files),
        active_qc_file=active or '',
        patient_index=0,
        patient_path='',
        patient_info=json.dumps({}),
        phase=session.get('phase', 'ED'),
        qc_comment='',
        mri_slices=json.dumps([]),
        seg_slices=json.dumps([]),
        seg_coords=json.dumps([]),
        seg_labels=json.dumps([]),
        seg_shape=[0, 0, 0],
        seg_spacing=[1.0, 1.0, 1.0],
        total_patients=0,
    )


@pages_bp.route('/')
@login_required
def index():
    username = session['username']
    files = list_qc_files(username)

    # Auto-pick first file if user has files but none selected yet.
    if not session.get('active_qc_file') and files:
        session['active_qc_file'] = files[0]
        session['patient_index'] = 0

    # Drop stale selection if the file was removed from the folder.
    if session.get('active_qc_file') and session['active_qc_file'] not in files:
        session.pop('active_qc_file', None)
        session['patient_index'] = 0

    active = session.get('active_qc_file')
    store = get_store_for_session(session)

    if store is None:
        return _empty_render(username, files, active)

    session.setdefault('phase', 'ED')
    payload = build_patient_payload(store, session.get('patient_index', 0), session['phase'])

    if payload is None:
        return _empty_render(username, files, active)

    qc_comment = payload['patient_info'].get(f"{payload['phase']}_Comments", '')

    return render_template(
        'index.html',
        username=username,
        qc_files=json.dumps(files),
        active_qc_file=active,
        patient_index=payload['patient_index'],
        patient_path=payload['patient_path'],
        patient_info=json.dumps(payload['patient_info']),
        phase=payload['phase'],
        qc_comment=qc_comment,
        mri_slices=json.dumps(payload['mri_slices']),
        seg_slices=json.dumps(payload['seg_slices']),
        seg_coords=json.dumps(payload['seg_coords']),
        seg_labels=json.dumps(payload['seg_labels']),
        seg_shape=payload['seg_shape'],
        seg_spacing=payload['seg_spacing'],
        total_patients=payload['total_patients'],
    )


@pages_bp.route('/docs')
@login_required
def docs():
    """Viewer page for the generated team document (rendered client-side)."""
    return render_template('docs.html', username=session['username'])


@pages_bp.route('/docs/file/<path:filename>')
@login_required
def docs_file(filename):
    """Serve any document's markdown + image assets (login-gated — patient-derived).

    `filename` is reports-relative (e.g. `hulei_acdc_discussion/report.md` or
    `.../imgs/x.png`); send_from_directory's safe_join blocks path traversal.
    """
    return send_from_directory(DOCS_ROOT, filename)


@pages_bp.route('/files')
@admin_required
def files():
    """File System — admin-only NIfTI browser + multi-pane 3D segmentation viewer."""
    return render_template('files.html', username=session['username'])


@pages_bp.route('/admin')
@admin_required
def admin_tools():
    """Admin Tools — manage users + per-user QC-file visibility (admin-only)."""
    return render_template('admin.html', username=session['username'])


@pages_bp.route('/health')
def health():
    return jsonify({'status': 'ok', 'message': 'Cardiac Segmentation QC Studio is running'})
