from twitter_handler import Twitter
from redis_handler import Redis
from image_generator import merge_images, retrieve_image_path

from decouple import config

from db import DB

import time


db_client = DB()
twitter_client = Twitter()
redis_client = Redis()


CHECK_IMAGE_CACHE = config("CHECK_IMAGE_CACHE", True, cast=bool)


def most_liking_users(username: str, tweet_id, type: str = "t"):
    if CHECK_IMAGE_CACHE:
        cached_path = retrieve_image_path(username, "liking")
        if cached_path:
            print("Found cached image for", username, "in", cached_path)
            if type == "d":
                user_id = tweet_id
                if not user_id:
                    user_id = twitter_client.get_user_id_by_user_name(username)
                twitter_client.send_result_in_direct(cached_path, user_id)
                print("Send result in direct for", username, "in", cached_path)
            else:
                twitter_client.tweet_result(cached_path, tweet_id)
                print("Tweeted result for", username, "in", cached_path)
            return

    print("Finding most liking users for", username)
    liking_users, likes_avg = twitter_client.get_user_huge_fans(username)

    items = []

    liking_users = list(reversed(list(liking_users.items())[-12:]))
    for _username, data in liking_users:
        items.append([data.get("count", 0), _username, data.get("profile_image_url"), data.get("name")])

    db_client.add_handled_liking({
        "username": username,
        "result": items
    })
    image_path = merge_images(items, likes_avg, username)
    if type == "d":
        user_id = tweet_id
        if not user_id:
            user_id = twitter_client.get_user_id_by_user_name(username)
        twitter_client.send_result_in_direct(image_path, user_id)
        print("Send result in direct for", username, "in", image_path)
    else:
        twitter_client.tweet_result(image_path, tweet_id)
        print("Tweeted result for", username, "in", image_path)
    

def most_liked_users(username: str, tweet_id, type: str = "t"):
    if CHECK_IMAGE_CACHE:
        cached_path = retrieve_image_path(username, "liked")
        if cached_path:
            print("Found cached image for", username, "in", cached_path)
            if type == "d":
                user_id = tweet_id
                if not user_id:
                    user_id = twitter_client.get_user_id_by_user_name(username)
                twitter_client.send_result_in_direct(cached_path, user_id)
                print("Send result in direct for", username, "in", cached_path)
            else:
                twitter_client.tweet_result(cached_path, tweet_id)
                print("Tweeted result for", username, "in", cached_path)
            return

    print("Finding most liked users for", username)
    try:
        liked_users, total_likes = twitter_client.get_user_most_liked_users(username)
    except Exception as e:
        print(e)
        print(username, tweet_id)
        return

    items = []
    liked_users = list(reversed(list(liked_users.items())[-12:]))
    for _username, data in liked_users:
        items.append([data.get("count", 0), _username, data.get("profile_image_url"), data.get("name")])

    image_path = merge_images(items, username=username, total_likes=total_likes)
    if type == "d":
        user_id = tweet_id
        if not user_id:
            user_id = twitter_client.get_user_id_by_user_name(username)
        twitter_client.send_result_in_direct(image_path, user_id)
        print("Send result in direct for", username, "in", image_path)
    else:
        twitter_client.tweet_result(image_path, tweet_id)
        print("Tweeted result for", username, "in", image_path)
    db_client.add_handled_liked({
        "username": username,
        "result": items
    })
    

# ACTION = "liking_users"
ACTION = "liked_users"


if __name__ == "__main__":
    # username, tweet_id = "mh_bahmani", None
    # # most_liking_users(username, tweet_id)
    # most_liked_users(username, tweet_id, "d")
    # exit()

    print("Starting to handle", ACTION, "events")
    while True:
        event = redis_client.get_event_from_queue(ACTION)
        if event:
            username, tweet_id, type = event
            print("Handling", ACTION, "event for", username, tweet_id, f"from {'directs' if type == 'd' else 'tweets'}")
            redis_client.add_username_to_progressing(username, f"{ACTION}-progressing")
            if username:
                if ACTION == "liking_users":
                    most_liking_users(username, tweet_id, type)
                elif ACTION == "liked_users":
                    most_liked_users(username, tweet_id, type)
        # else: print("Noting found in queue", ACTION)
        time.sleep(1)
