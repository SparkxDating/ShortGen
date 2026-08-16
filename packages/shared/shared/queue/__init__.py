"""Queue abstraction. Business logic must depend on ``JobQueue``, not Redis."""

from shared.queue.interface import JobQueue, QueueJob
from shared.queue.factory import create_job_queue

__all__ = ["JobQueue", "QueueJob", "create_job_queue"]
