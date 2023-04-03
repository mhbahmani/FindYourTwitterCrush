from twitter_handler import Twitter
from redis_handler import Redis
from db import DB

import time


client = Twitter()
LIKING_USERS_SRC_TWEET_ID = 1638537552570220545

LIKES_SRC_TWEET_ID = 1642201471356682244

db_client = DB()
redis_client = Redis()

handled_users_liking = set()
handled_users_liked = set()


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
    all_progressings = redis_client.get_all_progressing_events("liking_users")
    repliers = client.get_tweet_replies_with_tweepy(LIKING_USERS_SRC_TWEET_ID)
    for replier in repliers:
        if replier[0] in handled_users_liking or replier[0] in all_progressings: continue
        print("Adding", replier, "to queue liking_users")
        redis_client.add_event_to_queue(replier, queue="liking_users")
        handled_users_liking.add(replier[0])
    direct_requests = client.get_directs_usernames()
    for request in direct_requests:
        if request['username'] in handled_users_liking: continue
        print("Adding", request, "to queue", "liking_users")
        redis_client.add_event_to_queue(request, queue="liking_users")
        handled_users_liking.add(request['username'])

def check_for_new_requests_on_likes():
    all_progressings = redis_client.get_all_progressing_events("liked_users")
    repliers = client.get_tweet_replies_with_tweepy(LIKES_SRC_TWEET_ID)
    for replier in repliers:
        if replier[0] in handled_users_liked or replier[0] in all_progressings: continue
        print("Adding", replier, "to queue liked_users")
        redis_client.add_event_to_queue(replier, queue="liked_users")
        handled_users_liked.add(replier[0])
    direct_requests = client.get_directs_usernames()
    for request in direct_requests:
        if request['username'] in handled_users_liked: continue
        print("Adding", request, "to queue", "liked_users")
        redis_client.add_event_to_queue([request['username'], str(request['user_id']), "d"], queue="liked_users")
        handled_users_liked.add(request['username'])

load_handled_users()
while True:
    # check_for_new_requests_on_most_liking()
    check_for_new_requests_on_likes()
    time.sleep(10 * 60)