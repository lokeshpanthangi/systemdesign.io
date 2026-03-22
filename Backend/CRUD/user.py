from datetime import datetime
from typing import Optional
from passlib.context import CryptContext
from bson import ObjectId
from database.database import db
import bcrypt

password_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def is_bcrypt_hash(hash_str: str) -> bool:
    return isinstance(hash_str, str) and hash_str.startswith(("$2a$", "$2b$", "$2y$"))


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if is_bcrypt_hash(hashed_password):
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8")[:72],
                hashed_password.encode("utf-8"),
            )
        except Exception:
            return False
    try:
        return password_context.verify(plain_password, hashed_password)
    except Exception:
        return False


async def create_user(first_name: str, last_name: str, email: str, password: str) -> Optional[dict]:
    existing_user = await db.users.find_one({"email": email})
    if existing_user:
        return None

    user = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "password_hash": hash_password(password),
        "created_at": datetime.utcnow(),
    }

    result = await db.users.insert_one(user)
    user["_id"] = str(result.inserted_id)
    user.pop("password_hash", None)
    return user


async def authenticate_user(email: str, password: str) -> Optional[dict]:
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(password, user.get("password_hash", "")):
        return None

    user["_id"] = str(user["_id"])
    user.pop("password_hash", None)
    return user


async def get_user_by_email(email: str) -> Optional[dict]:
    user = await db.users.find_one({"email": email})
    if not user:
        return None

    user["_id"] = str(user["_id"])
    user.pop("password_hash", None)
    return user
