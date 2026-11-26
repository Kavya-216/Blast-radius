import hashlib
import hmac


def verify_github_signature(secret: str, raw_body: bytes, signature_header: str | None) -> bool:
    if not secret or not signature_header or not signature_header.startswith("sha256="):
        return False
    supplied = signature_header.removeprefix("sha256=")
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, supplied)
