import json
import os

from config import QC_DECISIONS

# Reserved JSON top-level key holding non-patient metadata (schema_version,
# dataset_root). Schema v1 files omit it; v2+ files include it. The store
# strips it from `patient_data` so downstream code can treat the rest as a
# pure patient → info dict regardless of schema version.
META_KEY = '__meta__'


class QCStore:
    """Ordered patient database with JSON persistence for a single user + file.

    Construct with the absolute path to a user's QC JSON file. The file is read
    on init and re-read is not automatic — call reload() if the file changes
    externally. Not safe for concurrent writes, but since each file belongs to
    a single user, concurrent access is unlikely.

    Schema:
      - **v1 (legacy)**: top-level keys are ABSOLUTE patient paths.
        `path_at(i)` and `resolved_path(i)` return the same value.
      - **v2**: optional `__meta__: {dataset_root, schema_version}` sits at the
        top of the file; remaining keys are patient paths RELATIVE to
        `dataset_root`. `resolved_path(i)` joins them. Migrating a file in
        place lets you rename/move `/mnt/storage` without rewriting every key.

    Both schemas are read transparently; `_persist()` round-trips whichever
    schema the file was loaded with.
    """

    def __init__(self, json_path):
        self.json_path = json_path
        self.patient_data = {}
        self.patient_list = []
        self.dataset_root = None       # absolute prefix (v2); None means v1
        self.schema_version = 1
        self.reload()

    def reload(self):
        with open(self.json_path, 'r') as f:
            raw = json.load(f)
        meta = raw.pop(META_KEY, None) if isinstance(raw, dict) else None
        if isinstance(meta, dict):
            self.dataset_root = meta.get('dataset_root') or None
            self.schema_version = int(meta.get('schema_version', 2))
        else:
            self.dataset_root = None
            self.schema_version = 1
        self.patient_data = raw
        self.patient_list = list(self.patient_data.keys())

    def count(self):
        return len(self.patient_list)

    def path_at(self, index):
        """The patient's key as stored in the JSON file (may be relative)."""
        if 0 <= index < len(self.patient_list):
            return self.patient_list[index]
        return None

    def resolved_path(self, index):
        """Absolute filesystem path to the patient directory (for nifti loaders).

        v1 files: returns the key as-is (already absolute).
        v2 files: joins `dataset_root + key`.
        """
        key = self.path_at(index)
        if key is None:
            return None
        if self.dataset_root:
            return os.path.join(self.dataset_root, key)
        return key

    def info_at(self, index):
        path = self.path_at(index)
        if path is None:
            return None
        return self.patient_data.get(path, {})

    def set_comment(self, index, phase, comment):
        path = self.path_at(index)
        if path is None or path not in self.patient_data:
            return False
        self.patient_data[path][f"{phase}_Comments"] = comment
        self._persist()
        return True

    def _persist(self):
        # Re-emit __meta__ for v2 files so the schema round-trips. Order
        # matters: __meta__ first, then patients in original order — that way
        # patient_list (and patient_index) stays stable across save/load.
        out = {}
        if self.schema_version >= 2 or self.dataset_root:
            out[META_KEY] = {
                'schema_version': self.schema_version or 2,
                'dataset_root': self.dataset_root,
            }
        out.update(self.patient_data)
        # Atomic replace. A plain open('w') truncates the file first, so any
        # concurrent reader (save_qc and qc_statistics fire near-simultaneously
        # from the same browser) can catch it empty -> JSONDecodeError -> 500.
        # This actually happened ~5x during a heavy review session (2026-08-30).
        # Writing a sibling tmp file and os.replace()-ing it in keeps a complete
        # file visible to readers at every instant.
        tmp = self.json_path + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(out, f, indent=4)
        os.replace(tmp, self.json_path)


def parse_decision(comment):
    """Extract QC decision label from a '<decision>:<comments>' string.

    Returns '-' for empty comments, the matched decision, or 'unknown' if the
    prefix isn't one of the known decisions.
    """
    if not comment or not comment.strip():
        return '-'
    for decision in QC_DECISIONS:
        if comment.startswith(f"{decision}:"):
            return decision
    return 'unknown'
