"""
Role-Based Access Control (RBAC)

Permissions define WHAT a role can do.

Roles are mapped to permissions here so business logic only checks
permissions—not role names.
"""

# ============================================================
# Permission Constants
# ============================================================

VIEW_DOCUMENTS = "documents:view"
UPLOAD_DOCUMENTS = "documents:upload"
EDIT_DOCUMENTS = "documents:edit"
DELETE_DOCUMENTS = "documents:delete"

VIEW_VENDORS = "vendors:view"
MANAGE_VENDORS = "vendors:manage"

VIEW_ANALYTICS = "analytics:view"

VIEW_AI = "ai:view"
RUN_AI = "ai:run"

VIEW_APPROVALS = "approvals:view"
APPROVE_DOCUMENTS = "approvals:approve"

VIEW_MEMBERS = "members:view"
INVITE_MEMBERS = "members:invite"
REMOVE_MEMBERS = "members:remove"

VIEW_SETTINGS = "settings:view"
UPDATE_SETTINGS = "settings:update"

VIEW_INTEGRATIONS = "integrations:view"
MANAGE_INTEGRATIONS = "integrations:manage"

VIEW_AUDIT_LOGS = "audit:view"

VIEW_BILLING = "billing:view"
MANAGE_BILLING = "billing:manage"


# ============================================================
# Role Permission Mapping
# ============================================================

ROLE_PERMISSIONS = {

    "owner": {

        VIEW_DOCUMENTS,
        UPLOAD_DOCUMENTS,
        EDIT_DOCUMENTS,
        DELETE_DOCUMENTS,

        VIEW_VENDORS,
        MANAGE_VENDORS,

        VIEW_ANALYTICS,

        VIEW_AI,
        RUN_AI,

        VIEW_APPROVALS,
        APPROVE_DOCUMENTS,

        VIEW_MEMBERS,
        INVITE_MEMBERS,
        REMOVE_MEMBERS,

        VIEW_SETTINGS,
        UPDATE_SETTINGS,

        VIEW_INTEGRATIONS,
        MANAGE_INTEGRATIONS,

        VIEW_AUDIT_LOGS,

        VIEW_BILLING,
        MANAGE_BILLING,
    },

    "admin": {

        VIEW_DOCUMENTS,
        UPLOAD_DOCUMENTS,
        EDIT_DOCUMENTS,
        DELETE_DOCUMENTS,

        VIEW_VENDORS,
        MANAGE_VENDORS,

        VIEW_ANALYTICS,

        VIEW_AI,
        RUN_AI,

        VIEW_APPROVALS,
        APPROVE_DOCUMENTS,

        VIEW_MEMBERS,
        INVITE_MEMBERS,

        VIEW_SETTINGS,
        UPDATE_SETTINGS,

        VIEW_INTEGRATIONS,
        MANAGE_INTEGRATIONS,

        VIEW_AUDIT_LOGS,

        VIEW_BILLING,
    },

    "member": {

        VIEW_DOCUMENTS,
        UPLOAD_DOCUMENTS,
        EDIT_DOCUMENTS,

        VIEW_VENDORS,

        VIEW_ANALYTICS,

        VIEW_AI,
        RUN_AI,

        VIEW_APPROVALS,
    },

    "approver": {

        VIEW_DOCUMENTS,

        VIEW_AI,

        VIEW_APPROVALS,
        APPROVE_DOCUMENTS,
    },

    "viewer": {

        VIEW_DOCUMENTS,

        VIEW_ANALYTICS,

        VIEW_AI,
    },
}


# ============================================================
# Helper Functions
# ============================================================

def has_permission(role: str, permission: str) -> bool:
    """
    Returns True if the role has the permission.
    """
    return permission in ROLE_PERMISSIONS.get(role, set())


def get_permissions(role: str) -> set[str]:
    """
    Returns all permissions for a role.
    """
    return ROLE_PERMISSIONS.get(role, set())