from twitter_handler import Twitter
from redis_handler import Redis
from db import DB

import time


client = Twitter()
LIKING_USERS_SRC_TWEET_ID = 1633814696355680256

LIKES_SRC_TWEET_ID = 1636379732823666689

db_client = DB()
redis_client = Redis()

handled_users_liking = set()
handled_users_liked = set()


def load_handled_users():
    for user in db_client.get_all_handled_liking():
        handled_users_liking.add(user["username"])
    for user in db_client.get_all_handled_liked():
        handled_users_liked.add(user["username"])

    for user in redis_client.get_all_in_liking_queue():
        handled_users_liking.add(user.decode("utf-8"))
    for user in redis_client.get_all_in_liked_queue():
        handled_users_liked.add(user.decode("utf-8"))


def check_for_new_requests_on_most_liking():
    all_progressings = redis_client.get_all_progressing_events("liking_users")
    repliers = client.get_tweet_repliers(LIKING_USERS_SRC_TWEET_ID)
    for replier in repliers:
        if replier in handled_users_liking or replier in all_progressings: continue
        print("Adding", replier, "to queue liking_users")
        redis_client.add_event_to_queue(replier, queue="liking_users")
        handled_users_liking.add(replier)

def check_for_new_requests_on_likes():
    all_progressings = redis_client.get_all_progressing_events("liked_users")
    repliers = client.get_tweet_repliers(LIKES_SRC_TWEET_ID)
    for replier in repliers:
        if replier in handled_users_liked or replier in all_progressings: continue
        print("Adding", replier, "to queue liked_users")
        redis_client.add_event_to_queue(replier, queue="liked_users")
        handled_users_liked.add(replier)


load_handled_users()
while True:
    check_for_new_requests_on_most_liking()
    check_for_new_requests_on_likes()
    time.sleep(60)