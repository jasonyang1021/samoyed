from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.core.config import settings
from app.db.models import Lab, LabInvitation, LabMembership, User
from sqlalchemy.orm import Session


def google_enabled() -> bool:
    return bool(settings.google_client_id and settings.google_client_secret)


def admin_emails() -> set[str]:
    return {email.strip().lower() for email in settings.admin_emails.split(",") if email.strip()}


def sync_user(db: Session, profile: dict) -> User:
    user_id = profile.get("sub")
    email = (profile.get("email") or "").lower()
    user = db.get(User, user_id) if user_id else None
    if user is None:
        user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(id=user_id, email=email, name=profile.get("name"), picture=profile.get("picture"))
        db.add(user)
    user.email = email
    user.name = profile.get("name")
    user.picture = profile.get("picture")
    user.role = "system_admin" if email in admin_emails() else (user.role if user.role in {"lab_admin", "lab_user"} else "guest")
    if user.role == "system_admin":
        for lab in db.query(Lab).all():
            membership = db.get(LabMembership, {"user_id": user.id, "lab_id": lab.id})
            if membership is None:
                db.add(LabMembership(user_id=user.id, lab_id=lab.id, role="lab_admin"))
    invitations = db.query(LabInvitation).filter(LabInvitation.email == email, LabInvitation.status == "pending").all()
    for invitation in invitations:
        membership = db.get(LabMembership, {"user_id": user.id, "lab_id": invitation.lab_id})
        if membership is None:
            db.add(LabMembership(user_id=user.id, lab_id=invitation.lab_id, role=invitation.role))
        invitation.status = "accepted"
    db.commit()
    db.refresh(user)
    return user


def session_profile(user: User) -> dict:
    return {"sub": user.id, "email": user.email, "name": user.name, "picture": user.picture, "role": user.role}


def google_state() -> str:
    return secrets.token_urlsafe(32)


def google_authorization_url(state: str) -> str:
    params = {
        "client_id": settings.google_client_id or "",
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "state": state,
        "prompt": "select_account",
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


def _google_request(url: str, data: bytes | None = None, headers: dict[str, str] | None = None) -> dict:
    request = Request(url, data=data, headers=headers or {}, method="POST" if data else "GET")
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def exchange_google_code(code: str) -> dict:
    body = urlencode({
        "code": code,
        "client_id": settings.google_client_id or "",
        "client_secret": settings.google_client_secret or "",
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }).encode("utf-8")
    token = _google_request("https://oauth2.googleapis.com/token", body, {"Content-Type": "application/x-www-form-urlencoded"})
    return _google_request("https://openidconnect.googleapis.com/v1/userinfo", headers={"Authorization": f"Bearer {token['access_token']}"})


def _encode(value: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode()).decode().rstrip("=")


def _decode(value: str) -> dict | None:
    try:
        return json.loads(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode())
    except (ValueError, json.JSONDecodeError):
        return None


def _secret() -> bytes:
    return (settings.google_client_secret or "local-development-session-secret").encode()


def create_session(user: dict) -> str:
    payload = {"sub": user.get("sub"), "email": user.get("email"), "name": user.get("name"), "picture": user.get("picture"), "role": "system_admin" if user.get("email", "").lower() in admin_emails() else "guest", "exp": int(time.time()) + 60 * 60 * 24 * 7}
    body = _encode(payload)
    signature = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def read_session(token: str | None) -> dict | None:
    if not token or "." not in token:
        return None
    body, signature = token.rsplit(".", 1)
    expected = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    payload = _decode(body)
    if not payload or payload.get("exp", 0) < time.time():
        return None
    return payload
