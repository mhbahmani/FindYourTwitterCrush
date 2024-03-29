from src.twitter_handler import Twitter
from src.redis_handler import Redis
from src.image_generator import merge_images, check_output_image_is_present
from src.utils import generate_private_output_address, get_twitter_config_name
from src.exceptions import (
    PrivateAccountException,
    RateLimitException
)

from decouple import config

from src.db import DB

import time
import logging


logging.basicConfig(
    filename="events_handler.log",
    filemode="a",
    format='%(asctime)s - %(levelname)s' + f' - {get_twitter_config_name()}' + ' - %(message)s',
    level={
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG,
        'ERROR': logging.ERROR,
    }[config("LOG_LEVEL", default="INFO")])


db_client = DB()
twitter_client = Twitter()
redis_client = Redis()


RENEW_CACHED_IMAGES_ON_CACHE_TYPE_REQUESTS = config("RENEW_CACHED_IMAGES_ON_CACHE_TYPE_REQUESTS", default=False, cast=bool)
CHECK_IMAGE_CACHE = config("CHECK_IMAGE_CACHE", default=True, cast=bool)
NUMBER_OF_RESULTS = 12

# If the queue be empty for EMPTY_QUEUE_COUNTER_TRESHOLD, the handler checks for the blocked queue
HANDLE_BLOCKED_USERS_WHEN_QUEUE_IS_EMPTY_FOR_TOO_LONG = \
    config("HANDLE_BLOCKED_USERS_WHEN_QUEUE_IS_EMPTY_FOR_TOO_LONG", default=False, cast=bool)
# This variable shows the amount of time the queue should be empty for the handler to check the blocked queue
EMPTY_QUEUE_COUNTER_TRESHOLD = config("EMPTY_QUEUE_COUNTER_TRESHOLD", default=100, cast=int)


def most_liking_users(username: str, tweet_id, type: str = "t"):
    if type == "c":
        try:
            logging.info(f"Trying to cache output for {username}")
            # If renewing is not necessary and there is already an output for this user,
            # skip the request
            if not RENEW_CACHED_IMAGES_ON_CACHE_TYPE_REQUESTS \
                and check_output_image_is_present(username, "liking"):
                    logging.info(f"There is already an output of type liking for {username}")
                    return
            # If renewing is mandatory or there is no output for this user, make an output
            liking_users, likes_avg = twitter_client.get_user_most_liking_users(username)
                
        except Exception as e:
            logging.error(e)
            logging.error(username, tweet_id)
            return

        users = []
        for _scree_name in liking_users:
            user = liking_users.get(_scree_name)
            users.append([
                user.get("count", 0),
                _scree_name,
                user.get("profile_image_url"),
                user.get("name")
            ])
        image_path = merge_images(data=users, username=username, likes_avg=likes_avg)
        
        db_client.add_handled_liking({
            "username": username,
            "result": users
        })

        return

    if CHECK_IMAGE_CACHE:
        cached_path = check_output_image_is_present(username, "liking")
        if cached_path:
            logging.info(f"Found cached image for {username} in {cached_path}")
            if type == "d":
                user_id = tweet_id
                if not user_id:
                    user_id = twitter_client.get_user_id_by_username(username)
                output_address = generate_private_output_address(cached_path)
                twitter_client.send_result_in_direct(user_id, output_address)
                logging.info(f"Send result in direct for {username} in {cached_path}")
            else:
                # Not working, because of developer account suspension
                # twitter_client.tweet_result(cached_path, tweet_id)
                twitter_client.send_output_in_reply(cached_path, tweet_id)
                logging.info(f"Tweeted result for {username} in {cached_path}")
            return

    logging.info(f"Finding most liking users for {username}")
    try:
        liking_users, likes_avg = twitter_client.get_user_most_liking_users(username, NUMBER_OF_RESULTS)
    except Exception as e:
        logging.error(e)
        logging.error(username, tweet_id)
        return

    users = []
    for _scree_name in liking_users:
        user = liking_users.get(_scree_name)
        users.append([
            user.get("count", 0),
            _scree_name,
            user.get("profile_image_url"),
            user.get("name")
        ])
    
    db_client.add_handled_liking({
        "username": username,
        "result": users
    })

    private = True if type == "d" else False
    image_path = merge_images(data=users, username=username, likes_avg=likes_avg, private=private)
    if type == "d":
        user_id = tweet_id
        if not user_id:
            user_id = twitter_client.get_user_id_by_username(username)
        output_address = generate_private_output_address(image_path)
        twitter_client.send_result_in_direct(user_id, output_address)
        logging.info(f"Send result in direct for {username} in {image_path}")
    else:
        # Not working, because of developer account suspension
        # twitter_client.tweet_result(image_path, tweet_id)
        twitter_client.send_output_in_reply(image_path, tweet_id)
        logging.info(f"result for {username} in {image_path} tweeted")

def most_liked_users(username: str, tweet_id, type: str = "t", queue: str = "liked_users"):
    if type == "c":
        try:
            logging.info(f"Trying to cache output for {username}")
            # If renewing is not necessary and there is already an output for this user,
            # skip the request
            if not RENEW_CACHED_IMAGES_ON_CACHE_TYPE_REQUESTS \
                and check_output_image_is_present(username, "liked"):
                    logging.info(f"There is already an output of type liked for {username}")
                    return
            # If renewing is mandatory or there is no output for this user, make an output
            liked_users, total_likes = twitter_client.get_user_most_liked_users(username)
        except RateLimitException as e:
            logging.error(e.message)
            redis_client.add_event_to_head_of_the_queue([username, str(tweet_id), type], queue)
            logging.info("Going to sleep for 5 hours")
            time.sleep(5 * 60 * 60)
            return
        except PrivateAccountException as e:
            logging.error(f"\"{username}\" is private, skipping")
            return
            # TODO: Send a message (based on the type of the request) to the user
        except Exception as e:
            logging.error(e)
            return

        users = []
        for screen_name in liked_users:
            users.append(
                [
                    liked_users.get(screen_name, {}).get("count", 0),
                    screen_name,
                    liked_users.get(screen_name, {}).get("profile_image_url"),
                    liked_users.get(screen_name, {}).get("name")
                ]
            )
        image_path = merge_images(data=users, username=username, total_likes=total_likes)

        db_client.add_handled_liked({
            "username": username,
            "result": users
        })
        return

    if CHECK_IMAGE_CACHE:
        cached_path = check_output_image_is_present(username, "liked")
        if cached_path:
            logging.info(f"Found cached image for {username} in {cached_path}")
            if type == "d":
                user_id = tweet_id
                if not user_id:
                    user_id = twitter_client.get_user_id_by_username(username)
                output_address = generate_private_output_address(cached_path)
                twitter_client.send_result_in_direct(user_id, output_address)
                logging.info(f"Send result in direct for {username} in {cached_path}")
            elif type == "b":
                user_id = tweet_id
                redis_client.add_event_to_queue([username, user_id, cached_path], queue="liked_users_done")
            else:
                # Not working, because of developer account suspension
                twitter_client.send_output_in_reply(cached_path, tweet_id)
                logging.info(f"Tweeted result for {username} in {cached_path}")
            return

    logging.info(f"Finding most liked users for {username}")
    try:
        if not RENEW_CACHED_IMAGES_ON_CACHE_TYPE_REQUESTS:
            users, total_likes = db_client.get_handled_liked(username)
        # If there was no record for this user on database
        # TODO: Move this to redis
        if RENEW_CACHED_IMAGES_ON_CACHE_TYPE_REQUESTS or not users:
            try:
                liked_users, total_likes = twitter_client.get_user_most_liked_users(username, NUMBER_OF_RESULTS)
            except RateLimitException as e:
                logging.error(e.message)
                redis_client.add_event_to_head_of_the_queue([username, str(tweet_id), type], queue)
                logging.info("Going to sleep for 5 hours")
                time.sleep(5 * 60 * 60)
                return
            except PrivateAccountException as e:
                logging.error(f"\"{username}\" is private, skipping")
                return
                # TODO: Send a message (based on the type of the request) to the user
            except Exception as e:
                logging.error(e)
                return
            users = []
            for screen_name in liked_users:
                users.append(
                    [
                        liked_users.get(screen_name, {}).get("count", 0),
                        screen_name,
                        liked_users.get(screen_name, {}).get("profile_image_url"),
                        liked_users.get(screen_name, {}).get("name")
                    ]
                )

            db_client.add_handled_liked({
                "username": username,
                "result": users,
                "total_likes": total_likes
            })

    except Exception as e:
        logging.error(e)
        logging.error(username, tweet_id)
        return

    private = True if type == "d" else False
    image_path = merge_images(data=users, username=username, total_likes=total_likes, private=private)
    if type == "d":
        user_id = tweet_id
        if not user_id:
            user_id = twitter_client.get_user_id_by_username(username)
        output_address = generate_private_output_address(image_path)
        twitter_client.send_result_in_direct(user_id, output_address)
        logging.info(f"Send result in direct for {username} in {image_path}")
    elif type == "b":
        user_id = tweet_id
        redis_client.add_event_to_queue([username, user_id, image_path], queue="liked_users_done")
    else:
        # Not working, because of developer account suspension
        twitter_client.send_output_in_reply(image_path, tweet_id)
        logging.info(f"result for {username} in {image_path} tweeted")

# ACTION = "liking_users"
ACTION = "liked_users"


if __name__ == "__main__":
    logging.info(f"Starting to handle {ACTION} events")
    empty_queue_counter = 0
    while True:
        event = redis_client.get_event_from_queue(ACTION)

        if not event:
            if HANDLE_BLOCKED_USERS_WHEN_QUEUE_IS_EMPTY_FOR_TOO_LONG:
                empty_queue_counter += 1
                if empty_queue_counter > EMPTY_QUEUE_COUNTER_TRESHOLD:
                    logging.info("Checking blocked queue")
                    event = redis_client.get_event_from_queue(ACTION + "_blocked")
            # If an event fetched or HANDLE_BLOCKED_USERS_WHEN_QUEUE_IS_EMPTY_FOR_TOO_LONG is not set
            if not event:
                time.sleep(5)
                continue
        
        empty_queue_counter = 0

        username, tweet_id, type = event
        logging.info(f"Handling {ACTION} event for {username} {tweet_id} from {'directs' if type == 'd' else 'tweets'}")
        redis_client.add_username_to_progressing(username, f"{ACTION}-progressing")
        if username:
            if ACTION == "liking_users":
                most_liking_users(username, tweet_id, type)
            elif ACTION == "liked_users":
                most_liked_users(username, tweet_id, type)

        time.sleep(5)
