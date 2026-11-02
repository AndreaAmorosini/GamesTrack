"""Cifratura delle credenziali a riposo (campo api_key in platforms-users).

Usa Fernet (cryptography) con chiave da variabile d'ambiente
CREDENTIAL_ENCRYPTION_KEY. Per generarne una:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Comportamento degradato: se la libreria o la chiave non sono disponibili,
i valori passano in chiaro senza errori (compatibile con i dati esistenti).
La decifratura riconosce i token Fernet (prefisso "gAAAAA") e restituisce
inalterato qualsiasi valore non cifrato, così la migrazione è trasparente.
"""

import logging
import os

logger = logging.getLogger(__name__)

_FERNET = None
try:
    from cryptography.fernet import Fernet

    _key = os.getenv("CREDENTIAL_ENCRYPTION_KEY")
    if _key:
        _FERNET = Fernet(_key)
except ImportError:
    logger.warning(
        "Libreria 'cryptography' non disponibile: le credenziali saranno "
        "memorizzate in chiaro (aggiungila e configura CREDENTIAL_ENCRYPTION_KEY)"
    )

if _FERNET is None and os.getenv("CREDENTIAL_ENCRYPTION_KEY"):
    logger.warning(
        "CREDENTIAL_ENCRYPTION_KEY impostata ma non valida: le credenziali "
        "verranno memorizzate in chiaro"
    )


def encrypt_value(value):
    """Cifra un valore per la memorizzazione. None-safe, idempotente in degrado."""
    if value is None or _FERNET is None:
        return value
    try:
        return _FERNET.encrypt(str(value).encode()).decode()
    except Exception:
        logger.warning("Encryption failed, storing plaintext")
        return value


def decrypt_value(value):
    """Decifra un valore memorizzato. I valori non cifrati passano inalterati."""
    if value is None or _FERNET is None:
        return value
    if not isinstance(value, str) or not value.startswith("gAAAAA"):
        return value  # non cifrato (dato pre-esistente o degrado)
    try:
        return _FERNET.decrypt(value.encode()).decode()
    except Exception:
        logger.warning("Decryption failed: returning value as-is")
        return value
