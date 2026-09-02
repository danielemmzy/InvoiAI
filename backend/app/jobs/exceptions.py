from __future__ import annotations


class JobError(Exception):
    """
    Base exception for all background jobs.
    """


# =====================================================
# Queue
# =====================================================


class QueueError(JobError):
    """
    Queue backend failure.
    """


class QueueUnavailableError(QueueError):
    """
    Queue service unavailable.
    """


class JobNotFoundError(QueueError):
    """
    Requested job does not exist.
    """


class DuplicateJobError(QueueError):
    """
    Job already exists.
    """


# =====================================================
# Registration
# =====================================================


class JobRegistrationError(JobError):
    """
    Invalid job registration.
    """


class UnknownJobError(JobRegistrationError):
    """
    Job type not registered.
    """


# =====================================================
# Execution
# =====================================================


class JobExecutionError(JobError):
    """
    Job execution failed.
    """


class JobTimeoutError(JobExecutionError):
    """
    Job exceeded execution timeout.
    """


class JobCancelledError(JobExecutionError):
    """
    Job cancelled before completion.
    """


class JobRetryExceededError(JobExecutionError):
    """
    Maximum retry attempts exceeded.
    """


# =====================================================
# Serialization
# =====================================================


class JobSerializationError(JobError):
    """
    Failed to serialize job payload.
    """


class JobDeserializationError(JobError):
    """
    Failed to deserialize job payload.
    """


# =====================================================
# Worker
# =====================================================


class WorkerError(JobError):
    """
    Worker failure.
    """


class WorkerUnavailableError(WorkerError):
    """
    Worker unavailable.
    """


class WorkerShutdownError(WorkerError):
    """
    Worker shutting down.
    """