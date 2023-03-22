from twitter_handler import Twitter
from redis_handler import Redis
from image_generator import merge_images

from db import DB

import time


db_client = DB()
twitter_client = Twitter()
redis_client = Redis()


def most_liking_users(username: str, tweet_id):
    print("Finding most liking users for", username)
    liking_users, likes_avg = twitter_client.get_user_huge_fans(username)
    names = []
    for _username, likes in liking_users.items():
        name = twitter_client.get_user_name_by_username(_username)
        names.append(name)
    
    res = liking_users
    items = []
    l = list(reversed(list(res.items())[-12:]))
    i = 0
    for user, val in l:
        i += 1
        items.append([val, user, twitter_client.get_user_profile_image(user).replace("_normal", ""), names[-i]])

    db_client.add_handled_liking({
        "username": username,
        "result": items
    })
    merge_images(items, likes_avg, username)

    # send tweet
    

def most_liked_users(username: str, tweet_id):
    liked_users = twitter_client.get_user_most_liked_users(username)
    names = []
    for _username, _ in liked_users.items():
        names.append(twitter_client.get_user_name_by_username(_username))

    res = liked_users
    items = []
    l = list(reversed(list(res.items())[-12:]))
    i = 0
    for user, val in l:
        i += 1
        items.append([val, user, twitter_client.get_user_profile_image(user).replace("_normal", ""), names[-i]])
    
    db_client.add_handled_liked({
        "username": username,
        "result": items
    })
    image_path = merge_images(items, username=username)
    twitter_client.tweet_result(image_path, tweet_id)
    

# ACTION = "liking_users"
ACTION = "liked_users"

if __name__ == "__main__":
    print("Starting to handle", ACTION, "events")
    while True:
        event = redis_client.get_event_from_queue(ACTION)
        if event:
            username, tweet_id = event
            print("Handling", ACTION, "event for", username, tweet_id)
            redis_client.add_username_to_progressing(username, f"{ACTION}-progressing")
            if username:
                if ACTION == "liking_users":
                    most_liking_users(username, tweet_id)
                elif ACTION == "liked_users":
                    most_liked_users(username, tweet_id)
        # else: print("Noting found in queue", ACTION)
        time.sleep(1)