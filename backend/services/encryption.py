"""
Cifrado de campos sensibles — LOPDP Art. 26 (datos de salud = datos sensibles).
Usa Fernet (AES-128-CBC + HMAC-SHA256). Clave rotable via FERNET_KEY en .env.
"""
import json
import hashlib
from cryptography.fernet import Fernet
from config import settings

_fernet = Fernet(settings.fernet_key.encode())


def encrypt(data: dict | list | str) -> bytes:
    # Cualquier estructura JSON-serializable (dict, list, ...) se serializa;
    # las cadenas se cifran tal cual. Antes solo manejaba dict → list.encode()
    # lanzaba AttributeError y rompía la persistencia de conversaciones.
    if not isinstance(data, str):
        data = json.dumps(data, ensure_ascii=False, default=str)
    return _fernet.encrypt(data.encode("utf-8"))


def decrypt(ciphertext: bytes) -> dict:
    plaintext = _fernet.decrypt(ciphertext).decode("utf-8")
    try:
        return json.loads(plaintext)
    except json.JSONDecodeError:
        return {"raw": plaintext}


def encrypt_str(value: str) -> bytes:
    return _fernet.encrypt(value.encode("utf-8"))


def decrypt_str(ciphertext: bytes) -> str:
    return _fernet.decrypt(ciphertext).decode("utf-8")


def hash_identifier(value: str) -> str:
    """SHA-256 de un identificador sensible (IP, número de póliza, etc.).
    Permite indexar sin exponer datos personales — pseudonimización LOPDP Art. 19."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
