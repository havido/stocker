import redis
import json
import os

class DatabaseManager:
    def __init__(self):
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)
        
    def save_analysis(self, identifier: str, data: dict):
        self.client.set(f"db:{identifier}", json.dumps(data))
        
    def get_analysis(self, identifier: str):
        val = self.client.get(f"db:{identifier}")
        if val:
            return json.loads(val)
        return None

    def publish_log(self, identifier: str, message: str):
        self.client.publish(f"logs:{identifier}", message)
