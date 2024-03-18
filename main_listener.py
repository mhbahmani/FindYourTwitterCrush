from src.twitter_handler import Twitter
from src.redis_handler import Redis
from src.db import DB

import datetime
import time


client = Twitter()
LIKING_USERS_SRC_TWEET_ID = 123

LIKES_SRC_TWEET_ID = 123

db_client = DB()
redis_client = Redis()

handled_users_liking = set() # List of usersnames
handled_users_liked = set() # List of usernames


def load_handled_users():
    for username in db_client.get_all_handled_liking():
        handled_users_liking.add(username)
    for username in db_client.get_all_handled_liked():
        handled_users_liked.add(username)

    for user in redis_client.get_all_in_liking_queue():
        handled_users_liking.add(user)
    for user in redis_client.get_all_in_liked_queue():
        handled_users_liked.add(user)


def check_for_new_requests_on_most_liking():
    in_progress_usernames = redis_client.get_all_progressing_events("liking_users")
    repliers = client.get_replied_users(LIKING_USERS_SRC_TWEET_ID)
    for screen_name in repliers:
        if screen_name in handled_users_liking or screen_name in in_progress_usernames: continue
        print("* Adding", screen_name, "to queue liking_users, tweet_id", repliers.get(screen_name)[1])
        redis_client.add_event_to_queue(repliers[screen_name], queue="liking_users")
        handled_users_liking.add(screen_name)

    # direct_requests = client.get_direct_usernames(datetime.datetime(2024, 3, 10))
    # for screen_name in direct_requests:
    #     if screen_name in handled_users_liking or screen_name in in_progress_usernames: continue
    #     print("* Adding", screen_name, "request to queue liking_users, conversation id:", direct_requests[screen_name].get("conversation_id"))
    #     redis_client.add_event_to_queue([screen_name, str(direct_requests[screen_name].get('conversation_id')), "d"], queue="liking_users")
    #     handled_users_liking.add(screen_name)

def check_for_new_requests_on_likes():
    in_progress_usernames = redis_client.get_all_progressing_events("liked_users")
    repliers = client.get_replied_users(LIKES_SRC_TWEET_ID)
    for screen_name in repliers:
        if screen_name in handled_users_liked or screen_name in in_progress_usernames: continue
        print("= Adding", screen_name, "to queue liked_users, tweet_id", repliers.get(screen_name)[1])
        redis_client.add_event_to_queue(repliers[screen_name], queue="liked_users")
        handled_users_liked.add(screen_name)

    # direct_requests = client.get_direct_usernames(datetime.datetime(2024, 3, 10))
    # for screen_name in direct_requests:
    #     if screen_name in handled_users_liked or screen_name in in_progress_usernames: continue
    #     print("= Adding", screen_name, "request to queue liked_users, conversation id:", direct_requests[screen_name].get("conversation_id"))
    #     redis_client.add_event_to_queue([screen_name, str(direct_requests[screen_name].get('conversation_id')), "d"], queue="liked_users")
    #     handled_users_liked.add(screen_name)

load_handled_users()
while True:
    # check_for_new_requests_on_most_liking()
    check_for_new_requests_on_likes()
    time.sleep(10 * 60)