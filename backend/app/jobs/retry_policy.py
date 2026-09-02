from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RetryPolicy:
    """
    Retry policy for background jobs.

    Responsibilities
    ----------------
    • Encapsulate retry behavior
    • Compute retry delays
    • Support exponential backoff

    Queue implementations
    use this policy instead
    of hardcoding retry logic.
    """

    max_attempts: int = 3

    initial_delay: int = 30

    backoff_factor: float = 2.0

    max_delay: int = 900

    exponential_backoff: bool = True

    # =====================================================
    # Retry Decision
    # =====================================================

    def should_retry(
        self,
        *,
        attempt: int,
    ) -> bool:
        """
        Returns True if another retry
        should be attempted.
        """

        return attempt < self.max_attempts

    # =====================================================
    # Delay
    # =====================================================

    def delay(
        self,
        *,
        attempt: int,
    ) -> int:
        """
        Calculate retry delay.
        """

        if not self.exponential_backoff:

            return self.initial_delay

        delay = int(
            self.initial_delay
            * (self.backoff_factor ** max(attempt - 1, 0))
        )

        return min(
            delay,
            self.max_delay,
        )

    # =====================================================
    # Reset
    # =====================================================

    def first_delay(
        self,
    ) -> int:
        """
        Initial retry delay.
        """

        return self.initial_delay

    # =====================================================
    # Summary
    # =====================================================

    def as_dict(
        self,
    ) -> dict:

        return {
            "max_attempts": self.max_attempts,
            "initial_delay": self.initial_delay,
            "backoff_factor": self.backoff_factor,
            "max_delay": self.max_delay,
            "exponential_backoff": self.exponential_backoff,
        }


#
# Default retry policy
#

DEFAULT_RETRY_POLICY = RetryPolicy()