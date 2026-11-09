import base64
from Crypto.Cipher import AES

# Key and IV extracted from Palantir 3 resolver module
_RAW_SECRET = b"hTh8uRnL5bX8PZC6Tc3t46nVDFfBpB6Tjw3qazQThpexpg8bLdimevNHj5vJR0nP"
_DECODED_SECRET = base64.b64decode(_RAW_SECRET)
AES_IV = _DECODED_SECRET[:16]
AES_KEY = _DECODED_SECRET[16:]

def decrypt_palantir_url(encrypted_url: str) -> str:
    """
    Decrypts an encrypted Palantir link (AES-128 OFB mode, URL-safe base64 encoded).
    """
    if not encrypted_url:
        return ""
    if encrypted_url.startswith("http://") or encrypted_url.startswith("https://"):
        return encrypted_url
    
    try:
        cipher = AES.new(AES_KEY, AES.MODE_OFB, AES_IV)
        decoded_b64 = base64.urlsafe_b64decode(encrypted_url)
        decrypted_bytes = cipher.decrypt(decoded_b64)
        return decrypted_bytes.decode("utf-8", errors="ignore").strip()
    except Exception as e:
        # Return empty on failure
        return ""
