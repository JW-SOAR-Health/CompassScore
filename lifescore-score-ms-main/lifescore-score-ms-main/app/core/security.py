"""
Security and authentication utilities for a FastAPI application.

This module provides functions for password hashing, JWT token creation,
verification, and third-party authentication with Apple. It includes:

- Password hashing and verification using `passlib`.
- JWT creation, encoding, decoding, and verification using `jose`.
- Apple ID token verification with public keys from Apple's servers.
- User retrieval and validation from JWT tokens.

Dependencies:
- `fastapi`, `jose`, `passlib`, `requests`, `uuid`
- `app.shared_db`: SQLAlchemy models (`User`, `Pii`) and database management.
- `app.core.responses`: Response handlers for consistent API responses.

Ensure environment variables like `JWT_SECRET`, `ALGORITHM`,
`APPLE_PUBLIC_KEY`, and `APPLE_CLIENT_ID` are set correctly.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt, jwk
from jose.utils import base64url_decode
from passlib.context import CryptContext
import requests
from app.shared_db.models.users import User
from app.shared_db.models.piis import Pii as Piis
from app.shared_db.database import get_db
from app.shared_db.config import settings
from app.core.responses import response_handler
import sentry_sdk

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify if the provided plain password matches the hashed password.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hashes the given password using passlib.
    """
    return pwd_context.hash(password)


async def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    """
    Creates a new JWT access token.
    """
    if not settings.JWT_SECRET:
        raise ValueError("JWT_SECRET is not set in settings.")

    if not settings.ALGORITHM:
        raise ValueError("ALGORITHM is not set in settings.")
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


async def create_refresh_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    """
    Creates a new JWT refresh token.
    """
    if not settings.JWT_SECRET:
        raise ValueError("JWT_SECRET is not set in settings.")

    if not settings.ALGORITHM:
        raise ValueError("ALGORITHM is not set in settings.")

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=4320)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def get_token_payload(token: str) -> Optional[dict]:
    """
    Decodes the given JWT token to extract its payload.
    """
    if not settings.JWT_SECRET:
        raise ValueError("JWT_SECRET is not set in settings.")

    if not settings.ALGORITHM:
        raise ValueError("ALGORITHM is not set in settings.")

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        print("JWTError", token)
        return None
    return payload


async def verify_apple_token(token: str, db=None) -> dict:
    """
    Verifies the given Apple token using the Apple public key.
    """
    if not settings.APPLE_PUBLIC_KEY:
        raise ValueError("APPLE_PUBLIC_KEY is not set in settings.")

    if not settings.APPLE_CLIENT_ID:
        raise ValueError("APPLE_CLIENT_ID is not set in settings.")

    try:
        # Fetch Apple's public keys
        apple_key_url = "https://appleid.apple.com/auth/keys"
        keys_response = requests.get(apple_key_url, timeout=5)
        keys = keys_response.json().get("keys", [])

        # Decode the JWT token without verification to extract the header
        headers = jwt.get_unverified_header(token)
        kid = headers.get("kid")

        # Find the key with a matching 'kid'
        matching_key = next((key for key in keys if key["kid"] == kid), None)
        if not matching_key:
            raise response_handler.unauthorized("Invalid key ID")

        # Construct the public key from Apple's JWK
        public_key = jwk.construct(matching_key)

        # Extract the token's signature and message
        message, encoded_signature = str(token).rsplit(".", 1)
        decoded_signature = base64url_decode(encoded_signature.encode("utf-8"))

        # Verify the signature
        if not public_key.verify(message.encode("utf-8"), decoded_signature):
            raise response_handler.unauthorized("Invalid signature")

        # Decode the token
        decoded_token = jwt.decode(
            token,
            public_key.to_pem().decode("utf-8"),
            algorithms=["RS256"],
            audience=settings.APPLE_CLIENT_ID,
        )

        user_email = decoded_token.get("email")
        if not user_email:
            raise response_handler.unauthorized("Could not validate credentials")

        # Initialize db if not provided
        if not db:
            db = next(get_db())

        user = db.query(Piis).filter(Piis.email == user_email).first()
        if user is None:
            raise response_handler.unauthorized("User does not exist")

        return {"user_id": str(user.user_id)}

    except Exception as e:
        raise response_handler.unauthorized(f"Error verifying token: {e}")


async def get_current_user(token: str = Depends(oauth2_scheme), db=None) -> User:
    """
    Retrieves the current user based on the provided JWT token.
    """
    if not settings.JWT_SECRET:
        raise ValueError("JWT_SECRET is not set in settings.")

    if not settings.ALGORITHM:
        raise ValueError("ALGORITHM is not set in settings.")
    try:
        payload = get_token_payload(token)
        if not payload:
            print("payload is none")
            raise response_handler.unauthorized("Could not validate credentials")

        user_id = payload.get("id")
        if not user_id:
            print("user_id is none")
            raise response_handler.unauthorized("Could not validate credentials")

        user_id = UUID(user_id)

    except ExpiredSignatureError as exc:
        raise response_handler.unauthorized("Expired Token") from exc
    except (JWTError, ValueError) as exc:
        raise response_handler.unauthorized("JWT Error") from exc

    # Initialize db if not provided
    if not db:
        db = next(get_db())

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise response_handler.unauthorized("User does not exist")
    sentry_sdk.set_user({"id": str(user.id), "email": user.pii.email})
    return user
