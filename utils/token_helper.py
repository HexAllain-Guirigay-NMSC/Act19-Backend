import secrets
from datetime import datetime, timedelta


def generate_token():
    return secrets.token_hex(32)


def get_expiry(hours=24):
    return datetime.now() + timedelta(hours=hours)