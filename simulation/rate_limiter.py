"""
Rate limiter for Gemini API to avoid hitting request limits.
"""
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import deque


class GeminiRateLimiter:
    """
    Manages rate limiting for Gemini 2.0 Flash Exp API.

    Limits (as of 2024):
    - 10 requests per minute
    - 4 million tokens per minute
    - 1,500 requests per day
    """

    def __init__(self):
        # Rate limits
        self.requests_per_minute = 10
        self.requests_per_day = 1500
        self.tokens_per_minute = 4_000_000

        # Tracking
        self.request_times = deque(maxlen=100)
        self.daily_request_count = 0
        self.daily_reset_time = datetime.now()
        self.token_usage = deque(maxlen=100)

    def can_make_request(self, estimated_tokens: int = 500) -> Tuple[bool, str]:
        """Check if we can make a request now."""
        now = datetime.now()

        # Reset daily counter if needed
        if now - self.daily_reset_time > timedelta(days=1):
            self.daily_request_count = 0
            self.daily_reset_time = now
            print(f"Daily limit reset. New day started at {now}")

        # Check daily limit
        if self.daily_request_count >= self.requests_per_day:
            return False, f"Daily limit reached ({self.requests_per_day} requests)"

        # Check per-minute request limit
        one_minute_ago = now - timedelta(minutes=1)
        recent_requests = [t for t in self.request_times if t > one_minute_ago]

        if len(recent_requests) >= self.requests_per_minute:
            wait_time = 60 - (now - recent_requests[0]).total_seconds()
            return False, f"Rate limit: wait {int(wait_time)} seconds"

        # Check token limit
        recent_tokens = sum(
            entry['tokens'] for entry in self.token_usage
            if entry['time'] > one_minute_ago
        )

        if recent_tokens + estimated_tokens > self.tokens_per_minute:
            return False, f"Token limit would be exceeded ({recent_tokens + estimated_tokens} > {self.tokens_per_minute})"

        return True, "OK"

    def wait_if_needed(self, estimated_tokens: int = 500) -> None:
        """Wait if rate limited before making request."""
        while True:
            can_proceed, message = self.can_make_request(estimated_tokens)

            if can_proceed:
                break

            if "wait" in message.lower():
                # Extract wait time from message
                try:
                    wait_seconds = int(''.join(filter(str.isdigit, message.split("wait")[1].split("seconds")[0])))
                except:
                    wait_seconds = 10  # Default wait

                print(f"Rate limited: {message}")
                print(f"Waiting {wait_seconds} seconds...")
                time.sleep(wait_seconds + 1)  # Add 1 second buffer
            else:
                # Daily limit or token limit reached
                raise Exception(f"Rate limit error: {message}")

    def record_request(self, tokens_used: int = 500) -> None:
        """Record that a request was made."""
        now = datetime.now()

        # Record request time
        self.request_times.append(now)
        self.daily_request_count += 1

        # Record token usage
        self.token_usage.append({
            'time': now,
            'tokens': tokens_used
        })

        # Log status
        if self.daily_request_count % 10 == 0:
            print(f"Progress: {self.daily_request_count}/{self.requests_per_day} daily requests used")

    def get_status(self) -> Dict:
        """Get current rate limit status."""
        now = datetime.now()
        one_minute_ago = now - timedelta(minutes=1)

        recent_requests = len([t for t in self.request_times if t > one_minute_ago])
        recent_tokens = sum(
            entry['tokens'] for entry in self.token_usage
            if entry['time'] > one_minute_ago
        )

        return {
            'daily_requests_used': self.daily_request_count,
            'daily_requests_limit': self.requests_per_day,
            'recent_requests_per_minute': recent_requests,
            'requests_per_minute_limit': self.requests_per_minute,
            'recent_tokens_per_minute': recent_tokens,
            'tokens_per_minute_limit': self.tokens_per_minute,
            'can_make_request': self.can_make_request()[0]
        }