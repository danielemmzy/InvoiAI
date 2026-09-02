from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.core.enum.notification import NotificationChannel
from app.services.notification.provider.base import NotificationProvider
from app.services.notification.template_renderer import TemplateRenderer


logger = logging.getLogger(__name__)


class EmailNotificationProvider(NotificationProvider):
    """
    Email notification provider.

    Responsibilities
    ----------------
    - Render notification templates.
    - Resolve SMTP configuration.
    - Send email through SMTP.
    - Return delivery success/failure.

    This class contains email transport logic only.
    """

    channel = NotificationChannel.EMAIL
    name = "smtp"

    def __init__(
        self,
        *,
        renderer: TemplateRenderer | None = None,
    ) -> None:

        self.renderer = renderer or TemplateRenderer()

    # =========================================================
    # Availability
    # =========================================================

    async def is_available(self) -> bool:

        return bool(
            settings.smtp_host
            and settings.smtp_sender_email
        )

    # =========================================================
    # Send
    # =========================================================

    async def send(
        self,
        *,
        user_id: UUID,
        title: str,
        message: str,
        data: dict[str, Any] | None = None,
        organization_id: UUID | None = None,
        recipient: str | None = None,
        template: str | None = None,
    ) -> bool:

        if not recipient:

            logger.warning(
                "Email delivery skipped: recipient missing "
                "for user %s",
                user_id,
            )

            return False

        if not await self.is_available():

            logger.warning(
                "Email provider unavailable.",
            )

            return False

        context = data or {}

        if template:

            html = self.renderer.render_html(
                template=template,
                context=context,
            )

            text = self.renderer.render_text(
                template=template,
                context=context,
            )

        else:

            html = message
            text = message

        return await asyncio.to_thread(
            self._send_smtp,
            recipient,
            title,
            html,
            text,
        )

    # =========================================================
    # SMTP Transport
    # =========================================================

    def _send_smtp(
        self,
        recipient: str,
        subject: str,
        html: str,
        text: str,
    ) -> bool:

        message = MIMEMultipart(
            "alternative",
        )

        message["Subject"] = subject

        message["From"] = (
            f"{settings.smtp_sender_name} "
            f"<{settings.smtp_sender_email}>"
        )

        message["To"] = recipient

        message.attach(
            MIMEText(
                text,
                "plain",
            )
        )

        message.attach(
            MIMEText(
                html,
                "html",
            )
        )

        with smtplib.SMTP(
            settings.smtp_host,
            settings.smtp_port,
            timeout=30,
        ) as server:

            server.starttls()

            if settings.smtp_username:

                server.login(
                    settings.smtp_username,
                    settings.smtp_password,
                )

            server.sendmail(
                settings.smtp_sender_email,
                [recipient],
                message.as_string(),
            )

        logger.info(
            "Email accepted by SMTP server for user %s",
            recipient,
        )

        return True