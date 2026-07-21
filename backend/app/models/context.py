from dataclasses import dataclass
from typing import Optional


# ============================================================
# Authentication
# ============================================================

@dataclass(frozen=True)
class AuthUser:
    """
    Identity returned after JWT validation.

    Authentication only.

    No organization information belongs here.
    """

    id: str

    email: str

    email_confirmed: bool = False

    phone: Optional[str] = None

    is_anonymous: bool = False


# ============================================================
# Organization
# ============================================================

@dataclass(frozen=True)
class OrgInfo:

    id: str

    name: str

    slug: str

    plan: str

    currency: str

    country: Optional[str]

    features: dict

    document_limit: int


# ============================================================
# Membership
# ============================================================

@dataclass(frozen=True)
class MemberInfo:

    user_id: str

    role: str

    department: Optional[str]

    spending_limit: Optional[float]

    is_active: bool


# ============================================================
# Usage
# ============================================================

@dataclass(frozen=True)
class UsageInfo:

    month: str

    document_count: int

    document_limit: int

    api_calls: int

    storage_bytes: int

    ai_tokens_used: int

    @property
    def documents_remaining(self) -> int:
        return max(
            0,
            self.document_limit - self.document_count,
        )

    @property
    def limit_reached(self) -> bool:
        return self.document_count >= self.document_limit


# ============================================================
# Organization Context
# ============================================================

@dataclass(frozen=True)
class OrganizationContext:

    org: OrgInfo

    member: MemberInfo

    settings: dict

    usage: UsageInfo

    @property
    def org_id(self) -> str:
        return self.org.id

    @property
    def user_id(self) -> str:
        return self.member.user_id

    @property
    def role(self) -> str:
        return self.member.role

    @property
    def plan(self) -> str:
        return self.org.plan