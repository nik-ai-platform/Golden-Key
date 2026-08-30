from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from pwdlib.hashers.argon2 import Argon2Hasher
from pwdlib.hashers.bcrypt import BcryptHasher


DEFAULT_PASSWORD_HASH = PasswordHash((Argon2Hasher(), BcryptHasher()))


class HashingService:
    def __init__(self, password_hash=None):
        self._password_hash = password_hash or DEFAULT_PASSWORD_HASH


    def hash_password(self, password: str) -> str:
        return self._password_hash.hash(password)


    def verify_password(self, password: str, stored_hash: str) -> bool:
        try:
            return self._password_hash.verify(password, stored_hash)
        except (UnknownHashError, ValueError):
            return False
