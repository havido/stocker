"""
Shared broker definition.

Both the API server and the Worker import this module.
The API uses it to push tasks into the queue.
The Worker uses it to pull tasks out of the queue.
"""
import os
import taskiq_redis

redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
broker = taskiq_redis.ListQueueBroker(redis_url)
