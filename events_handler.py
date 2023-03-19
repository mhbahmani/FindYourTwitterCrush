from twitter_handler import Twitter
from redis_handler import Redis
from image_generator import merge_images


import time


twitter_client = Twitter()
redis_client = Redis()

# TODO: Handle duplicate usernames, in case of restarting the server

def most_liking_users(username: str):
    print("Finding most liking users for", username)
    liking_users, likes_avg = twitter_client.get_user_huge_fans(username)
    names = []
    for username, likes in liking_users.items():
        name = twitter_client.get_user_name_by_username(username)
        names.append(name)
    
    res = liking_users
    items = []
    l = list(reversed(list(res.items())[-12:]))
    i = 0
    for user, val in l:
        i += 1
        items.append([val, user, twitter_client.get_user_profile_image(user).replace("_normal", ""), names[-i]])
    merge_images(items, likes_avg)


def most_liked_users(username: str):
    liked_users = twitter_client.get_user_most_liked_users(username)
    names = []
    for username, _ in liked_users.items():
        names.append(twitter_client.get_user_name_by_username(username))

    res = liked_users
    items = []
    l = list(reversed(list(res.items())[-12:]))
    i = 0
    for user, val in l:
        i += 1
        items.append([val, user, twitter_client.get_user_profile_image(user).replace("_normal", ""), names[-i]])
    
    merge_images(items)


# ACTION = "liking_users"
ACTION = "liked_users"

if __name__ == "__main__":
    while True:
        username = redis_client.get_event_from_queue(ACTION)
        if username:
            if ACTION == "liking_users":
                most_liking_users(username)
            elif ACTION == "liked_users":
                most_liked_users(username)
            break
        time.sleep(1)