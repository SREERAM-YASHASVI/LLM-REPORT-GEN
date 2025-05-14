import time
import threading
import asyncio
from collections import deque
import logging

logger = logging.getLogger(__name__)

class EnhancedRateLimiter:
    """
    Enhanced rate limiter with request queuing capability.
    Handles bursts of requests more gracefully by queuing instead of rejecting.
    """
    def __init__(self, capacity: int, leak_rate_per_sec: float, max_queue_size: int = 20):
        self.capacity = capacity
        self.leak_rate = leak_rate_per_sec
        self.water = 0.0
        self.last_check = time.time()
        self.lock = threading.Lock()
        self.queue = deque(maxlen=max_queue_size)
        self.max_queue_size = max_queue_size
        
    def allow_request(self) -> bool:
        """
        Returns True if the request is allowed immediately, False if rate limited.
        Does not implement queuing - use allow_request_with_queue for that.
        """
        with self.lock:
            now = time.time()
            elapsed = now - self.last_check
            leaked = elapsed * self.leak_rate
            self.water = max(0.0, self.water - leaked)
            self.last_check = now

            if self.water < self.capacity:
                self.water += 1
                return True
            return False
            
    async def allow_request_with_queue(self, timeout: float = 5.0) -> bool:
        """
        Async version that queues requests when rate limited.
        Returns True if request is processed within timeout, False otherwise.
        """
        # First try immediate processing
        if self.allow_request():
            return True
            
        # Otherwise queue the request
        if len(self.queue) >= self.max_queue_size:
            logger.warning(f"Queue full ({self.max_queue_size} requests) - rejecting request")
            return False
            
        # Create future for this request
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self.queue.append(future)
        
        try:
            # Wait for processing with timeout
            await asyncio.wait_for(future, timeout)
            return True
        except asyncio.TimeoutError:
            # Remove from queue if still there
            if future in self.queue:
                self.queue.remove(future)
            logger.warning(f"Request timed out after {timeout}s in queue")
            return False
            
    async def process_queue(self):
        """
        Process queued requests at the configured rate.
        Should be run as a background task.
        """
        while True:
            await asyncio.sleep(1.0 / self.leak_rate)  # Sleep based on rate
            
            if not self.queue:
                continue
                
            with self.lock:
                now = time.time()
                elapsed = now - self.last_check
                leaked = elapsed * self.leak_rate
                self.water = max(0.0, self.water - leaked)
                self.last_check = now
                
                if self.water < self.capacity and self.queue:
                    self.water += 1
                    future = self.queue.popleft()
                    if not future.done():
                        future.set_result(True)

# Example usage:
# limiter = EnhancedRateLimiter(capacity=20, leak_rate_per_sec=5)
# 
# # In FastAPI startup event:
# @app.on_event("startup")
# async def startup_event():
#     asyncio.create_task(limiter.process_queue())
#
# # In API endpoint:
# if await limiter.allow_request_with_queue(timeout=3.0):
#     # Process request
# else:
#     # Return 429 Too Many Requests 