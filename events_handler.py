from twitter_handler import Twitter
from redis_handler import Redis

import time


twitter_client = Twitter()
redis_client = Redis()


def most_liking_users(username: str):
    pass


if __name__ == "__main__":
    while True:
        username = redis_client.get_event_from_queue("liking_users")
        most_liking_users(username)
        time.sleep(5)