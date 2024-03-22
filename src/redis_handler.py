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
            if len(splited_event) == 2:
                username, tweet_id = splited_event
                return username, tweet_id, "t"
            elif len(splited_event) == 3:
                username, tweet_id, type = splited_event
                return username, tweet_id, type
    def get_queue_size(self, queue: str) -> int:
        return int(self.client.llen(queue))

    def get_all_progressing_events(self, queue: str) -> list:
        return [user.decode("utf-8") for user in list(self.client.lrange(f"{queue}-progressing", 0, -1))]

    def get_all_in_liking_queue(self):
        return [user.decode("utf-8").split("####")[0] for user in list(self.client.lrange("liking_users", 0, -1))]
    
    def get_all_in_liked_queue(self):
        return [user.decode("utf-8").split("####")[0] for user in list(self.client.lrange("liked_users", 0, -1))]

    def get_all_user_ids_in_liked_queue(self):
        return [user.decode("utf-8").split("####")[1] for user in list(self.client.lrange("liked_users", 0, -1))]
    
    def get_user_request_count(self, user_id: str, request_type: str) -> int:
        count = self.client.get(self.generate_get_count_key(user_id, request_type))
        return int(count) if count else 0
    
    def increase_user_request_count(self, user_id: str, request_type: str) -> None:
        self.client.incr(self.generate_get_count_key(user_id, request_type), 1)

    def generate_get_count_key(self, user_id: str, request_type: str) -> str:
        return str(user_id) + "_" + request_type