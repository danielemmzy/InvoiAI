"""
============================================================
app/core/versions.py

Centralized version management for InvoiAI.

Every major subsystem has its own version so we can track
breaking changes, AI engine upgrades, prompt revisions,
database migrations, and API compatibility.

Do NOT hardcode version strings anywhere else.
Always import from this module.

Example:
    from app.core.versions import APP_VERSION
============================================================
"""

from typing import Final

# ============================================================
# Application
# ============================================================

APP_VERSION: Final = "2.0.0"

API_VERSION: Final = "v1"

DATABASE_SCHEMA_VERSION: Final = "v4"

# ============================================================
# AI
# ============================================================

AI_ENGINE_VERSION: Final = "2.0.0"

OCR_ENGINE_VERSION: Final = "2.0.0"

ANALYSIS_ENGINE_VERSION: Final = "2.0.0"

EMBEDDING_ENGINE_VERSION: Final = "2.0.0"

PROMPT_VERSION: Final = "2.0.0"

# ============================================================
# Verification Engine
# ============================================================

VERIFICATION_ENGINE_VERSION: Final = "2.0.0"

RULE_ENGINE_VERSION: Final = "2.0.0"

RISK_ENGINE_VERSION: Final = "2.0.0"

# ============================================================
# Organization / OCM
# ============================================================

OCM_VERSION: Final = "2.0.0"

RBAC_VERSION: Final = "2.0.0"

# ============================================================
# Integrations
# ============================================================

INTEGRATION_VERSION: Final = "2.0.0"

QUICKBOOKS_CONNECTOR_VERSION: Final = "2.0.0"

XERO_CONNECTOR_VERSION: Final = "2.0.0"

# ============================================================
# Background Workers
# ============================================================

WORKER_VERSION: Final = "2.0.0"

QUEUE_VERSION: Final = "2.0.0"

# ============================================================
# Finance Copilot
# ============================================================

FINANCE_COPILOT_VERSION: Final = "2.0.0"

MEMORY_ENGINE_VERSION: Final = "2.0.0"

VECTOR_ENGINE_VERSION: Final = "2.0.0"