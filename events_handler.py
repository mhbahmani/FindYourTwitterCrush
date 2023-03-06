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
    liking = {}
    for username, likes in liking_users.items():
        name = twitter_client.get_user_name_by_username(username)
        liking[name] = f"{likes}%"
    
    res = liking_users
    names = list(liking_users.keys())
    items = []
    l = list(reversed(list(res.items())[-12:]))
    i = 0
    for user, val in l:
        i += 1
        items.append([val, user, twitter_client.get_user_profile_image(user).replace("_normal", ""), names[-i]])
    merge_images(items, likes_avg)


if __name__ == "__main__":
    while True:
        username = redis_client.get_event_from_queue("liking_users")
        if username:
            most_liking_users(username)
            break
        time.sleep(1)