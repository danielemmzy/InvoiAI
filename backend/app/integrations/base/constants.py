from __future__ import annotations

from enum import Enum


class IntegrationEnvironment(str, Enum):

    SANDBOX = "sandbox"

    PRODUCTION = "production"


class SyncDirection(str, Enum):

    IMPORT = "import"

    EXPORT = "export"

    BIDIRECTIONAL = "bidirectional"


class SyncResult(str, Enum):

    SUCCESS = "success"

    FAILED = "failed"

    PARTIAL = "partial"


DEFAULT_TIMEOUT = 30

DEFAULT_PAGE_SIZE = 100

MAX_RETRIES = 3

BACKOFF_SECONDS = 2