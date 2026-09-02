"""Compatibility import for the V2 SMTP notification provider.

The transport implementation lives in ``email_service.py``; keeping this
module as a re-export preserves the established provider import path without
maintaining two competing email provider implementations.
"""
from app.services.notification.email_service import EmailNotificationProvider

__all__ = ["EmailNotificationProvider"]
