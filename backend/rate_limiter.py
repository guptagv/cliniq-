"""
Simple in-memory rate limiter.
Limits each user to 30 questions per hour.
"""

import time
from collections import defaultdict

class RateLimiter:
    def __init__(self, max_requests: int = 30, window_seconds: int = 3600):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)

    def is_allowed(self, user_id: str) -> bool:
        now = time.time()
        # Clean old entries
        self.requests[user_id] = [
            t for t in self.requests[user_id]
            if now - t < self.window_seconds
        ]
        # Check limit
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        self.requests[user_id].append(now)
        return True

    def remaining(self, user_id: str) -> int:
        now = time.time()
        self.requests[user_id] = [
            t for t in self.requests[user_id]
            if now - t < self.window_seconds
        ]
        return max(0, self.max_requests - len(self.requests[user_id]))

# Global instance
limiter = RateLimiter()