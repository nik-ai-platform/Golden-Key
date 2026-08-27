from pwdlib import PasswordHash


class HashingService:
    def __init__(self, password_hash=None):
        self._password_hash = password_hash or PasswordHash.recommended()


    def hash_password(self, password: str) -> str:
        return self._password_hash.hash(password)


    def verify_password(self, password: str, stored_hash: str) -> bool:
        return self._password_hash.verify(password, stored_hash)
