import requests
from telethon import TelegramClient, events
import urllib.request
from decouple import config
from http.client import TOO_MANY_REQUESTS
from time import sleep
from src.redis_handler import Redis
from src.db import DB
from src.utils import generate_result_tweet_text
from src.image_generator import check_output_image_is_present


import re
import logging
import asyncio

logging.basicConfig(level=logging.INFO)

loop = asyncio.get_event_loop()

REQUEST_LIMIT = 1

api_id = config("CLIENT_API_ID")
api_hash = config("CLIENT_API_HASH")
client = TelegramClient('anon_crush', api_id, api_hash)

handled_users_liking = set() # List of usersnames
handled_users_liked = set() # List of usernames

db_client = DB()
redis_client = Redis()

error_template = """
تو یه پیام، لینک صفحه‌ی profileت رو برام بفرست. یه چیزی مثل این لینک:
https://twitter.com/mh_bahmani
"""
request_accepted_msg = "✨ سلام، درخواستت رفت تو صف. به محض این که آماده بشه، برات می‌فرستمش😌"
already_got_your_request_msg = """
یا درخواستت ثبت شده و تو صفه و یا به لیمیت تعداد درخواست رسیدی.
"""
too_many_requests_msg = f"""
بیشتر از {REQUEST_LIMIT} درخواست رو نمی‌تونی بدی و به سقف تعداد درخواست‌هاست رسیدی. فعلا صبر کن تا این سقف رو بیشتر کنم و بتونی دوباره درخواست بدی"""

@client.on(events.NewMessage(pattern=r"/start"))
async def start_handler(event):
    user_id = event.original_update.message.peer_id.user_id
    await client.send_message(user_id, error_template)

@client.on(events.NewMessage())
async def username_handler(event):
    text = event.raw_text
    # print(text)
    user_id = event.original_update.message.peer_id.user_id
    # print(redis_client.get_user_request_count(str(user_id), "liked_users"))
    if redis_client.get_user_request_count(str(user_id), "liked_users") >= REQUEST_LIMIT:
        await client.send_message(user_id, too_many_requests_msg)
        return
    redis_client.increase_user_request_count(str(user_id), "liked_users")

    # fetch the part of the text that matchs with https://.*
    profile_url = re.findall(r'https://.*', text)
    if not profile_url:
        await client.send_message(user_id, error_template)
        return
    else: profile_url = profile_url[0]
    username = profile_url.strip().split("/")[-1]

    # in_progress_usernames = redis_client.get_all_progressing_events("liked_users")
    if user_id in handled_users_liked:
        await client.send_message(user_id, already_got_your_request_msg)
        return
    print("= Adding", username, "to queue liked_users, user_d", user_id)
    redis_client.add_event_to_queue([username, str(user_id), "b"], queue="liked_users")
    handled_users_liked.add(user_id)

    await client.send_message(user_id, request_accepted_msg, link_preview=False)
    # await client.disconnect()


async def send_output(user_id, image_path):
    await client.start()
    await client.send_message(user_id, generate_result_tweet_text(), link_preview=False, file=image_path)
    await client.disconnect()
    # async with TelegramClient('anon_crush-2', api_id, api_hash) as telegram_client:
    #     await telegram_client.send_message(user_id, generate_result_tweet_text(), link_preview=False, file=image_path)
    #     await telegram_client.disconnect()

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