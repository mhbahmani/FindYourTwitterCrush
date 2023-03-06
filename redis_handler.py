from decouple import config
import redis


class Redis:
    def __init__(self) -> None:
        self.client = redis.Redis(
            host=config("REDIS_HOST", "localhost"),
            port=config("REDIS_PORT", 6479, cast=int),
            db=0)

    def add_event_to_queue(self, event: str, queue: str = "liking_users") -> None:
        self.client.rpush(queue, event)
    
    def get_event_from_queue(self, queue: str) -> str:
        event = self.client.lpop(queue)
        if event: return event.decode("utf-8")