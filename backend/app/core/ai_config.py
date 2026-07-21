"""
============================================================
app/core/ai_config.py

Central AI configuration.

Single source of truth for:

- OpenAI models
- Embedding models
- AI pipeline
- OCR thresholds
- Verification thresholds
- Retry policy

Never hardcode AI values elsewhere.
============================================================
"""

from dataclasses import dataclass
from typing import Final

from backend.app.core.enum.enums import AIProvider


# ============================================================
# AI Models
# ============================================================

EXTRACTION_MODEL: Final = "gpt-4o-mini"

ANALYSIS_MODEL: Final = "gpt-4o-mini"

COPILOT_MODEL: Final = "gpt-4.1"

EMBEDDING_MODEL: Final = "text-embedding-3-small"


# ============================================================
# Providers
# ============================================================

DEFAULT_PROVIDER: Final = AIProvider.OPENAI


# ============================================================
# Model Parameters
# ============================================================

TEMPERATURE: Final = 0.1

MAX_TOKENS: Final = 4096

TOP_P: Final = 1.0


# ============================================================
# OCR
# ============================================================

MIN_OCR_CONFIDENCE: Final = 0.80

AUTO_RETRY_OCR: Final = True

MAX_OCR_RETRIES: Final = 2


# ============================================================
# Analysis
# ============================================================

MIN_ANALYSIS_CONFIDENCE: Final = 0.75

AUTO_ANALYZE_AFTER_UPLOAD: Final = True

GENERATE_VENDOR_MEMORY: Final = True

GENERATE_EMBEDDINGS: Final = True


# ============================================================
# Embeddings
# ============================================================

EMBEDDING_DIMENSIONS: Final = 1536

SIMILARITY_THRESHOLD: Final = 0.85


# ============================================================
# Finance Copilot
# ============================================================

MAX_CHAT_HISTORY: Final = 20

MAX_CONTEXT_DOCUMENTS: Final = 25

MAX_CONTEXT_VENDORS: Final = 10


# ============================================================
# Background Jobs
# ============================================================

OCR_QUEUE: Final = "ocr"

ANALYSIS_QUEUE: Final = "analysis"

EMBEDDING_QUEUE: Final = "embeddings"

SYNC_QUEUE: Final = "sync"

EMAIL_QUEUE: Final = "email"


# ============================================================
# Retry Policy
# ============================================================

MAX_AI_RETRIES: Final = 3

RETRY_DELAY_SECONDS: Final = 5


# ============================================================
# Version Metadata
# ============================================================

ENGINE_VERSION: Final = "2.0.0"

ANALYSIS_VERSION: Final = "2.0.0"

PROMPT_VERSION: Final = "2.0.0"


# ============================================================
# Verification Pipeline
# ============================================================

@dataclass(frozen=True)
class VerificationModule:
    name: str
    weight: float
    enabled: bool = True


VERIFICATION_PIPELINE: Final = [

    VerificationModule(
        name="ocr_validation",
        weight=0.10,
    ),

    VerificationModule(
        name="math_check",
        weight=0.20,
    ),

    VerificationModule(
        name="vendor_check",
        weight=0.15,
    ),

    VerificationModule(
        name="duplicate_check",
        weight=0.15,
    ),

    VerificationModule(
        name="historical_check",
        weight=0.15,
    ),

    VerificationModule(
        name="po_match",
        weight=0.10,
    ),

    VerificationModule(
        name="fraud_check",
        weight=0.10,
    ),

    VerificationModule(
        name="compliance_check",
        weight=0.05,
    ),
]