from twitter_handler import Twitter
from redis_handler import Redis

import time


client = Twitter()
LIKING_USERS_SRC_TWEET_ID = 1632440250646577153
LIKES_SRC_TWEET_ID =1632440250646577153

redis_client = Redis()

def check_for_new_requests_on_most_liking():
    repliers = client.get_tweet_repliers(LIKING_USERS_SRC_TWEET_ID)
    for replier in repliers:
        print("Adding", replier, "to queue liking_users")
        redis_client.add_event_to_queue(replier, queue="liking_users")


def check_for_new_requests_on_likes():
    repliers = client.get_tweet_repliers(LIKES_SRC_TWEET_ID)
    for replier in repliers:
        print("Adding", replier, "to queue likes")
        redis_client.add_event_to_queue(replier, queue="likes")

while True:
    check_for_new_requests_on_most_liking()
    time.sleep(60)