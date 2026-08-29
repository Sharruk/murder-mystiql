from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import jwt
from fastapi import Header, HTTPException, Request, status

from backend.app.config import get_settings
from backend.app.models import Participant

logger = logging.getLogger("murder_mystiql.auth")

_firebase_initialized = False


def init_firebase_admin() -> bool:
    """Initialize Firebase Admin SDK using environment variables or local service account file."""
    global _firebase_initialized
    if _firebase_initialized:
        return True

    try:
        import firebase_admin
        from firebase_admin import credentials

        if firebase_admin._apps:
            _firebase_initialized = True
            return True

        settings = get_settings()

        # 1. Try Environment Variables (Vercel / Production)
        if settings.firebase_client_email and settings.firebase_private_key:
            pk = settings.firebase_private_key.replace("\\n", "\n")
            cred_dict = {
                "type": "service_account",
                "project_id": settings.firebase_project_id or "murder-mystiql",
                "client_email": settings.firebase_client_email,
                "private_key": pk,
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("Firebase Admin initialized via environment credentials.")
            return True

        # 2. Try configured path or local service account JSON in workspace
        candidate_paths: list[Path] = []
        if settings.firebase_service_account_path:
            candidate_paths.append(Path(settings.firebase_service_account_path))

        # Root workspace files matching *firebase-adminsdk*.json
        root_dir = Path(__file__).resolve().parent.parent.parent
        candidate_paths.extend(root_dir.glob("*firebase-adminsdk*.json"))
        candidate_paths.extend(root_dir.glob("credentials*.json"))

        for p in candidate_paths:
            if p.is_file():
                try:
                    cred = credentials.Certificate(str(p))
                    firebase_admin.initialize_app(cred)
                    _firebase_initialized = True
                    logger.info(f"Firebase Admin initialized from {p.name}")
                    return True
                except Exception as ex:
                    logger.warning(f"Failed to load Firebase credential from {p}: {ex}")

        # 3. Default Application Credentials fallback
        try:
            firebase_admin.initialize_app()
            _firebase_initialized = True
            logger.info("Firebase Admin initialized with default credentials.")
            return True
        except Exception as ex:
            logger.warning(f"Could not initialize default Firebase credentials: {ex}")

    except ImportError:
        logger.warning("firebase_admin library is not installed.")

    return False


def verify_firebase_id_token(id_token: str) -> dict[str, Any]:
    """Cryptographically verify Firebase ID token and enforce @ssn.edu.in institutional check."""
    init_firebase_admin()
    import firebase_admin.auth

    try:
        decoded = firebase_admin.auth.verify_id_token(id_token, check_revoked=False)
    except Exception as err:
        logger.warning(f"Firebase token verification failed: {err}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": f"Invalid or expired Firebase ID token: {err}"},
        )

    # 1. Verify email verified
    email_verified = decoded.get("email_verified", False)
    if not email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "email_unverified", "message": "Email address must be verified in Google/Firebase."},
        )

    # 2. Strict @ssn.edu.in domain verification
    raw_email = decoded.get("email") or ""
    email = raw_email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "invalid_email", "message": "Invalid email address in token."},
        )

    parts = email.split("@")
    if len(parts) != 2 or parts[1] != "ssn.edu.in":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "invalid_domain",
                "message": "Only verified SSN institutional accounts (@ssn.edu.in) can participate in MURDER MYSTIQL.",
            },
        )

    return decoded


def create_session_jwt(participant: Participant) -> str:
    """Create a signed JWT session token for authenticated SSN participant."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": participant.firebase_uid,
        "participant_id": participant.id,
        "email": participant.email,
        "name": participant.display_name,
        "is_qualified": participant.is_qualified,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=24)).timestamp()),
    }
    return jwt.encode(payload, settings.session_secret, algorithm="HS256")


def decode_session_jwt(token: str) -> dict[str, Any]:
    """Decode and validate application session JWT."""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.session_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "token_expired", "message": "Session token has expired. Please sign in again."},
        )
    except jwt.PyJWTError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": f"Invalid session token: {err}"},
        )
