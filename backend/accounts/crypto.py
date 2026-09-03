"""Encryption at rest for channel credentials (Fernet).

The key comes from CHANNEL_TOKEN_KEY; when unset it is derived from
SECRET_KEY so development works without extra config. Production should set
its own key so rotating SECRET_KEY does not orphan stored tokens.
"""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


def _fernet() -> Fernet:
    key = getattr(settings, "CHANNEL_TOKEN_KEY", "") or ""
    if not key:
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest()).decode()
    return Fernet(key)


class EncryptedTextField(models.TextField):
    """TextField whose value is stored encrypted. Not searchable, by design."""

    description = "Text encrypted at rest"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if not value:
            return value
        return _fernet().encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        try:
            return _fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            # Key changed or row corrupted: treat as no credential; the owner re-connects.
            logger.warning("Could not decrypt a stored channel credential")
            return ""
