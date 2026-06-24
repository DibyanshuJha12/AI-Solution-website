from __future__ import annotations

import hashlib
import json
import re
import secrets
import urllib.parse
import urllib.request
from datetime import timedelta
from pathlib import Path

from flask import current_app, request, session
from werkzeug.utils import secure_filename

from ..models import utcnow


TAG_RE = re.compile(r"<[^>]*>")


def sanitize_text(value: str | None, *, max_length: int = 2000, preserve_newlines: bool = False) -> str:
    if not value:
        return ""
    cleaned = TAG_RE.sub("", value)
    if preserve_newlines:
        normalized_lines = []
        for line in cleaned.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            normalized_lines.append(re.sub(r"[ \t]+", " ", line).strip())
        cleaned = "\n".join(normalized_lines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    else:
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:max_length]


def allowed_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_RESUME_EXTENSIONS"]


def allowed_media_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_MEDIA_EXTENSIONS"]


def secure_resume_filename(filename: str) -> str:
    safe = secure_filename(filename)
    suffix = Path(safe).suffix.lower()
    return f"{secrets.token_hex(12)}{suffix}"


def secure_media_filename(filename: str) -> str:
    safe = secure_filename(filename)
    suffix = Path(safe).suffix.lower()
    return f"{secrets.token_hex(12)}{suffix}"


def client_ip() -> str:
    return (request.headers.get("X-Forwarded-For", request.remote_addr) or "")[:80]


def parse_user_agent(user_agent: str | None) -> dict[str, str]:
    agent = (user_agent or "").lower()

    if "edg" in agent:
        browser = "Microsoft Edge"
    elif "chrome" in agent and "chromium" not in agent:
        browser = "Chrome"
    elif "firefox" in agent:
        browser = "Firefox"
    elif "safari" in agent and "chrome" not in agent:
        browser = "Safari"
    elif "opr/" in agent or "opera" in agent:
        browser = "Opera"
    else:
        browser = "Unknown Browser"

    if "windows" in agent:
        operating_system = "Windows"
    elif "mac os" in agent or "macintosh" in agent:
        operating_system = "macOS"
    elif "android" in agent:
        operating_system = "Android"
    elif "iphone" in agent or "ipad" in agent or "ios" in agent:
        operating_system = "iOS"
    elif "linux" in agent:
        operating_system = "Linux"
    else:
        operating_system = "Unknown OS"

    if any(token in agent for token in ("mobile", "iphone", "android")):
        device = "Mobile"
    elif "ipad" in agent or "tablet" in agent:
        device = "Tablet"
    else:
        device = "Desktop"

    return {
        "browser": browser,
        "operating_system": operating_system,
        "device": device,
    }


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session_identifier() -> str:
    return secrets.token_urlsafe(32)


def _captcha_store() -> dict[str, dict]:
    store = session.get("numeric_captcha", {})
    if not isinstance(store, dict):
        store = {}
    return store


def build_numeric_captcha(scope: str, *, refresh: bool = False) -> dict[str, str]:
    store = _captcha_store()
    existing = store.get(scope)
    created_at = existing.get("created_at") if isinstance(existing, dict) else None
    if existing and not refresh and created_at:
        try:
            age = utcnow().timestamp() - float(created_at)
        except Exception:
            age = 9999
        if age < 600:
            return {"prompt": existing["prompt"], "scope": scope}

    left = secrets.randbelow(9) + 2
    right = secrets.randbelow(8) + 1
    if secrets.randbelow(2):
        prompt = f"{left} + {right}"
        answer = str(left + right)
    else:
        left = max(left, right + 1)
        prompt = f"{left} - {right}"
        answer = str(left - right)

    store[scope] = {
        "prompt": prompt,
        "answer": answer,
        "created_at": str(utcnow().timestamp()),
    }
    session["numeric_captcha"] = store
    session.modified = True
    return {"prompt": prompt, "scope": scope}


def verify_numeric_captcha(scope: str, answer: str | None) -> tuple[bool, str]:
    store = _captcha_store()
    challenge = store.get(scope)
    if not challenge:
        build_numeric_captcha(scope, refresh=True)
        return False, "Security check expired. Please try again."

    expected = str(challenge.get("answer", "")).strip()
    supplied = sanitize_text(answer or "", max_length=20)
    try:
        created_at = float(challenge.get("created_at", 0))
    except (TypeError, ValueError):
        build_numeric_captcha(scope, refresh=True)
        return False, "Security check expired. Please try again."
    if utcnow().timestamp() - created_at > 600:
        build_numeric_captcha(scope, refresh=True)
        return False, "Security check expired. Please try again."
    if supplied != expected:
        build_numeric_captcha(scope, refresh=True)
        return False, "Security check failed. Please solve the refreshed challenge."

    build_numeric_captcha(scope, refresh=True)
    return True, "verified"


def verify_recaptcha_token(token: str | None, *, action: str = "submit") -> tuple[bool, str]:
    secret_key = current_app.config.get("RECAPTCHA_SECRET_KEY", "")
    if not secret_key:
        if current_app.config.get("ALLOW_INSECURE_DEV_CAPTCHA", False):
            return True, "verified"
        return False, "reCAPTCHA is not configured. Please contact support."

    cleaned_token = sanitize_text(token or "", max_length=3000)
    if not cleaned_token:
        return False, "Security verification is missing. Please refresh and try again."

    payload = urllib.parse.urlencode(
        {
            "secret": secret_key,
            "response": cleaned_token,
            "remoteip": client_ip(),
        }
    ).encode("utf-8")
    request_obj = urllib.request.Request(
        "https://www.google.com/recaptcha/api/siteverify",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(request_obj, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
    except Exception:
        if current_app.config.get("ALLOW_INSECURE_DEV_CAPTCHA", False):
            current_app.logger.warning("reCAPTCHA verification skipped during local development.", exc_info=True)
            return True, "verified"
        current_app.logger.warning("reCAPTCHA verification failed.", exc_info=True)
        return False, "Security verification is temporarily unavailable. Please try again."

    if not result.get("success"):
        return False, "Security verification failed. Please try again."

    expected_action = action.strip()
    result_action = str(result.get("action") or "").strip()
    if expected_action and result_action and result_action != expected_action:
        return False, "Security verification action did not match. Please try again."

    min_score = float(current_app.config.get("RECAPTCHA_MIN_SCORE", 0.4))
    score = result.get("score")
    if score is not None and float(score) < min_score:
        return False, "Security verification score was too low. Please try again."

    return True, "verified"


def login_attempt_count(email: str, user_type: str, *, success: bool, minutes: int = 15) -> int:
    from ..models import AuthSessionLog

    since = utcnow() - timedelta(minutes=minutes)
    return (
        AuthSessionLog.query.filter_by(email=email.lower().strip(), user_type=user_type, success=success)
        .filter(AuthSessionLog.logged_in_at >= since)
        .count()
    )


def is_login_rate_limited(email: str, user_type: str, threshold: int = 5, minutes: int = 15) -> bool:
    return login_attempt_count(email, user_type, success=False, minutes=minutes) >= threshold


def is_suspicious_login(email: str, user_type: str, ip_address: str, browser: str, operating_system: str) -> bool:
    from ..models import AuthSessionLog

    previous = (
        AuthSessionLog.query.filter_by(email=email.lower().strip(), user_type=user_type, success=True)
        .order_by(AuthSessionLog.logged_in_at.desc())
        .first()
    )
    if not previous:
        return False
    if previous.ip_address and previous.ip_address != ip_address:
        return True
    if previous.browser and previous.browser != browser:
        return True
    if previous.operating_system and previous.operating_system != operating_system:
        return True
    return False
