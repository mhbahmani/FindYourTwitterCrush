from src.messages import RESULT_TWEET_TEXTS

import random


PRIVATE_OUTPUT_DOMAIN = "twitter-stats.mhbahmani.ir"

def generate_private_output_address(output_path) -> str:
    return f'{PRIVATE_OUTPUT_DOMAIN}/{output_path.split("/")[-1]}'

def generate_result_tweet_text() -> str:
    # Choose random element of messages list
    return random.choice(RESULT_TWEET_TEXTS)
