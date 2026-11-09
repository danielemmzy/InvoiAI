from uuid import UUID

from app.core.enum.notification import NotificationChannel, NotificationType
from app.models.domain.ap import InvoiceComment
from app.repositories.ap.comment_repository import InvoiceCommentRepository
from app.services.notification.notification_service import NotificationService


class InvoiceCommentService:
    """
    Lets a user tag teammates on a bill. Mirrors the video's
    "tag a team member, they get pushed into the bill" pattern —
    the workflow task (approval step) stays the source of truth;
    this is a side-channel for internal discussion + notification.
    """

    def __init__(
        self,
        repository: InvoiceCommentRepository | None = None,
        notifications: NotificationService | None = None,
    ) -> None:
        self.repository = repository or InvoiceCommentRepository()
        self.notifications = notifications or NotificationService()

    async def list_for_document(self, org_id: UUID, document_id: UUID):
        return await self.repository.list_for_document(org_id, document_id)

    async def add_comment(
        self,
        *,
        org_id: UUID,
        document_id: UUID,
        author_id: UUID,
        body: str,
        mentioned_user_ids: list[UUID] | None = None,
    ) -> InvoiceComment:

        if not body or not body.strip():
            raise ValueError("Comment body cannot be empty.")

        mentioned = mentioned_user_ids or []

        # id/created_at are Postgres-generated; pass a dict so we don't
        # have to construct an under-populated InvoiceComment instance
        # just to insert it.
        payload = {
            "org_id": str(org_id),
            "document_id": str(document_id),
            "author_id": str(author_id),
            "body": body.strip(),
            "mentioned_user_ids": [str(u) for u in mentioned],
        }

        created = await self.repository.create_comment(payload)
        if created is None:
            raise RuntimeError("Failed to save comment.")

        for user_id in mentioned:
            if str(user_id) == str(author_id):
                continue
            await self.notifications.send(
                user_id=user_id,
                organization_id=org_id,
                type=NotificationType.INVOICE_MENTION,
                title="You were tagged on a bill",
                message=body.strip()[:280],
                data={"document_id": str(document_id), "comment_id": str(created.id)},
                channel=NotificationChannel.IN_APP,
            )

        return created
