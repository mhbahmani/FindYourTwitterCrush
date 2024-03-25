from src.messages import RESULT_TWEET_TEXTS
from src.static_data import TWITTER_CONFIG_PATH_TO_NAME
from src.twitter_handler import Twitter

from decouple import config

import random


PRIVATE_OUTPUT_DOMAIN = "twitter-stats.mhbahmani.ir"

def generate_private_output_address(output_path) -> str:
    return f'{PRIVATE_OUTPUT_DOMAIN}/{output_path.split("/")[-1]}'

def generate_result_tweet_text() -> str:
    # Choose random element of messages list
    return random.choice(RESULT_TWEET_TEXTS)

def get_twitter_config_name(config_file_path: str = None) -> str:
    if not config_file_path:
        config_file_path = config("CONFIG_FILE_PATH", default=Twitter.DEFAULT_CONFIG_FILE_PATH)

    return \
        TWITTER_CONFIG_PATH_TO_NAME.get(config_file_path.strip(".").strip("/").split("/")[-1], "Not Found")