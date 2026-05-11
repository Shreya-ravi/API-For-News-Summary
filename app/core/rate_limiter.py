from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, deque[datetime]] = defaultdict(deque)

    def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        now = datetime.now(timezone.utc)
        threshold = now - timedelta(seconds=window_seconds)
        bucket = self._buckets[key]
        while bucket and bucket[0] < threshold:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(status_code=429, detail='Rate limit exceeded. Please try again later.')
        bucket.append(now)


rate_limiter = InMemoryRateLimiter()
