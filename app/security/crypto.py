from cryptography.fernet import Fernet

class CryptoBox:
    def __init__(self, fernet_key: str):
        # fernet_key debe ser urlsafe base64-encoded 32-byte key
        self._f = Fernet(fernet_key.encode("utf-8"))

    def encrypt(self, plain: str) -> str:
        token = self._f.encrypt(plain.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, token: str) -> str:
        data = self._f.decrypt(token.encode("utf-8"))
        return data.decode("utf-8")
