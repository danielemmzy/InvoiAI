def seats_available(*, active_count: int, pending_count: int, limit: int | None) -> bool:
    return limit is None or active_count + pending_count < limit
