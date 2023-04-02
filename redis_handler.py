from decouple import config
import redis


class Redis:
    def __init__(self) -> None:
        self.client = redis.Redis(
            host=config("REDIS_HOST", "localhost"),
            port=config("REDIS_PORT", 6479, cast=int),
            db=0)

    def add_event_to_queue(self, event: str, queue: str = "liking_users") -> None:
        self.client.rpush(queue, "####".join(event))

    def add_username_to_progressing(self, username: str, queue: str) -> None:
        self.client.rpush(queue, username)

    def get_event_from_queue(self, queue: str) -> str:
        event = self.client.lpop(queue)
        if event:
            event = event.decode("utf-8")
            splited_event = event.split("####")
            if len(splited_event) == 2 or splited_event[-1] == "t":
                username, tweet_id = splited_event[0], splited_event[1]
                return username, tweet_id, "t"
            elif len(splited_event) == 3 and splited_event[-1] == "d":
                username, tweet_id, _ = splited_event
                return username, tweet_id, "d"
        
    def get_all_progressing_events(self, queue: str) -> list:
        return list(self.client.lrange(f"{queue}-progressing", 0, -1))

    def get_all_in_liking_queue(self):
        return [user.decode("utf-8").split("####")[0] for user in list(self.client.lrange("liking_users", 0, -1))]
    
    def get_all_in_liked_queue(self):
        return [user.decode("utf-8").split("####")[0] for user in list(self.client.lrange("liked_users", 0, -1))]