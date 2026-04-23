import json

from config import QC_DECISIONS


class QCStore:
    """Ordered patient database with JSON persistence for a single user + file.

    Construct with the absolute path to a user's QC JSON file. The file is read
    on init and re-read is not automatic — call reload() if the file changes
    externally. Not safe for concurrent writes, but since each file belongs to
    a single user, concurrent access is unlikely.
    """

    def __init__(self, json_path):
        self.json_path = json_path
        self.patient_data = {}
        self.patient_list = []
        self.reload()

    def reload(self):
        with open(self.json_path, 'r') as f:
            self.patient_data = json.load(f)
        self.patient_list = list(self.patient_data.keys())

    def count(self):
        return len(self.patient_list)

    def path_at(self, index):
        if 0 <= index < len(self.patient_list):
            return self.patient_list[index]
        return None

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
        with open(self.json_path, 'w') as f:
            json.dump(self.patient_data, f, indent=4)


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
