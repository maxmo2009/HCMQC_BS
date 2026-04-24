import os
from datetime import timedelta

SECRET_KEY = 'cmr_qc_secret_key_12345'
SESSION_LIFETIME = timedelta(days=3)

BASE_PATH = ''

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
JSON_DIR = os.path.join(PROJECT_ROOT, 'JSON')
USERS_JSON_PATH = os.path.join(JSON_DIR, 'users.json')
USERS_DIR = os.path.join(JSON_DIR, 'users')

HOST = '0.0.0.0'
PORT = 5000
DEBUG = False

LABEL_COLOR_MAP = {
    0: (0, 0, 0),
    1: (255, 0, 0),
    2: (0, 255, 0),
    3: (0, 136, 255),
}

QC_DECISIONS = ('accept', 'reject', 'finetune', 'unclassified')


def user_dir(username):
    return os.path.join(USERS_DIR, username)


def user_qc_file(username, filename):
    return os.path.join(USERS_DIR, username, filename)
