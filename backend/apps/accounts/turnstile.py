"""
Server-side Cloudflare Turnstile verification for Eden Training Institute and Therapy (EdenLMS).
Complies with Pre-Deployment Security Checklist #12:
- Rejects missing, malformed, or fake tokens directly on the server.
- Strictly disables dev/test pass tokens in production (`config.settings.prod` or `ALLOW_DEV_SANDBOX=False`).
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
CLOUDFLARE_TEST_SECRET = "1x0000000000000000000000000000000AA"
DEV_PASS_TOKENS = frozenset({"turnstile-dev-pass-token", "XXXX.DUMMY.TOKEN.XXXX"})


def _is_dev_sandbox_enabled() -> bool:
    """
    Return True only in local dev/test environments (`config.settings.dev`) unless
    explicitly disabled via `settings.ALLOW_DEV_SANDBOX = False`.
    Always returns False under `config.settings.prod`.
    """
    explicit_flag = getattr(settings, "ALLOW_DEV_SANDBOX", None)
    if explicit_flag is False:
        return False
    if explicit_flag is True:
        return True

    settings_module = getattr(settings, "SETTINGS_MODULE", "") or os.environ.get(
        "DJANGO_SETTINGS_MODULE", ""
    )
    if settings_module.endswith(".prod"):
        return False
    return bool(getattr(settings, "DEBUG", False) or settings_module.endswith(".dev"))


def verify_turnstile_token(token: str | None, remote_ip: str | None = None) -> bool:
    """
    Validate a Cloudflare Turnstile token server-side.
    - Rejects empty, whitespace, or malformed tokens immediately.
    - In local dev/test (`_is_dev_sandbox_enabled() == True`) with Cloudflare's test secret key,
      accepts DEV_PASS_TOKENS for deterministic offline testing.
    - In production (`config.settings.prod` or `ALLOW_DEV_SANDBOX=False`), strictly rejects
      DEV_PASS_TOKENS and CLOUDFLARE_TEST_SECRET, enforcing live HTTPS verification.
    """
    if not token or not isinstance(token, str) or not token.strip():
        return False

    cleaned_token = token.strip()
    secret_key = getattr(settings, "TURNSTILE_SECRET_KEY", "").strip()
    sandbox_allowed = _is_dev_sandbox_enabled()

    if not secret_key:
        return False

    if sandbox_allowed and secret_key == CLOUDFLARE_TEST_SECRET:
        return cleaned_token in DEV_PASS_TOKENS

    if not sandbox_allowed and (
        secret_key == CLOUDFLARE_TEST_SECRET or cleaned_token in DEV_PASS_TOKENS
    ):
        return False

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