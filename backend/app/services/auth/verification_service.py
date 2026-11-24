"""Six-digit email verification.

Design rules
------------
- Email is the primary and sufficient verification path. SMS is optional and
  never blocks signup, including for users in Nigeria.
- Codes are six digits, hashed with an HMAC pepper, single-use, expiring, and
  attempt-limited. The plaintext code is only handed to the email sender.
- Resend and verification responses are non-enumerating: an unknown email gets
  the same shape as a known one.
- Verification is enforced server-side. Completing it also confirms the
  Supabase email so existing token validation remains the source of truth.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Literal, Protocol
from uuid import UUID, uuid4

from app.core.config import settings
from app.core.logging import logger
from app.repositories.auth.verification_repository import (
    EmailVerificationRepository,
    _as_utc,
)

PURPOSE = "email_verification"
GENERIC_RESEND_MESSAGE = (
    "If an account is waiting for verification, a new six-digit code has "
    "been sent."
)

VerifyStatus = Literal[
    "verified",
    "invalid",
    "expired",
    "locked",
    "already_verified",
    "delivery_failed",
]


@dataclass(frozen=True)
class VerifyResult:
    status: VerifyStatus
    attempts_remaining: int | None = None
    message: str = ""


class VerificationEmailSender(Protocol):
    async def send_code(
        self,
        *,
        user_id: UUID,
        email: str,
        code: str,
        first_name: str | None = None,
    ) -> bool: ...


class SmtpVerificationEmailSender:
    """Deliver the code through the existing SMTP notification provider."""

    async def send_code(
        self,
        *,
        user_id: UUID,
        email: str,
        code: str,
        first_name: str | None = None,
    ) -> bool:
        from app.services.notification.email_service import EmailNotificationProvider

        greeting = f"Hi {first_name},\n\n" if first_name else ""
        message = (
            f"{greeting}Your InvoiAI verification code is {code}.\n\n"
            f"It expires in {settings.otp_expire_minutes} minutes. "
            "If you did not create an InvoiAI account, you can ignore this email."
        )

        try:
            return await EmailNotificationProvider().send(
                user_id=user_id,
                title="Your InvoiAI verification code",
                message=message,
                recipient=email,
            )
        except Exception:
            # Never include the code in the log line.
            logger.exception("verification_email_delivery_failed")
            return False


def generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_code(*, email: str, code: str) -> str:
    pepper = settings.otp_hash_secret or settings.secret_key
    message = f"{email.strip().lower()}:{code}".encode("utf-8")
    return hmac.new(pepper.encode("utf-8"), message, hashlib.sha256).hexdigest()


def code_matches(*, email: str, code: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_code(email=email, code=code), code_hash)


def _utc_now() -> datetime:
    return datetime.now(UTC)


class EmailVerificationService:
    def __init__(
        self,
        *,
        repository: EmailVerificationRepository | None = None,
        sender: VerificationEmailSender | None = None,
        auth_repository: Any | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository or EmailVerificationRepository()
        self.sender = sender or SmtpVerificationEmailSender()
        self.auth_repository = auth_repository
        self._now = now or _utc_now

    # ------------------------------------------------------------------
    # Issue
    # ------------------------------------------------------------------

    async def issue(
        self,
        *,
        user_id: UUID | str,
        email: str,
        first_name: str | None = None,
    ) -> dict[str, Any]:
        email = email.strip().lower()
        await self.repository.invalidate_pending(user_id=user_id, email=email)

        code = generate_code()
        now = self._now()
        expires_at = now + timedelta(minutes=settings.otp_expire_minutes)

        row = await self.repository.create(
            {
                # Supply the id and timestamps here rather than relying on
                # database defaults so the same code path is testable.
                "id": str(uuid4()),
                "user_id": str(user_id),
                "email": email,
                "purpose": PURPOSE,
                "code_hash": hash_code(email=email, code=code),
                "status": "pending",
                "attempts": 0,
                "max_attempts": settings.otp_max_attempts,
                "resend_count": 0,
                "last_sent_at": now.isoformat(),
                "expires_at": expires_at.isoformat(),
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }
        )

        sent = await self.sender.send_code(
            user_id=UUID(str(user_id)),
            email=email,
            code=code,
            first_name=first_name,
        )

        return {
            "challenge_id": row.get("id"),
            "email": email,
            "code_sent": sent,
            "expires_in_seconds": settings.otp_expire_minutes * 60,
            "resend_cooldown_seconds": settings.otp_resend_cooldown_seconds,
            "max_attempts": settings.otp_max_attempts,
        }

    # ------------------------------------------------------------------
    # Verify
    # ------------------------------------------------------------------

    async def verify(self, *, email: str, code: str) -> VerifyResult:
        email = email.strip().lower()
        code = code.strip()

        if len(code) != 6 or not code.isdigit():
            return VerifyResult("invalid", message="Enter the six-digit code.")

        challenge = await self.repository.latest_for_email(email, purpose=PURPOSE)
        if not challenge:
            return VerifyResult(
                "invalid",
                message="That code is invalid or has expired.",
            )

        status = challenge.get("status")

        if status == "verified":
            return VerifyResult(
                "already_verified",
                message="This email is already verified. Please sign in.",
            )
        if status == "locked":
            return VerifyResult(
                "locked",
                message="Too many incorrect attempts. Request a new code.",
            )
        if status == "expired":
            return VerifyResult(
                "expired",
                message="That code has expired. Request a new code.",
            )

        expires_at = _as_utc(challenge.get("expires_at"))
        if expires_at is None or expires_at <= self._now():
            await self.repository.expire(challenge["id"])
            return VerifyResult(
                "expired",
                message="That code has expired. Request a new code.",
            )

        attempts = int(challenge.get("attempts") or 0)
        max_attempts = int(
            challenge.get("max_attempts") or settings.otp_max_attempts
        )

        if not code_matches(
            email=email,
            code=code,
            code_hash=str(challenge.get("code_hash") or ""),
        ):
            attempts += 1
            locked = attempts >= max_attempts
            await self.repository.increment_attempts(
                challenge["id"],
                attempts,
                locked=locked,
            )
            if locked:
                return VerifyResult(
                    "locked",
                    attempts_remaining=0,
                    message="Too many incorrect attempts. Request a new code.",
                )
            return VerifyResult(
                "invalid",
                attempts_remaining=max(0, max_attempts - attempts),
                message=(
                    "That code is incorrect. "
                    f"{max(0, max_attempts - attempts)} attempts remaining."
                ),
            )

        # Confirm the identity provider before burning the code. If Supabase
        # is temporarily unavailable the user can retry the same code.
        user_id = challenge.get("user_id")
        if user_id and self.auth_repository is not None:
            try:
                await self.auth_repository.admin_confirm_email(user_id)
            except Exception:
                logger.exception("verification_provider_confirm_failed")
                return VerifyResult(
                    "delivery_failed",
                    message=(
                        "Verification is temporarily unavailable. "
                        "Please try the same code again."
                    ),
                )

        await self.repository.mark_verified(challenge["id"])
        return VerifyResult("verified", message="Your email is verified.")

    # ------------------------------------------------------------------
    # Resend
    # ------------------------------------------------------------------

    async def resend(self, *, email: str) -> dict[str, Any]:
        email = email.strip().lower()
        latest = await self.repository.latest_for_email(email, purpose=PURPOSE)

        if not latest:
            return {
                "message": GENERIC_RESEND_MESSAGE,
                "retry_after_seconds": None,
                "code_sent": False,
            }

        # Never reopen a verified account by issuing another challenge.
        if latest.get("status") == "verified":
            return {
                "message": GENERIC_RESEND_MESSAGE,
                "retry_after_seconds": None,
                "code_sent": False,
            }

        last_sent = _as_utc(latest.get("last_sent_at")) or _as_utc(
            latest.get("created_at")
        )
        now = self._now()

        cooldown = settings.otp_resend_cooldown_seconds
        if last_sent is not None:
            elapsed = (now - last_sent).total_seconds()
            if elapsed < cooldown:
                return {
                    "message": GENERIC_RESEND_MESSAGE,
                    "retry_after_seconds": int(cooldown - elapsed),
                    "code_sent": False,
                }

        # Ratio: at most OTP_MAX_RESENDS_PER_HOUR new challenges per email.
        rows = await self.repository.recent_for_email(email, purpose=PURPOSE)
        hour_ago = now - timedelta(hours=1)
        recent = [
            row
            for row in rows
            if (_as_utc(row.get("created_at")) or datetime.min.replace(tzinfo=UTC))
            > hour_ago
        ]
        if len(recent) >= settings.otp_max_resends_per_hour:
            return {
                "message": GENERIC_RESEND_MESSAGE,
                "retry_after_seconds": cooldown,
                "code_sent": False,
            }

        result = await self.issue(
            user_id=latest["user_id"],
            email=email,
        )
        try:
            await self.repository.update(
                result["challenge_id"],
                {
                    "resend_count": int(latest.get("resend_count") or 0) + 1,
                    "last_sent_at": now.isoformat(),
                },
            )
        except Exception:
            logger.exception("verification_resend_count_failed")

        return {
            "message": GENERIC_RESEND_MESSAGE,
            "retry_after_seconds": cooldown,
            "code_sent": bool(result.get("code_sent")),
        }

    # ------------------------------------------------------------------
    # Gate
    # ------------------------------------------------------------------

    async def is_verified(self, user_id: UUID | str) -> bool | None:
        latest = await self.repository.latest_for_user(user_id)
        if latest is None:
            return None
        return latest.get("status") == "verified"


def resolve_email_verified(
    user_id: UUID | str,
    *,
    supabase_verified: bool,
) -> bool:
    """Combine Supabase confirmation and the OTP challenge state.

    - Supabase unconfirmed -> unverified.
    - No OTP row -> legacy account; trust Supabase confirmation.
    - OTP row present -> verified only when its status is ``verified``.

    A lookup failure falls back to the Supabase value so an infrastructure
    hiccup does not lock every existing account out of the product.
    """
    if not supabase_verified:
        return False

    try:
        status = EmailVerificationRepository().latest_status_for_user_sync(user_id)
    except Exception as exc:
        # The fallback exists so an infrastructure hiccup does not lock every
        # existing account out. Logging must therefore never be able to turn
        # that fallback into a request failure.
        try:
            logger.warning(
                "verification_state_lookup_failed",
                error_type=type(exc).__name__,
                error=str(exc)[:200],
            )
        except Exception:  # pragma: no cover - logging must not fail a request
            pass
        return True

    if status is None:
        return True
    return status == "verified"
