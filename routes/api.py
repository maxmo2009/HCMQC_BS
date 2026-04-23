from flask import Blueprint, jsonify, request, send_file, session

from routes.auth import login_required
from services.patient import build_patient_payload, get_store_for_session
from services.qc_store import parse_decision
from services.users import list_qc_files, resolve_qc_path

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
