"""
DPO Pay Integration & Server-to-Server Verification Service for Eden Training Institute and Therapy.
Complies with Blueprint Phase 3 & Phase 5 and Pre-Deployment Security Checklist #22:
- Never trusts a price or status sent by the browser.
- Uses defusedxml to parse DPO API v6 XML responses safely.
- Strictly disables unconfigured `sandbox-test-token` / `your-dpo-*` placeholders in production,
  while allowing explicit `DPO-PILOT-SANDBOX` mode during pilot staging prior to DPO bank KYC completion.
- Locks only the Payment table row during `select_for_update()` for PostgreSQL outer-join safety.
"""
import os
import urllib.error
import urllib.request
import uuid
import xml.etree.ElementTree as StdET
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from defusedxml import ElementTree as SafeET
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Price
from apps.enrollments.models import Enrollment, activate_enrollment

from .models import Payment

DPO_HOSTED_CHECKOUT_BASE = "https://secure.3gdirectpay.com/payv3.php?ID="
EXPLICIT_PILOT_TOKEN = "DPO-PILOT-SANDBOX"


class PaymentIntegrationError(Exception):
    """Raised when DPO Pay communication, configuration, or verification fails."""


@dataclass(frozen=True)
class DpoVerificationResult:
    """Normalized server-to-server verification payload returned by DPO verifyToken."""

    result_code: str
    result_explanation: str
    transaction_amount_minor: int
    transaction_currency: str
    customer_credit_type: str
    raw_xml: str


def _is_placeholder_company_token(company_token: str) -> bool:
    """Return True if the configured DPO_COMPANY_TOKEN is blank or a local placeholder."""
    return (
        not company_token
        or company_token.startswith("your-dpo-")
        or company_token == "sandbox-test-token"
    )


def _is_dev_sandbox_enabled() -> bool:
    """
    Return True in local dev/test environments (`config.settings.dev`) or when the administrator
    explicitly opts into `DPO_COMPANY_TOKEN = 'DPO-PILOT-SANDBOX'` for pre-KYC pilot rehearsals.
    """
    company_token = getattr(settings, "DPO_COMPANY_TOKEN", "").strip()
    if company_token == EXPLICIT_PILOT_TOKEN:
        return True

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


def _decimal_string_to_minor_units(amount_str: str) -> int:
    """Convert a major-unit decimal string (e.g., '35000.00') to integer minor units."""
    try:
        dec = Decimal(amount_str.strip()).quantize(Decimal("0.01"))
    except (InvalidOperation, AttributeError) as exc:
        raise ValidationError(
            f"Invalid monetary amount string from provider: {amount_str!r}"
        ) from exc
    return int(dec * 100)


def build_dpo_create_token_xml(
    *,
    company_token: str,
    service_type: str,
    amount_major: Decimal,
    currency: str,
    company_ref: str,
    redirect_url: str,
    back_url: str,
    service_description: str,
    customer_email: str,
) -> bytes:
    """Construct a DPO API v6 createToken XML payload using parameterized ElementTree nodes."""
    root = StdET.Element("API3G")

    StdET.SubElement(root, "CompanyToken").text = company_token
    StdET.SubElement(root, "Request").text = "createToken"

    tx = StdET.SubElement(root, "Transaction")
    StdET.SubElement(tx, "PaymentAmount").text = f"{amount_major:.2f}"
    StdET.SubElement(tx, "PaymentCurrency").text = currency
    StdET.SubElement(tx, "CompanyRef").text = company_ref
    StdET.SubElement(tx, "RedirectURL").text = redirect_url
    StdET.SubElement(tx, "BackURL").text = back_url
    StdET.SubElement(tx, "CompanyRefUnique").text = "1"
    StdET.SubElement(tx, "PTL").text = "24"
    StdET.SubElement(tx, "customerEmail").text = customer_email

    services = StdET.SubElement(root, "Services")
    service = StdET.SubElement(services, "Service")
    StdET.SubElement(service, "ServiceType").text = service_type
    StdET.SubElement(service, "ServiceDescription").text = service_description
    StdET.SubElement(service, "ServiceDate").text = datetime.now(UTC).strftime(
        "%Y/%m/%d %H:%M"
    )

    return StdET.tostring(root, encoding="utf-8", xml_declaration=True)


def build_dpo_verify_token_xml(*, company_token: str, trans_token: str) -> bytes:
    """Construct a DPO API v6 verifyToken XML payload."""
    root = StdET.Element("API3G")
    StdET.SubElement(root, "CompanyToken").text = company_token
    StdET.SubElement(root, "Request").text = "verifyToken"
    StdET.SubElement(root, "TransactionToken").text = trans_token
    return StdET.tostring(root, encoding="utf-8", xml_declaration=True)


def request_dpo_trans_token(
    *,
    payment: Payment,
    redirect_url: str,
    back_url: str,
) -> tuple[str, str, dict]:
    """
    Request a DPO Hosted Checkout Transaction Token (`TransToken`).
    """
    company_token = getattr(settings, "DPO_COMPANY_TOKEN", "").strip()
    service_type = getattr(settings, "DPO_SERVICE_TYPE", "").strip() or "5525"
    api_url = getattr(
        settings,
        "DPO_API_URL",
        "https://secure.3gdirectpay.com/API/v6/",
    ).strip()
    sandbox_allowed = _is_dev_sandbox_enabled()
    is_placeholder = _is_placeholder_company_token(company_token) or (
        company_token == EXPLICIT_PILOT_TOKEN
    )

    if is_placeholder:
        if not sandbox_allowed:
            raise PaymentIntegrationError(
                "Production DPO_COMPANY_TOKEN is not configured. Sandbox tokens are disabled in production."
            )
        trans_token = f"DPO-SANDBOX-{payment.id.hex[:16].upper()}"
        checkout_url = f"{DPO_HOSTED_CHECKOUT_BASE}{trans_token}"
        log_entry = {
            "mode": "sandbox_local",
            "created_at": datetime.now(UTC).isoformat(),
            "trans_token": trans_token,
            "amount_minor": payment.amount_minor,
            "currency": payment.currency,
        }
        return trans_token, checkout_url, log_entry

    course_title = (
        payment.enrollment.cohort.course.title
        if payment.enrollment
        else "Eden Training Institute and Therapy Tuition"
    )
    customer_email = payment.enrollment.user.email if payment.enrollment else ""

    xml_payload = build_dpo_create_token_xml(
        company_token=company_token,
        service_type=service_type,
        amount_major=payment.amount_major,
        currency=payment.currency,
        company_ref=payment.company_ref,
        redirect_url=redirect_url,
        back_url=back_url,
        service_description=course_title[:100],
        customer_email=customer_email,
    )

    req = urllib.request.Request(
        api_url,
        data=xml_payload,
        headers={"Content-Type": "application/xml; charset=utf-8"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_xml = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise PaymentIntegrationError(f"Failed to reach DPO Pay API: {exc}") from exc

    parsed = SafeET.fromstring(raw_xml)
    result_code = (parsed.findtext("Result") or "").strip()
    explanation = (parsed.findtext("ResultExplanation") or "").strip()
    trans_token = (parsed.findtext("TransToken") or "").strip()

    if result_code != "000" or not trans_token:
        raise PaymentIntegrationError(
            f"DPO createToken rejected request (Result={result_code}): {explanation}"
        )

    checkout_url = f"{DPO_HOSTED_CHECKOUT_BASE}{trans_token}"
    log_entry = {
        "mode": "live_dpo",
        "result_code": result_code,
        "result_explanation": explanation,
        "raw_create_response": raw_xml,
    }
    return trans_token, checkout_url, log_entry


def fetch_dpo_verification_from_provider(payment: Payment) -> DpoVerificationResult:
    """
    Perform a server-to-server call to DPO's `verifyToken` endpoint.
    """
    company_token = getattr(settings, "DPO_COMPANY_TOKEN", "").strip()
    api_url = getattr(
        settings,
        "DPO_API_URL",
        "https://secure.3gdirectpay.com/API/v6/",
    ).strip()
    sandbox_allowed = _is_dev_sandbox_enabled()
    is_placeholder = _is_placeholder_company_token(company_token) or (
        company_token == EXPLICIT_PILOT_TOKEN
    )

    if not sandbox_allowed and payment.provider_ref.startswith("DPO-SANDBOX-"):
        raise PaymentIntegrationError(
            "Sandbox payment tokens cannot be verified in production."
        )

    if is_placeholder:
        if not sandbox_allowed:
            raise PaymentIntegrationError(
                "Production DPO_COMPANY_TOKEN is not configured. Cannot verify payment in production."
            )
        return DpoVerificationResult(
            result_code="000",
            result_explanation="Transaction Paid (Sandbox Server-to-Server Verification)",
            transaction_amount_minor=payment.amount_minor,
            transaction_currency=payment.currency,
            customer_credit_type="M-PESA / CARD",
            raw_xml=(
                f"<API3G><Result>000</Result>"
                f"<ResultExplanation>Transaction Paid</ResultExplanation>"
                f"<TransactionAmount>{payment.amount_major:.2f}</TransactionAmount>"
                f"<TransactionCurrency>{payment.currency}</TransactionCurrency></API3G>"
            ),
        )

    xml_payload = build_dpo_verify_token_xml(
        company_token=company_token,
        trans_token=payment.provider_ref,
    )
    req = urllib.request.Request(
        api_url,
        data=xml_payload,
        headers={"Content-Type": "application/xml; charset=utf-8"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw_xml = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise PaymentIntegrationError(
            f"Failed to verify token with DPO Pay: {exc}"
        ) from exc

    parsed = SafeET.fromstring(raw_xml)
    result_code = (parsed.findtext("Result") or "").strip()
    explanation = (parsed.findtext("ResultExplanation") or "").strip()
    tx_amount_str = (parsed.findtext("TransactionAmount") or "0.00").strip()
    tx_currency = (parsed.findtext("TransactionCurrency") or "").strip().upper()
    credit_type = (parsed.findtext("CustomerCreditType") or "").strip()

    return DpoVerificationResult(
        result_code=result_code,
        result_explanation=explanation,
        transaction_amount_minor=_decimal_string_to_minor_units(tx_amount_str),
        transaction_currency=tx_currency,
        customer_credit_type=credit_type,
        raw_xml=raw_xml,
    )


@transaction.atomic
def initiate_enrollment_payment(
    *,
    enrollment: Enrollment,
    redirect_url: str,
    back_url: str,
) -> Payment:
    """
    Create or reuse an INITIATED Payment for an Enrollment using the server-computed audience Price.
    """
    locked_enrollment = Enrollment.objects.select_for_update().get(pk=enrollment.pk)
    if locked_enrollment.status == Enrollment.Status.ACTIVE:
        raise ValidationError("This enrollment is already paid and active.")

    server_price = locked_enrollment.get_server_price()
    if server_price is None:
        raise ValidationError(
            "No server price is configured for this course and student audience."
        )

    existing_initiated = (
        Payment.objects.select_for_update()
        .filter(
            enrollment=locked_enrollment,
            provider=Payment.Provider.DPO,
            status=Payment.Status.INITIATED,
            amount_minor=server_price.amount_minor,
            currency=server_price.currency,
        )
        .first()
    )
    if existing_initiated and existing_initiated.checkout_url:
        return existing_initiated

    company_ref = f"EDEN-{uuid.uuid4().hex[:12].upper()}"
    placeholder_ref = f"PENDING-{company_ref}"

    payment = Payment.objects.create(
        enrollment=locked_enrollment,
        provider=Payment.Provider.DPO,
        provider_ref=placeholder_ref,
        company_ref=company_ref,
        amount_minor=server_price.amount_minor,
        currency=server_price.currency,
        status=Payment.Status.INITIATED,
    )

    trans_token, checkout_url, create_log = request_dpo_trans_token(
        payment=payment,
        redirect_url=redirect_url,
        back_url=back_url,
    )

    payment.provider_ref = trans_token
    payment.checkout_url = checkout_url
    payment.raw_log = {"initiation": create_log, "verifications": []}
    payment.save(
        update_fields=["provider_ref", "checkout_url", "raw_log", "updated_at"]
    )
    return payment


def verify_and_activate_dpo_payment(
    *,
    provider_ref: str,
    verification_override: DpoVerificationResult | None = None,
    trigger_source: str = "dpo_verify",
) -> Payment:
    """
    Idempotent server-to-server verification handler for both browser return and DPO webhook.
    """
    error_to_raise: ValidationError | None = None

    with transaction.atomic():
        try:
            payment = Payment.objects.select_for_update().get(
                provider=Payment.Provider.DPO,
                provider_ref=provider_ref,
            )
        except Payment.DoesNotExist as exc:
            raise ValidationError(
                f"Unknown DPO payment reference: {provider_ref}"
            ) from exc

        raw_log = dict(payment.raw_log or {})
        verifications = list(raw_log.get("verifications", []))

        if payment.status == Payment.Status.VERIFIED:
            verifications.append(
                {
                    "timestamp": datetime.now(UTC).isoformat(),
                    "trigger_source": trigger_source,
                    "note": "Idempotent duplicate notification ignored; payment already verified.",
                }
            )
            raw_log["verifications"] = verifications
            payment.raw_log = raw_log
            payment.save(update_fields=["raw_log", "updated_at"])
            return payment

        result = verification_override or fetch_dpo_verification_from_provider(payment)

        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "trigger_source": trigger_source,
            "result_code": result.result_code,
            "result_explanation": result.result_explanation,
            "reported_amount_minor": result.transaction_amount_minor,
            "reported_currency": result.transaction_currency,
            "customer_credit_type": result.customer_credit_type,
            "raw_xml": result.raw_xml,
        }
        verifications.append(log_entry)
        raw_log["verifications"] = verifications

        if result.result_code != "000":
            payment.status = Payment.Status.FAILED
            payment.raw_log = raw_log
            payment.save(update_fields=["status", "raw_log", "updated_at"])
            error_to_raise = ValidationError(
                f"DPO payment not completed (Result={result.result_code}): {result.result_explanation}"
            )
        elif (
            result.transaction_currency.upper() != payment.currency.upper()
            or result.transaction_amount_minor != payment.amount_minor
        ):
            payment.status = Payment.Status.TAMPERED
            payment.raw_log = raw_log
            payment.save(update_fields=["status", "raw_log", "updated_at"])
            error_to_raise = ValidationError(
                "Payment integrity violation: provider amount or currency does not match server price."
            )
        else:
            payment.status = Payment.Status.VERIFIED
            payment.verified_at = timezone.now()
            payment.raw_log = raw_log
            payment.save(
                update_fields=["status", "verified_at", "raw_log", "updated_at"]
            )

            residency_reg = getattr(payment, "residency_registration", None)
            if residency_reg is not None:
                residency_reg.status = "confirmed"
                residency_reg.save(update_fields=["status", "updated_at"])
            elif payment.enrollment_id is not None:
                activate_enrollment(
                    payment.enrollment,
                    source=f"dpo_verified:{payment.provider_ref}",
                )

    if error_to_raise is not None:
        raise error_to_raise

    return payment


@transaction.atomic
def record_manual_staff_payment(
    *,
    enrollment: Enrollment,
    staff_email: str,
    reference_note: str = "",
) -> Payment:
    """
    Creates an audited MANUAL Payment record for bank/M-Pesa edge cases and activates the enrollment.
    """
    locked_enrollment = Enrollment.objects.select_for_update().get(pk=enrollment.pk)
    server_price = locked_enrollment.get_server_price()
    amount_minor = server_price.amount_minor if server_price else 3_500_000
    currency = server_price.currency if server_price else Price.Currency.KES

    ref_code = f"MANUAL-{uuid.uuid4().hex[:12].upper()}"
    payment = Payment.objects.create(
        enrollment=locked_enrollment,
        provider=Payment.Provider.MANUAL,
        provider_ref=ref_code,
        company_ref=ref_code,
        amount_minor=amount_minor,
        currency=currency,
        status=Payment.Status.VERIFIED,
        verified_at=timezone.now(),
        raw_log={
            "manual_override": {
                "staff_email": staff_email,
                "timestamp": datetime.now(UTC).isoformat(),
                "reference_note": reference_note
                or "Marked paid manually via Django Admin",
            }
        },
    )

    activate_enrollment(
        locked_enrollment,
        source=f"staff_manual:{staff_email}",
    )
    return payment