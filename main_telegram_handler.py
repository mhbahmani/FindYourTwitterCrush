from telethon import TelegramClient, events
from telethon.errors import UserIsBlockedError
from decouple import config
from time import sleep

from src.redis_handler import Redis
from src.db import DB
from src.utils import generate_result_tweet_text
from src.twitter_handler import Twitter
from src.static_data import REQUEST_SOURCE
from src.messages import (
    too_many_requests_msg,
    request_accepted_msg,
    already_got_your_request_msg,
    NO_USERNAME_OF_LINK_PROVIDED_MSG,
    PRIVATE_ACCOUNT_ERROR_MSG,
    PROFILE_NOT_FOUND_MSG,
    ACCESS_DENIED_MSG,
    SUPPORT_MSG,
    USERNAME_NOT_FOUND_MSG,
    ALREADY_STARTED_MSG,
    START_MSG,
)

import re
import logging
import asyncio
import datetime


logging.basicConfig(
    filename="telegram_handler.log",
    filemode="a",
    format='%(asctime)s - %(levelname)s - %(message)s',
    level={
        'INFO': logging.INFO,
        'DEBUG': logging.DEBUG,
        'ERROR': logging.ERROR,
    }[config("LOG_LEVEL", default="INFO")])

loop = asyncio.get_event_loop()

QUEUE = config("QUEUE", "liked_users")
QUEUE_BLOCKED = QUEUE + "_blocked"
QUEUE_DONE = QUEUE + "_done"
REQUEST_LIMIT = 1

api_id = config("CLIENT_API_ID")
api_hash = config("CLIENT_API_HASH")
client = TelegramClient('anon_crush', api_id, api_hash)

SEND_SUPPORT_MSG = config("SEND_SUPPORT_MSG", default=True, cast=bool)
LIMITED_ACCESS_FOR_MY_FOLLOWINGS = config("LIMITED_ACCESS_FOR_MY_FOLLOWINGS", default=False, cast=bool)
ALLOW_REQUESTS_WHEN_QUEUE_SIZE_IS_LOW = config("ALLOW_REQUESTS_WHEN_QUEUE_SIZE_IS_LOW", default=True, cast=bool)
QUEUE_SIZE_TRESHOLD_ON_LIMITED_ACCESS = config("QUEUE_SIZE_TRESHOLD_ON_LIMITED_ACCESS", default=1, cast=int)

ADMIN_USER_ID = config("ADMIN_USER_ID", cast=int)
NO_LIMIT_USER_IDS = [int(user_id.strip()) for user_id in config("NO_LIMIT_USER_IDS").split(",")]

waiting_users_liking = set() # List of user_ids
waiting_users_liked = set() # List of user_ids
# This is required for cases that people send multiple requests and get access denied
blocked_users = set()

db_client = DB()
redis_client = Redis()

twitter_client = Twitter()
followings = []

SRC_TWEET_ID = 1769757048814686227


@client.on(events.NewMessage(pattern=r"/start"))
async def start_handler(event):
    user = {
        "user_id": event.original_update.message.peer_id.user_id,
        "username": event.message._sender.username
    } 
    if db_client.add_new_bot_user(user):
        await client.send_message(user.get("user_id"), START_MSG)
    else:
        await client.send_message(user.get("user_id"), ALREADY_STARTED_MSG)
    return


@client.on(events.NewMessage())
async def username_handler(event):
    text = event.raw_text
    if text == "/start" or "sendthistoallinblockedqueue" in text:
        return
    # print(text)
    user_id = event.original_update.message.peer_id.user_id
    username = event.message._sender.username
    
    try:
        loop.create_task(db_client.add_new_message(
            text, user_id,
            username,
            datetime.datetime.today().replace(microsecond=0).strftime('%Y-%m-%d %H:%M:%S'))
        )
    except Exception as e:
        logging.error(f"Storing message failed, message: {text} user_id: {user_id} username: {username}")
        logging.error(e)
        pass

    if not user_id in NO_LIMIT_USER_IDS \
        and redis_client.get_user_request_count(str(user_id), QUEUE) >= REQUEST_LIMIT:
        logging.info(f"Block request because of passing the request limit, user_id: {user_id}, username: {username}, text: {text}")
        await client.send_message(user_id, too_many_requests_msg.format(REQUEST_LIMIT))
        return

    # fetch the part of the text that matchs with https://.*
    text = text.split("?")[0]
    profile_url = re.findall(r'[h|H]ttps://.*', text)
    if not profile_url:
        twitter_username = re.findall(r'[a-zA-Z0-9_]+', text)
        if not twitter_username:
            await client.send_message(user_id, NO_USERNAME_OF_LINK_PROVIDED_MSG)
            return
        twitter_username = twitter_username[0]
        if not twitter_client.check_username_exists(twitter_username):
            await client.send_message(user_id, USERNAME_NOT_FOUND_MSG.format(twitter_username))
            return
    else:
        profile_url = profile_url[0]
        twitter_username = profile_url.strip().split("/")[-1].strip("/")
        if not twitter_client.check_username_exists(twitter_username):
            await client.send_message(user_id, PROFILE_NOT_FOUND_MSG.format(twitter_username))
            return

    if LIMITED_ACCESS_FOR_MY_FOLLOWINGS \
        and (not ALLOW_REQUESTS_WHEN_QUEUE_SIZE_IS_LOW or redis_client.get_queue_size(QUEUE) > QUEUE_SIZE_TRESHOLD_ON_LIMITED_ACCESS) \
        and not user_id in NO_LIMIT_USER_IDS \
        and not twitter_username.lower() in followings:
        logging.info(f"Access denied to username: {username}, twiiter_username: {twitter_username}, user_id: {user_id}")
        await client.send_message(user_id, ACCESS_DENIED_MSG, link_preview=False)
        if not user_id in blocked_users:
            redis_client.add_event_to_queue([twitter_username, str(user_id), REQUEST_SOURCE.BOT.value], QUEUE_BLOCKED)
            blocked_users.add(user_id)
        return
    
    if twitter_client.check_user_is_private_by_screen_name(twitter_username):
        logging.info(f"Access denied to private twitter account: {twitter_username}, requested by: {username}")
        await client.send_message(user_id, PRIVATE_ACCOUNT_ERROR_MSG.format(twitter_username))
        return

    # in_progress_usernames = redis_client.get_all_progressing_events(QUEUE)
    if user_id in waiting_users_liked:
        await client.send_message(user_id, already_got_your_request_msg)
        return

    print("Adding", twitter_username, "to queue", QUEUE, "tweet_id", user_id)
    redis_client.add_event_to_queue([twitter_username, str(user_id), REQUEST_SOURCE.BOT.value], queue=QUEUE)

    await client.send_message(user_id, request_accepted_msg, link_preview=False)
    
    waiting_users_liked.add(user_id)
    redis_client.increase_user_request_count(str(user_id), QUEUE)


async def handle_outputs():
    while True:
        try:
            event = redis_client.get_event_from_queue(QUEUE_DONE)
            if event:
                _, user_id, image_path = event
                user_id = int(user_id)
                logging.info(f"Send {image_path} for {user_id} in telegram")
                await client.send_message(user_id, generate_result_tweet_text(), file=image_path)
                if SEND_SUPPORT_MSG:
                    await client.send_message(user_id, SUPPORT_MSG, link_preview=False)
                waiting_users_liked.remove(user_id)
        except KeyError as e:
            pass
        except Exception as e:
            logging.error(f"Something went wrong on handling outputs: {e}")
        finally:
            await asyncio.sleep(10)


@client.on(events.NewMessage(pattern=r"/sendthistoallinblockedqueue.*"))
async def send_to_all_in_blockd_queue_users_handler(event):
    if event.original_update.message.peer_id.user_id != ADMIN_USER_ID:
        return
    
    logging.info("Sending a message to all users that are in blocked queue")
    
    message = event.raw_text.split("/sendthistoallinblockedqueue")[-1].strip()
    await client.send_message(ADMIN_USER_ID, message, link_preview=False)

    start = 0
    end = start + 30
    while True:
        removed_users_count_in_this_iteration = 0
        events = redis_client.get_events_in_queue_by_index_range(start, end, QUEUE_BLOCKED)
        if not events: break

        for _event in events:
            try:
                logging.info(f"Message sent to {_event.get('user_id')}")
                await client.send_message(int(_event.get("user_id")), message, link_preview=False)
            except UserIsBlockedError as e:
                logging.info(f"User {_event.get('screen_name')} {_event.get('user_id')} blocked the bot, removing from queue")
                redis_client.remove_event_from_queue([_event.get("screen_name"), _event.get("user_id"), _event.get("request_type")], QUEUE_BLOCKED)
                removed_users_count_in_this_iteration += 1
            except Exception as e:
                logging.error(e)
                logging.error(f"Error on user {_event.get('screen_name')} {_event.get('user_id')}")

        logging.info(f"Message sent to {len(events)} users, from index {start} to {end}")
        sleep(5)

        start = end + 1 - removed_users_count_in_this_iteration
        end = start + 30

    logging.info("Message sent to all the users in blocked queue")


async def load_followings():
    if not LIMITED_ACCESS_FOR_MY_FOLLOWINGS:
        logging.info("Loading followings skipped")
        return
    while True:
        global followings
        followings = [user.get("screen_name").lower() for user in twitter_client.get_user_followings("mh_bahmani")]
        logging.info(f"mh_bahmani followings loaded")
        await asyncio.sleep(60 * 60 * 5)


def load_all_liked_request_blocked_users():
    logging.info("Loading blocked user ids")
    for user_id in redis_client.get_all_liked_blocked_user_ids():
        blocked_users.add(int(user_id))

def load_waiting_users():
    logging.info("Loading warting users ids")
    # for username in db_client.get_all_handled_liking():
    #     handled_users_liking.add(username)
    # for username in db_client.get_all_handled_liked():
    #     handled_users_liked.add(username)

    for user_id in redis_client.get_all_user_ids_in_liked_queue():
        waiting_users_liking.add(int(user_id))
    for user_id in redis_client.get_all_user_ids_in_liked_queue():
        waiting_users_liked.add(int(user_id))

if __name__ == "__main__":
    logging.info("Starting the bot for queue: " + QUEUE)
    load_waiting_users()
    load_all_liked_request_blocked_users()
    client.start()
    loop.create_task(handle_outputs())
    loop.create_task(load_followings())
    client.run_until_disconnected()