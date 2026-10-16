"""
Server-side Cloudflare Turnstile verification for Dr. Violet's LMS (EdenLMS).
Complies with Pre-Deployment Security Checklist #12:
A missing or fake token is rejected directly by the API before authentication or registration proceeds.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
CLOUDFLARE_TEST_SECRET = "1x0000000000000000000000000000000AA"
DEV_PASS_TOKENS = frozenset({"turnstile-dev-pass-token", "XXXX.DUMMY.TOKEN.XXXX"})


def verify_turnstile_token(token: str | None, remote_ip: str | None = None) -> bool:
    """
    Validate a Cloudflare Turnstile token server-side.
    - Rejects empty, whitespace, or malformed tokens immediately.
    - In local dev/test (when using Cloudflare's dummy secret key), accepts explicit
      DEV_PASS_TOKENS so offline pytest suites and local dev forms can verify deterministically,
      while still rejecting fake/missing tokens.
    - In staging/production, performs an HTTPS POST to Cloudflare's siteverify endpoint.
    """
    if not token or not isinstance(token, str) or not token.strip():
        return False

    cleaned_token = token.strip()
    secret_key = getattr(settings, "TURNSTILE_SECRET_KEY", "").strip()

    if not secret_key:
        return False

    # Deterministic local/CI verification when using Cloudflare's official test secret key
    if secret_key == CLOUDFLARE_TEST_SECRET:
        return cleaned_token in DEV_PASS_TOKENS

    payload: dict[str, str] = {
        "secret": secret_key,
        "response": cleaned_token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip

    encoded_data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        TURNSTILE_VERIFY_URL,
        data=encoded_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
            return bool(body.get("success") is True)
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False