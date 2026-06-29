import os

from flask import Blueprint, jsonify, request, send_file, session

from routes.auth import admin_required, login_required
from services.docs import (
    create_doc,
    delete_doc,
    list_docs,
    save_doc,
    save_doc_image,
)
from services.filebrowser import is_nifti, list_dir, resolve
from services.mesh_loader import load_patient_meshes
from services.nifti_loader import load_nifti_voxels
from services.patient import build_patient_payload, get_store_for_session
from services.qc_store import parse_decision
from services.users import (
    add_user,
    admin_overview,
    delete_user,
    list_qc_files,
    resolve_qc_path,
    set_file_visibility,
    set_password,
)

api_bp = Blueprint('api', __name__, url_prefix='/api')


def _store_or_404():
    """Resolve the per-user store or return a JSON 404 response tuple."""
    store = get_store_for_session(session)
    if store is None:
        return None, (jsonify({
            'status': 'error',
            'message': 'No active dataset selected',
        }), 404)
    return store, None


@api_bp.route('/list_qc_files')
@login_required
def api_list_qc_files():
    files = list_qc_files(session['username'])
    return jsonify({
        'status': 'success',
        'files': files,
        'active': session.get('active_qc_file'),
    })


@api_bp.route('/docs')
@login_required
def api_docs():
    """List the markdown documents available to the /docs viewer."""
    return jsonify({'status': 'success', 'docs': list_docs()})


# ── Document editing (any logged-in user; docs are shared) ──────────────────
@api_bp.route('/docs/save', methods=['POST'])
@login_required
def api_docs_save():
    """Overwrite an existing doc's markdown. Body: {file, content}."""
    data = request.get_json(silent=True) or {}
    ok, msg = save_doc(data.get('file'), data.get('content'))
    if not ok:
        return jsonify({'status': 'error', 'message': msg}), 400
    return jsonify({'status': 'success'})


@api_bp.route('/docs/create', methods=['POST'])
@login_required
def api_docs_create():
    """Create a new blank document. Body: {title}. Returns the doc record."""
    data = request.get_json(silent=True) or {}
    ok, res = create_doc(data.get('title'))
    if not ok:
        return jsonify({'status': 'error', 'message': res}), 400
    return jsonify({'status': 'success', 'doc': res})


@api_bp.route('/docs/delete', methods=['POST'])
@login_required
def api_docs_delete():
    """Delete an entire document folder. Body: {dir}."""
    data = request.get_json(silent=True) or {}
    ok, msg = delete_doc(data.get('dir'))
    if not ok:
        return jsonify({'status': 'error', 'message': msg}), 400
    return jsonify({'status': 'success'})


@api_bp.route('/docs/image', methods=['POST'])
@login_required
def api_docs_image():
    """Upload an image into a doc's imgs/ folder. Multipart: dir=<rel>, image=<file>.
    Returns the doc-relative path ('imgs/<name>') to insert into the markdown."""
    dir_rel = request.form.get('dir')
    f = request.files.get('image')
    if f is None:
        return jsonify({'status': 'error', 'message': 'no image uploaded'}), 400
    ok, res = save_doc_image(dir_rel, f.filename, f.read())
    if not ok:
        return jsonify({'status': 'error', 'message': res}), 400
    return jsonify({'status': 'success', 'path': res})


@api_bp.route('/set_qc_file/<path:filename>')
@login_required
def set_qc_file(filename):
    path = resolve_qc_path(session['username'], filename)
    if path is None:
        return jsonify({'status': 'error', 'message': 'File not found'}), 404
    session['active_qc_file'] = filename
    session['patient_index'] = 0
    return jsonify({'status': 'success', 'active': filename})


@api_bp.route('/next_patient')
@login_required
def next_patient():
    store, err = _store_or_404()
    if err: return err
    new_index = (session.get('patient_index', 0) + 1) % store.count()
    session['patient_index'] = new_index
    return jsonify({
        'status': 'success',
        'patient_index': new_index,
        'total_patients': store.count(),
    })


@api_bp.route('/prev_patient')
@login_required
def prev_patient():
    store, err = _store_or_404()
    if err: return err
    new_index = (session.get('patient_index', 0) - 1) % store.count()
    session['patient_index'] = new_index
    return jsonify({
        'status': 'success',
        'patient_index': new_index,
        'total_patients': store.count(),
    })


@api_bp.route('/set_phase/<phase>')
@login_required
def set_phase(phase):
    if phase in ('ED', 'ES'):
        session['phase'] = phase
        return jsonify({'status': 'success', 'phase': phase})
    return jsonify({
        'status': 'error',
        'message': 'Invalid phase. Must be ED or ES',
    }), 400


@api_bp.route('/patient_data')
@login_required
def get_patient_data():
    store, err = _store_or_404()
    if err: return err
    payload = build_patient_payload(
        store,
        session.get('patient_index', 0),
        session.get('phase', 'ED'),
    )
    if payload is None:
        return jsonify({'status': 'error', 'message': 'Patient data not found'}), 404
    return jsonify({'status': 'success', 'data': payload})


@api_bp.route('/meshes/<int:patient_index>')
@login_required
def get_patient_meshes(patient_index):
    """Fitted template-mesh geometry for a patient/phase, for 3D overlay.

    Returns voxel-space vertices + triangle faces per region (LVendo/LVepi/
    LVmyo/RV), or {'available': False} when the patient has no vtks/ folder.
    Loaded lazily (meshes are large) — the viewer fetches this only when the
    mesh overlay is switched on.
    """
    store, err = _store_or_404()
    if err: return err
    patient_path = store.resolved_path(patient_index)
    if patient_path is None:
        return jsonify({'status': 'error', 'message': 'Invalid patient index'}), 404
    # Validate phase: it is interpolated into seg/vtk filenames, so an
    # unconstrained value (e.g. 'ES/../../etc/x') would escape the patient dir.
    phase = request.args.get('phase', session.get('phase', 'ED'))
    if phase not in ('ED', 'ES'):
        return jsonify({'status': 'error', 'message': "phase must be 'ED' or 'ES'"}), 400
    # Guard against loader failures (singular/degenerate affine -> inv() raises,
    # unreadable NIfTI, malformed VTK) so a bad case degrades instead of 500ing.
    try:
        data = load_patient_meshes(patient_path, phase)
    except Exception as exc:
        print(f"get_patient_meshes: {patient_path} {phase}: {exc}")
        return jsonify({'status': 'error', 'message': 'Failed to load meshes',
                        'available': False, 'regions': {}}), 500
    return jsonify({'status': 'success', 'phase': phase, **data})


@api_bp.route('/patient_list')
@login_required
def get_patient_list():
    store, err = _store_or_404()
    if err: return err
    patients = []
    for patient_path in store.patient_list:
        info = store.patient_data.get(patient_path, {})
        ed_comment = info.get('ED_Comments', '')
        es_comment = info.get('ES_Comments', '')
        comment_count = sum(1 for c in (ed_comment, es_comment) if c and c.strip())
        patients.append({
            'path': patient_path,
            'comment_status': f"{comment_count}/2",
            'ed_decision': parse_decision(ed_comment),
            'es_decision': parse_decision(es_comment),
        })
    return jsonify({
        'status': 'success',
        'patients': patients,
        'total': store.count(),
    })


@api_bp.route('/qc_statistics')
@login_required
def get_qc_statistics():
    store, err = _store_or_404()
    if err: return err
    stats = {'accept': 0, 'reject': 0, 'finetune': 0, 'unclassified': 0, 'no_decision': 0}
    for patient_path in store.patient_list:
        info = store.patient_data.get(patient_path, {})
        for phase in ('ED', 'ES'):
            decision = parse_decision(info.get(f"{phase}_Comments", ''))
            if decision in ('-', 'unknown'):
                stats['no_decision'] += 1
            else:
                stats[decision] += 1
    total = sum(stats.values())
    percentages = {k: round((v / total * 100), 1) if total > 0 else 0 for k, v in stats.items()}
    return jsonify({
        'status': 'success',
        'statistics': stats,
        'percentages': percentages,
        'total': total,
    })


@api_bp.route('/goto_patient/<int:patient_index>')
@login_required
def goto_patient(patient_index):
    store, err = _store_or_404()
    if err: return err
    if 0 <= patient_index < store.count():
        session['patient_index'] = patient_index
        return jsonify({
            'status': 'success',
            'patient_index': patient_index,
            'total_patients': store.count(),
        })
    return jsonify({
        'status': 'error',
        'message': f'Invalid patient index. Must be between 0 and {store.count() - 1}',
    }), 400


@api_bp.route('/save_qc', methods=['POST'])
@login_required
def save_qc():
    store, err = _store_or_404()
    if err: return err
    try:
        data = request.get_json()
        qc_comment = data.get('qc_comment', '')
        phase = data.get('phase', 'ED')
        patient_index = session.get('patient_index', 0)
        if patient_index < 0 or patient_index >= store.count():
            return jsonify({'status': 'error', 'message': 'Invalid patient index'}), 400
        if not store.set_comment(patient_index, phase, qc_comment):
            return jsonify({'status': 'error', 'message': 'Patient not found in database'}), 404
        return jsonify({
            'status': 'success',
            'message': 'QC data saved successfully',
            'patient_index': patient_index,
            'phase': phase,
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error saving QC data: {str(e)}',
        }), 500


@api_bp.route('/fs/list')
@admin_required
def fs_list():
    """List directories + NIfTI files under a path (admin-only, confined to FILES_ROOT)."""
    result = list_dir(request.args.get('path', ''))
    if result is None:
        return jsonify({'status': 'error', 'message': 'Invalid or inaccessible path'}), 404
    return jsonify({'status': 'success', **result})


@api_bp.route('/fs/nifti')
@admin_required
def fs_nifti():
    """Load a NIfTI file's segmentation voxels for the 3D viewer (admin-only)."""
    abs_path = resolve(request.args.get('path', ''))
    if abs_path is None or not os.path.isfile(abs_path):
        return jsonify({'status': 'error', 'message': 'File not found'}), 404
    if not is_nifti(abs_path):
        return jsonify({'status': 'error', 'message': 'Not a NIfTI file'}), 400
    # nib.load raises ImageFileError on corrupt/truncated files; surface as a
    # structured 422 the frontend's describeError() can render, not a 500 HTML.
    try:
        result = load_nifti_voxels(abs_path)
    except Exception as exc:
        return jsonify({
            'status': 'error', 'message': 'load_failed', 'detail': str(exc),
        }), 422
    if 'error' in result:
        return jsonify({'status': 'error', 'message': result['error'], **result}), 422
    return jsonify({'status': 'success', 'name': os.path.basename(abs_path), **result})


@api_bp.route('/admin/overview')
@admin_required
def api_admin_overview():
    """All users + their QC files + per-file visibility (admin-only)."""
    return jsonify({'status': 'success', 'users': admin_overview()})


@api_bp.route('/admin/visibility', methods=['POST'])
@admin_required
def api_admin_visibility():
    """Show/hide one user's QC file. Body: {username, filename, visible}."""
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    filename = data.get('filename')
    visible = bool(data.get('visible'))
    if not username or not filename:
        return jsonify({'status': 'error', 'message': 'username and filename required'}), 400
    if not set_file_visibility(username, filename, visible):
        return jsonify({'status': 'error', 'message': 'File not found in that user\'s folder'}), 404
    return jsonify({'status': 'success', 'username': username, 'filename': filename, 'visible': visible})


@api_bp.route('/admin/user', methods=['POST'])
@admin_required
def api_admin_create_user():
    """Create a user + empty data folder. Body: {username, password}."""
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    ok, msg = add_user(username, password)
    if not ok:
        return jsonify({'status': 'error', 'message': msg}), 400
    return jsonify({'status': 'success', 'username': username})


@api_bp.route('/admin/user/password', methods=['POST'])
@admin_required
def api_admin_set_password():
    """Change a user's password. Body: {username, password}."""
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    password = data.get('password') or ''
    ok, msg = set_password(username, password)
    if not ok:
        return jsonify({'status': 'error', 'message': msg}), (404 if msg == 'user not found' else 400)
    return jsonify({'status': 'success', 'username': username})


@api_bp.route('/admin/user/delete', methods=['POST'])
@admin_required
def api_admin_delete_user():
    """Delete a user. Body: {username, delete_data}. Admin account is protected."""
    data = request.get_json(silent=True) or {}
    username = data.get('username')
    delete_data = bool(data.get('delete_data'))
    ok, msg = delete_user(username, delete_data)
    if not ok:
        return jsonify({'status': 'error', 'message': msg}), (404 if msg == 'user not found' else 400)
    return jsonify({'status': 'success', 'username': username, 'deleted_data': delete_data})


@api_bp.route('/download_json')
@login_required
def download_json():
    store, err = _store_or_404()
    if err: return err
    try:
        return send_file(
            store.json_path,
            mimetype='application/json',
            as_attachment=True,
            download_name=session['active_qc_file'],
        )
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error downloading JSON file: {str(e)}',
        }), 500
