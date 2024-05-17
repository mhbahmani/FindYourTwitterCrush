from src.twitter_handler import Twitter
from src.redis_handler import Redis
from src.image_generator import merge_images, check_output_image_is_present
from src.utils import generate_private_output_address, get_twitter_config_name
from src.exceptions import (
    PrivateAccountException,
    RateLimitException
)
from src.static_data import (
    REQUEST_SOURCE,
    REQUEST_TYPE
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

SHORT_VERSION_OUTPUT = config("SHORT_VERSION_OUTPUT", default=False, cast=bool)


def most_liking_users(username: str, tweet_id, type: str = "t"):
    # Deprecated
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
    # Deprecated
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
        image_path = merge_images(data=users, username=username, total_likes=total_likes, short_version=SHORT_VERSION_OUTPUT)

        db_client.add_handled_liked({
            "username": username,
            "result": users,
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
    image_path = merge_images(data=users, username=username, total_likes=total_likes, private=private, short_version=SHORT_VERSION_OUTPUT)
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


def handle_request(username: str, tweet_id, type: str = "t", queue: str = "liked_users", handler = twitter_client.get_user_most_liked_users):
    output_image_path_extension = queue.replace("_users", "")
    if type == REQUEST_SOURCE.CACHE.value:
        try:
            logging.info(f"Trying to cache {queue} output for {username}")
            # If renewing is not necessary and there is already an output for this user,
            # skip the request
            if not RENEW_CACHED_IMAGES_ON_CACHE_TYPE_REQUESTS \
                and check_output_image_is_present(username, output_image_path_extension):
                    logging.info(f"There is already an output of type {queue} for {username}")
                    return
            # If renewing is mandatory or there is no output for this user, make an output
            # users is a dictionary of users
            # likes_count is likes average (in case of liking users) or total number of likes (in case of liked users)
            users, likes_count = handler(username)
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

        users_data = []
        for screen_name in users:
            users_data.append(
                [
                    users.get(screen_name, {}).get("count", 0),
                    screen_name,
                    users.get(screen_name, {}).get("profile_image_url"),
                    users.get(screen_name, {}).get("name")
                ]
            )
        if queue == REQUEST_TYPE.LIKED.value:
            image_path = merge_images(data=users_data, username=username, total_likes=likes_count, short_version=SHORT_VERSION_OUTPUT)
        elif queue == REQUEST_TYPE.LIKING.value:
            image_path = merge_images(data=users_data, username=username, likes_avg=likes_count, short_version=SHORT_VERSION_OUTPUT)

        if queue == REQUEST_TYPE.LIKED.value:
            db_client.add_handled_liked({
                "username": username,
                "result": users_data
            })
        elif queue == REQUEST_TYPE.LIKING.value:
            db_client.add_handled_liking({
                "username": username,
                "result": users_data
            })
        return

    if CHECK_IMAGE_CACHE:
        cached_path = check_output_image_is_present(username, output_image_path_extension)
        if cached_path:
            logging.info(f"Found cached image of type {queue} for {username} in {cached_path}")
            if type == REQUEST_SOURCE.DIRECT.value: 
                # Not working
                user_id = tweet_id
                if not user_id:
                    user_id = twitter_client.get_user_id_by_username(username)
                output_address = generate_private_output_address(cached_path)
                twitter_client.send_result_in_direct(user_id, output_address)
                logging.info(f"Send result in direct for {username} in {cached_path}")
            elif type == REQUEST_SOURCE.BOT.value:
                user_id = tweet_id
                redis_client.add_event_to_queue([username, user_id, cached_path], queue=f"{queue}_done")
            else:
                # Not working, because of developer account suspension
                twitter_client.send_output_in_reply(cached_path, tweet_id)
                logging.info(f"Tweeted result for {username} in {cached_path}")
            return

    logging.info(f"Finding most {queue.replace('_', ' ')} for {username}")
    try:
        if not RENEW_CACHED_IMAGES_ON_CACHE_TYPE_REQUESTS:
            if queue == REQUEST_TYPE.LIKED.value:
                users, likes_count = db_client.get_handled_liked(username)
            elif queue == REQUEST_TYPE.LIKING.value:
                users, likes_count = db_client.get_handled_liking(username)
        # If there was no record for this user on database
        if RENEW_CACHED_IMAGES_ON_CACHE_TYPE_REQUESTS or not users:
            try:
                users, likes_count = handler(username, NUMBER_OF_RESULTS)
                logging.info(f"Running handler of type {queue} for {username} ended")
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
            users_data = []
            for screen_name in users:
                users_data.append(
                    [
                        users.get(screen_name, {}).get("count", 0),
                        screen_name,
                        users.get(screen_name, {}).get("profile_image_url"),
                        users.get(screen_name, {}).get("name")
                    ]
                )

            if queue == REQUEST_TYPE.LIKED.value:
                db_client.add_handled_liked({
                    "username": username,
                    "result": users_data,
                    "total_likes": likes_count
                })
            elif queue == REQUEST_TYPE.LIKING.value:
                db_client.add_handled_liking({
                    "username": username,
                    "result": users_data,
                    "likes_avg": likes_count
                })

    except Exception as e:
        logging.error(e)
        logging.error(username, tweet_id)
        return

    private = True if type == REQUEST_SOURCE.DIRECT.value else False

    if queue == REQUEST_TYPE.LIKED.value:
        image_path = merge_images(data=users_data, username=username, total_likes=likes_count, short_version=SHORT_VERSION_OUTPUT, private=private)
    elif queue == REQUEST_TYPE.LIKING.value:
        image_path = merge_images(data=users_data, username=username, likes_avg=likes_count, short_version=SHORT_VERSION_OUTPUT, private=private)
    if type == REQUEST_SOURCE.DIRECT.value:
        # Not working, Not updated
        user_id = tweet_id
        if not user_id:
            user_id = twitter_client.get_user_id_by_username(username)
        output_address = generate_private_output_address(image_path)
        twitter_client.send_result_in_direct(user_id, output_address)
        logging.info(f"Send result in direct for {username} in {image_path}")
    elif type == REQUEST_SOURCE.BOT.value:
        user_id = tweet_id
        redis_client.add_event_to_queue([username, user_id, image_path], queue=f"{queue}_done")
        logging.info(f"results of type {queue} for {username} added to {queue}_done")
    else:
        # Not working, because of developer account suspension
        twitter_client.send_output_in_reply(image_path, tweet_id)
        logging.info(f"result of type {queue} for {username} in {image_path} tweeted")

ACTION = config("ACTION", default="liked_users")
# ACTION = "liking_users"
# ACTION = "liked_users"


if __name__ == "__main__":
    logging.info(f"Starting to handle {ACTION} events")
    empty_queue_counter = 0
    while True:
        event = redis_client.get_event_from_queue(ACTION)

        if not event:
            if HANDLE_BLOCKED_USERS_WHEN_QUEUE_IS_EMPTY_FOR_TOO_LONG:
                empty_queue_counter += 1
                if empty_queue_counter > EMPTY_QUEUE_COUNTER_TRESHOLD:
                    logging.info(f"Checking {ACTION}_blocked queue")
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
            if ACTION == REQUEST_TYPE.LIKING.value:
                handle_request(
                    username, tweet_id, type, ACTION,
                    handler=twitter_client.get_user_most_liking_users
                )
            elif ACTION == REQUEST_TYPE.LIKED.value:
                handle_request(
                    username, tweet_id, type, ACTION,
                    handler=twitter_client.get_user_most_liked_users
                )

        time.sleep(5)
