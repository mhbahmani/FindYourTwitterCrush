from telethon import TelegramClient, events
from decouple import config

from src.redis_handler import Redis
from src.db import DB
from src.utils import generate_result_tweet_text
from src.messages import (
    error_template,
    too_many_requests_msg,
    request_accepted_msg,
    already_got_your_request_msg,
    ALREADY_STARTED_MSG,
    START_MSG,
)

import re
import logging
import asyncio

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

REQUEST_LIMIT = 1

api_id = config("CLIENT_API_ID")
api_hash = config("CLIENT_API_HASH")
client = TelegramClient('anon_crush', api_id, api_hash)

NO_LIMIT_USER_IDS = [int(user_id.strip()) for user_id in config("NO_LIMIT_USER_IDS").split(",")]

handled_users_liking = set() # List of usersnames
handled_users_liked = set() # List of usernames

db_client = DB()
redis_client = Redis()


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
    if text == "/start":
        return
    # print(text)
    user_id = event.original_update.message.peer_id.user_id
    # print(redis_client.get_user_request_count(str(user_id), "liked_users"))
    if not user_id in NO_LIMIT_USER_IDS \
        and redis_client.get_user_request_count(str(user_id), "liked_users") >= REQUEST_LIMIT:
        await client.send_message(user_id, too_many_requests_msg.format(REQUEST_LIMIT))
        return

    # fetch the part of the text that matchs with https://.*
    profile_url = re.findall(r'https://.*', text)
    if not profile_url:
        await client.send_message(user_id, error_template)
        return
    else: profile_url = profile_url[0]
    twitter_username = profile_url.strip().split("/")[-1]

    # in_progress_usernames = redis_client.get_all_progressing_events("liked_users")
    if user_id in handled_users_liked:
        await client.send_message(user_id, already_got_your_request_msg)
        return
    print("= Adding", twitter_username, "to queue liked_users, user_d", user_id)
    redis_client.add_event_to_queue([twitter_username, str(user_id), "b"], queue="liked_users")

    await client.send_message(user_id, request_accepted_msg, link_preview=False)
    
    handled_users_liked.add(user_id)
    redis_client.increase_user_request_count(str(user_id), "liked_users")


async def send_output(user_id, image_path):
    await client.start()
    await client.send_message(user_id, generate_result_tweet_text(), link_preview=False, file=image_path)
    await client.disconnect()

async def handle_outputs():
    while True:
        event = redis_client.get_event_from_queue("liked_users_done")
        if event:
            _, user_id, image_path = event
            user_id = int(user_id)
            await client.send_message(user_id, generate_result_tweet_text(), file=image_path)
        await asyncio.sleep(10)


def load_handled_users():
    # for username in db_client.get_all_handled_liking():
    #     handled_users_liking.add(username)
    # for username in db_client.get_all_handled_liked():
    #     handled_users_liked.add(username)

    for user_id in redis_client.get_all_user_ids_in_liked_queue():
        handled_users_liking.add(user_id)
    for user_id in redis_client.get_all_user_ids_in_liked_queue():
        handled_users_liked.add(user_id)

if __name__ == "__main__":
    load_handled_users()
    client.start()
    # loop.run_until_complete(handle_outputs())
    loop.create_task(handle_outputs())
    print("start")
    client.run_until_disconnected()
    print("disconnected")