"""Durable provider checkpoints, without tokens or raw provider error bodies."""
from contextvars import ContextVar

recorder = ContextVar('publication_recorder', default=None)


def checkpoint(phase, **ids):
    callback = recorder.get()
    if callback:
        callback({'phase': phase, **{key: str(value) for key, value in ids.items() if key in {'container_id', 'post_id'}}})
