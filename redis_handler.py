from decouple import config
import redis


class Redis:
    def __init__(self) -> None:
        self.client = redis.Redis(
            host=config("REDIS_HOST", "localhost"),
            port=config("REDIS_PORT", 6479, cast=int),
            db=0)

    def add_event_to_queue(self, event: str, queue: str = "liking_users") -> None:
        self.client.rpush(queue, f"{event[0]}####{event[1]}")
    
    def get_event_from_queue(self, queue: str) -> str:
        event = self.client.lpop(queue)
        if event:
            event = event.decode("utf-8")
            username, tweet_id = event.split("####")
            return username, tweet_id

        
    def get_all_progressing_events(self, queue: str) -> list:
        return list(self.client.lrange(f"{queue}-progressing", 0, -1))

    def get_all_in_liking_queue(self):
        return [user.decode("utf-8").split("####")[0] for user in list(self.client.lrange("liking_users", 0, -1))]
    
    def get_all_in_liked_queue(self):
        return [user.decode("utf-8").split("####")[0] for user in list(self.client.lrange("liked_users", 0, -1))]