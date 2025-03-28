from http.client import TOO_MANY_REQUESTS
from collections import Counter
from time import sleep
from pytz import UTC

from src.static_data import REQUEST_SOURCE
from src.messages import (
    PRIVATE_OUTPUT_MESSAGE,
    RESULT_TWEET_TEXTS
)
from src.exceptions import (
    PrivateAccountException,
    NoTweetUserException,
    RateLimitException
)

import requests
import datetime
import logging
import tweepy
import twitter
import random
import json
import http
import time
import os

from decouple import config


SHORT_VERSION_OUTPUT = config("SHORT_VERSION_OUTPUT", default=False, cast=bool)

if SHORT_VERSION_OUTPUT: FETCH_LIKES_COUNT = 1000
else: FETCH_LIKES_COUNT = 3000
DOUBLE_QUOTE_CHAR = "\""
LIKES_PER_EACH_REQUEST = 100

NUM_OF_LOOKED_UP_TWEETS = 200
TWEET_LIKE_TRESHOLD = 300
NUM_OF_RETRIES = 5


class Twitter():
    DEFAULT_CONFIG_FILE_PATH = "config/twitter.json"
    BOT_CONFIG_FILE_PATH = "config/twitter_bot.json"
    BACKUP_DEFAULT_CONFIG_FILE_PATH = "config/twitter_backup.json"

    def __init__(self) -> None:
        self.bot_cookies, self.bot_headers = self.load_twitter_config(Twitter.BOT_CONFIG_FILE_PATH)

        config_file_path = config("CONFIG_FILE_PATH", default=Twitter.DEFAULT_CONFIG_FILE_PATH)

        if not config_file_path:
            logging.error("Config file path not set")
            raise Exception("Config file path not set")
        if not os.path.exists(config_file_path):
            logging.error(f"{config_file_path} does not exists")
            raise Exception("Config file not found")

        logging.info(f"Loading {config_file_path} config")
        self.cookies, self.headers = self.load_twitter_config(config_file_path)

        # Check config
        self.check_twitter_account_is_ok()

        CONSUMER_KEY = config("CONSUMER_KEY")
        CONSUMER_SECRET = config("CONSUMER_SECRET")
        ACCESS_TOKEN = config("ACCESS_TOKEN")
        ACCESS_TOKEN_SECRET = config("ACCESS_TOKEN_SECRET")

        self.auth_media = tweepy.OAuthHandler(
            CONSUMER_KEY,
            CONSUMER_SECRET
        )   
        self.auth_media.set_access_token(
            ACCESS_TOKEN,
            ACCESS_TOKEN_SECRET
        )
        self.api = tweepy.API(self.auth_media)

        self.client = tweepy.Client(
            consumer_key=CONSUMER_KEY,
            consumer_secret=CONSUMER_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET
        )


    def get_replied_users(self, tweet_id: int, tweet_author_username: str = None) -> list:
        repliers_with_tweet_id = {}
        # if tweet_author_username: repliers.add(tweet_author_username)
        cursor = None

        while True:
            tweet = self.get_tweet_info_by_id(tweet_id, cursor)
            entries = tweet.get("data", {}).get("threaded_conversation_with_injections_v2", {}).get("instructions")[0].get("entries", [])
            for entry in entries[:-1]:
                if entry.get("content", {}).get("items"):
                    for _item in entry.get("content", {}).get("items", []):
                        screen_name = _item.get("item", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {}).get("core", {}).get("user_results", {}).get("result", {}).get("legacy", {}).get("screen_name")
                        if screen_name and not repliers_with_tweet_id.get(screen_name):
                            repliers_with_tweet_id[screen_name] = [
                                screen_name,
                                _item.get("item", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {}).get("rest_id"),
                                REQUEST_SOURCE.CACHE.value
                            ]
                else:
                    screen_name = entry.get("content", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {}).get("core", {}).get("user_results", {}).get("result", {}).get("legacy", {}).get("screen_name")
                    if screen_name and not repliers_with_tweet_id.get(screen_name):
                        repliers_with_tweet_id[screen_name] = [
                            screen_name,
                            entry.get("content", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {}).get("rest_id"),
                            REQUEST_SOURCE.CACHE.value
                        ]
                    
            if entries[-1] and entries[-1].get("content", {}).get("itemContent", {}).get("cursorType") == "Bottom":
                cursor = entries[-1].get("content", {}).get("itemContent", {}).get("value")
            else: break

        return repliers_with_tweet_id

    def dump_json(self, filename: str, content: dict):
        import json
        with open(filename, "w") as f:
            json.dump(content, f, indent=4)

    def check_user_is_private_by_screen_name(self, username: str) -> bool:
        user = self.get_full_user_info_by_screen_name(username)
        return bool(user.get("data", {}).get("user", {}).get("result", {}).get("legacy", {}).get("protected", False))

    def get_full_user_info_by_screen_name(self, username: str) -> dict:
        params = {
            'variables': f'{{"screen_name":"{username}","withSafetyModeUserFields":true}}',
            'features': '{"hidden_profile_likes_enabled":false,"hidden_profile_subscriptions_enabled":false,"responsive_web_graphql_exclude_directive_enabled":false,"verified_phone_label_enabled":false,"subscriptions_verification_info_is_identity_verified_enabled":false,"subscriptions_verification_info_verified_since_enabled":false,"highlights_tweets_tab_ui_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":false,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"responsive_web_graphql_timeline_navigation_enabled":false}',
            'fieldToggles': '{"withAuxiliaryUserLabels":false}',
        }

        response = requests.get(
            'https://twitter.com/i/api/graphql/G3KGOASz96M-Qu0nwmGXNg/UserByScreenName',
            params=params,
            cookies=self.cookies,
            headers=self.headers
        )

        if response.status_code != http.HTTPStatus.OK:
            raise Exception("Request failed to get user id with status code: " + str(response.status_code))
        
        return response.json()

    def get_user_id_by_username(self, username: str) -> str:
        params = {
            'variables': f'{{"screen_name":"{username}","withSafetyModeUserFields":true}}',
            'features': '{"hidden_profile_likes_enabled":false,"hidden_profile_subscriptions_enabled":false,"responsive_web_graphql_exclude_directive_enabled":false,"verified_phone_label_enabled":false,"subscriptions_verification_info_is_identity_verified_enabled":false,"subscriptions_verification_info_verified_since_enabled":false,"highlights_tweets_tab_ui_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":false,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"responsive_web_graphql_timeline_navigation_enabled":false}',
            'fieldToggles': '{"withAuxiliaryUserLabels":false}',
        }

        response = requests.get(
            'https://twitter.com/i/api/graphql/G3KGOASz96M-Qu0nwmGXNg/UserByScreenName',
            params=params,
            cookies=self.cookies,
            headers=self.headers
        )

        if response.status_code != http.HTTPStatus.OK:
            raise Exception("Request failed to get user id with status code: " + str(response.status_code))
        
        user_id = response.json().get("data", {}).get("user", {}).get("result", {}).get("rest_id")
        if not user_id:
            raise Exception("User id not found")

        return user_id

    def get_user_name_by_username(self, username: str) -> str:
        # Old
        response = requests.get(f"https://api.twitter.com/2/users/by/username/{username}", headers=self.headers)
        return response.json().get('data', {}).get('name')

    def get_user_profile_image(self, username: str=None):
        # Old
        response = requests.get(f"https://api.twitter.com/1.1/users/show.json?screen_name={username}", headers=self.headers)
        return response.json().get('profile_image_url')

    def get_tweet_author_username(self, tweet_id: str) -> str:
        # Old
        return self.tweepy_api.get_status(tweet_id).user.screen_name

    def get_user_likes(self, user_id, username: str = None) -> dict:
        """
        Output:
        {
            screen_name: {
                name: ,
                profile_image_url: ,
                count:        
            },
        }
        """
        liked_users = {}
        total_likes_count = 0
        fetched_likes_count = 0
        cursor = None
        while True:
            params = {
                'variables': f"{{\"userId\":\"{user_id}\"{f',{DOUBLE_QUOTE_CHAR}cursor{DOUBLE_QUOTE_CHAR}:' + cursor if cursor else ''},\"count\":{LIKES_PER_EACH_REQUEST},\"includePromotedContent\":false,\"withClientEventToken\":false,\"withBirdwatchNotes\":false,\"withVoice\":true,\"withV2Timeline\":true}}",
                'features': '{"responsive_web_graphql_exclude_directive_enabled":false,"verified_phone_label_enabled":false,"responsive_web_home_pinned_timelines_enabled":true,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"c9s_tweet_anatomy_moderator_badge_enabled":true,"tweetypie_unmention_optimization_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":false,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":false,"tweet_awards_web_tipping_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_media_download_video_enabled":false,"responsive_web_enhance_cards_enabled":false}',
            }

            for i in range(NUM_OF_RETRIES):
                response = requests.get(
                    'https://twitter.com/i/api/graphql/QcxQeD_5XNaZ_GZpixExZQ/Likes',
                    params=params,
                    cookies=self.cookies,
                    headers=self.headers
                )
                if response.status_code != http.HTTPStatus.OK:
                    logging.error(f"Request failed to get user likes with status code: {str(response.status_code)}")
                    if i != NUM_OF_RETRIES - 1:
                        sleep((i + 3) * 60)
                        continue
                    raise RateLimitException()

            # User info in each entry:
            # entry.get("content").get("itemContent").get("tweet_results").get("result").get("core").get("user_results").get("result").get("legacy")
            iteration_likes = response.json().get("data", {}).get("user", {}).get("result", {}).get("timeline_v2", {}).get("timeline", {}).get("instructions", [{}])[0].get("entries", [])
            fetched_likes_count += len(iteration_likes)
            if not iteration_likes:
                logging.info(f"No entry found, iteration_likes is empty")
                return liked_users, total_likes_count

            for like in iteration_likes[:-2]:
                total_likes_count += 1
                user = self.get_liked_tweet_author_user(like)
                if not user:
                    logging.error(f"Something is wrong with this tweet {like}")
                    continue
                liked_users[user.get("screen_name")] = {
                    "name": user.get("name"),
                    "profile_image_url": self.fix_image_address(user.get("profile_image_url_https")),
                    "count": liked_users.get(user.get("screen_name"), {"count": 0}).get("count", 0) + 1,
                    "screen_name": user.get("screen_name")
                }

            logging.debug(f"Fetched likes count: {fetched_likes_count}")
            if fetched_likes_count >= FETCH_LIKES_COUNT: break
            
            if len(iteration_likes) < 3:
                # This user probably has no any other like in his account
                break
            last_tweet_id = iteration_likes[-3].get("content", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {}).get("rest_id")
            try:
                last_tweet_date = self.get_tweet_creattion_date_by_id(last_tweet_id)
                logging.debug(f"Last tweet date: {last_tweet_date}")
                if last_tweet_date < datetime.datetime.now().astimezone(UTC) - datetime.timedelta(days=356):
                    break
            except Exception as e:
                logging.error(f"Error in getting tweet date {e}")

            if iteration_likes[-1].get("content", {}).get("cursorType") == "Bottom":
                cursor = f'"{iteration_likes[-1].get("content", {}).get("value")}"'
                sleep(5)
            else:
                break

        return liked_users, total_likes_count


    def get_tweet_info_by_id(self, tweet_id: str, cursor: str = None):
        params = {
            'variables': f"{{\"focalTweetId\":\"{tweet_id}\"{f',{DOUBLE_QUOTE_CHAR}cursor{DOUBLE_QUOTE_CHAR}:' + f'{DOUBLE_QUOTE_CHAR}{cursor}{DOUBLE_QUOTE_CHAR}' if cursor else ''},\"referrer\":\"tweet\",\"with_rux_injections\":false,\"includePromotedContent\":true,\"withCommunity\":true,\"withQuickPromoteEligibilityTweetFields\":true,\"withBirdwatchNotes\":true,\"withVoice\":true,\"withV2Timeline\":true}}",
            'features': '{"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"c9s_tweet_anatomy_moderator_badge_enabled":true,"tweetypie_unmention_optimization_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"rweb_video_timestamps_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_enhance_cards_enabled":false}',
            'fieldToggles': '{"withArticleRichContentState":true}',
        }

        response = requests.get(
            'https://twitter.com/i/api/graphql/89OGj-X6Vddr9EbuwIEmgg/TweetDetail',
            params=params,
            cookies=self.cookies,
            headers=self.headers
        )

        return response.json()

    def get_tweet_creattion_date_by_id(self, tweet_id: str) -> datetime:
        tweet = self.get_tweet_info_by_id(tweet_id)
        entries = tweet.get("data", {}).get("threaded_conversation_with_injections_v2", {}).get("instructions", {})[0].get("entries", {})
        for entry in entries:
            if entry.get("content", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {}).get("rest_id") == tweet_id:
                date_str = entry.get("content", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {}).get("legacy", {}).get("created_at", {})
                break
        else: raise Exception("Tweet not found in the entries")
        return datetime.datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y").replace(tzinfo=UTC) 

    def convert_tweet_created_at_to_datetiem(self, created_at: str) -> datetime:
        return datetime.datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y").replace(tzinfo=UTC)

    def get_user_by_screen_name(self, screen_name: str) -> dict:
        params = {
            'include_ext_is_blue_verified': '1',
            'include_ext_verified_type': '1',
            'include_ext_profile_image_shape': '1',
            'q': f'{screen_name}',
            'src': 'search_box',
            'result_type': 'events,users,topics,lists',
        }

        response = requests.get(
            'https://twitter.com/i/api/1.1/search/typeahead.json',
            params=params,
            cookies=self.cookies,
            headers=self.headers
        )

        if response.status_code != http.HTTPStatus.OK:
            raise Exception("Request failed to search for user by screen name with status code: " + str(response.status_code))
        
        return response.json().get("users", [])[0]

    def get_liked_tweet_author_user(self, liked_tweet: dict) -> dict:
        if liked_tweet.get("content").get("itemContent").get("tweet_results", {}).get("result", {}).get("__typename") == "TweetWithVisibilityResults":
            tweet_info = liked_tweet.get("content").get("itemContent").get("tweet_results", {}).get("result", {}).get("tweet", {}).get("core", {})
        else:
            tweet_info = liked_tweet.get("content").get("itemContent").get("tweet_results", {}).get("result", {}).get("core", {})
        return tweet_info.get("user_results", {}).get("result", {}).get("legacy", {})

    def get_user_tweets(self, user_id: str, tweet_time_days_treshold: int = None, ignore_mentions: bool = True) -> set:
       # This function just gets the tweets and mentions and replies are not included
        """
            Output: {tweet_id, ...}
        """
        tweet_ids = set()
        cursor = None
        logging.info(f"Getting tweets of {user_id}")
        while True:
            params = {
                'variables': f"{{\"userId\":\"{user_id}\"{f',{DOUBLE_QUOTE_CHAR}cursor{DOUBLE_QUOTE_CHAR}:' + f'{DOUBLE_QUOTE_CHAR}{cursor}{DOUBLE_QUOTE_CHAR}' if cursor else ''},\"count\":100,\"includePromotedContent\":true,\"withQuickPromoteEligibilityTweetFields\":true,\"withVoice\":true,\"withV2Timeline\":true}}",
                'features': '{"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"c9s_tweet_anatomy_moderator_badge_enabled":true,"tweetypie_unmention_optimization_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"rweb_video_timestamps_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_enhance_cards_enabled":false}'
            }

            response = requests.get(
                'https://twitter.com/i/api/graphql/WwS-a6hAhqAAe-gItelmHA/UserTweets',
                params=params,
                cookies=self.cookies,
                headers=self.headers,
            )

            if response.status_code != http.HTTPStatus.OK:
                raise Exception("Request failed to get user tweets with status code: " + str(response.status_code))

            entries = response.json().get("data", {}).get("user", {}).get("result", {}).get("timeline_v2", {}).get("timeline", {}).get("instructions", [{"entries": []}])[-1].get("entries", [])
            for entry in entries:
                # A thread of tweets are shown together. These are the profile-conversation type.
                # In this entries, there is multiple tweets in "items".
                # Below if statement, handles these type of entries.
                if "profile-conversation" in entry.get("entryId"):
                    tweets_data = [
                        _tweet.get("item", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {})
                        for _tweet in entry.get("content").get("items")
                    ]
                elif "tweet" in entry.get("entryId"):
                    # These are normal tweets
                    tweets_data = [entry.get("content", {}).get("itemContent", {}).get("tweet_results").get("result", {})]

                for tweet_data in tweets_data:
                    legacy = tweet_data.get("legacy") if tweet_data.get("legacy") else tweet_data.get("tweet").get("legacy")
                    if ( tweet_data.get("tweet") and tweet_data.get("legacy") ) or \
                        legacy.get("retweeted_status_result") or \
                        not legacy.get("favorite_count") \
                        or legacy.get("favorite_count") > TWEET_LIKE_TRESHOLD:
                        # Tweet has no faves or it's a retweet or has more than TWEET_LIKE_TRESHOLD likes
                        continue
                    if tweet_time_days_treshold and \
                        self.convert_tweet_created_at_to_datetiem(legacy.get("created_at")) \
                        < datetime.datetime.now().astimezone(UTC) - datetime.timedelta(days=tweet_time_days_treshold):
                        return tweet_ids
                    tweet_ids.add(tweet_data.get("rest_id", tweet_data.get("tweet", {}).get("rest_id")))

            if not entries or\
                len(entries) == 2:
                # If entries are empty or it just has cursor-bottom and cursor-top
                break

            cursor = entries[-1].get("content", {}).get("value")
            if not cursor: break

            logging.info(f"Fetched {len(tweet_ids)} tweets for {user_id}")
            if len(tweet_ids) >= NUM_OF_LOOKED_UP_TWEETS: break
            sleep(30)

        return tweet_ids

    def get_tweet_liking_users(self, tweet_id: str) -> list:
        """
        Output: {
            screen_name: {
                name: ,
                profile_image_url: ,
                count:
        }
        """
        liked_users = {}
        cursor = None
        # If cursor is not None, but it's the same as previous cursor, break the loop
        previous_cursor = None
        while True:
            params = {
                'variables': f"{{\"tweetId\":\"{tweet_id}\"{f',{DOUBLE_QUOTE_CHAR}cursor{DOUBLE_QUOTE_CHAR}:' + f'{DOUBLE_QUOTE_CHAR}{cursor}{DOUBLE_QUOTE_CHAR}' if cursor else ''},\"count\":100,\"includePromotedContent\":true}}",
                'features': '{"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":true,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"c9s_tweet_anatomy_moderator_badge_enabled":true,"tweetypie_unmention_optimization_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"rweb_video_timestamps_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_enhance_cards_enabled":false}',
            }

            response = requests.get(
                'https://twitter.com/i/api/graphql/-di098ULkVEOqtzrQGHAVg/Favoriters',
                params=params,
                cookies=self.cookies,
                headers=self.headers,
            )

            if response.status_code != http.HTTPStatus.OK:
                raise Exception("Request failed to get tweet likes with status code: " + str(response.status_code))
            
            if not response.json().get("data", {}).get("favoriters_timeline", {}).get("timeline", {}).get("instructions", [{"entries": []}]):
                # No like found
                break
            entries = response.json().get("data", {}).get("favoriters_timeline", {}).get("timeline", {}).get("instructions", [{"entries": []}])[-1].get("entries", [])
            for entry in entries:
                if not "user" in entry.get("entryId"):
                    continue
                user = entry.get("content", {}).get("itemContent", {}).get("user_results", {}).get("result", {})
                if not user: # In some cases, user_results is empty
                    continue
                liked_users[user.get("legacy").get("screen_name")] = {
                    "name": user.get("legacy").get("name"),
                    "profile_image_url": self.fix_image_address(user.get("legacy").get("profile_image_url_https")),
                }

            if not entries: break

            if entries[-1].get("content", {}).get("cursorType") == "Bottom":
                previous_cursor = cursor
                cursor = entries[-1].get("content", {}).get("value")
            if not cursor or \
                cursor == previous_cursor:
                break
            sleep(5)

        return liked_users

    def get_user_most_liking_users(self, username: str, number_of_results: int = 12) -> tuple:
        user_id = self.get_user_id_by_username(username)
        tweets = list(self.get_user_tweets(
            user_id=user_id,
            tweet_time_days_treshold=365,
            ignore_mentions=True
        ))

        if not tweets:
            raise NoTweetUserException

        liking_users_data = {}
        num_tweets = len(tweets)
        counter = total_likes = 0
        for tweet_id in tweets:
            logging.info(f"{counter}/{len(tweets)} has been processed {tweet_id} {username}")
            while True:
                liking_users = dict()
                try:
                    liking_users = self.get_tweet_liking_users(tweet_id)
                    break
                except AttributeError as e:
                    logging.error(e)
                    logging.error("Tweet id: " + str(tweet_id) + ", Moving to the next tweet")
                    sleep(60)
                    break
                except Exception as e:
                    logging.error(e)
                    sleep_time = 600
                    logging.info(f"Waiting {sleep_time} sconds")
                    sleep(sleep_time)
                    logging.info("Trying again")

            counter += 1
            logging.debug(f"Tweet {tweet_id} has {len(liking_users)} likes")
            total_likes += len(liking_users)
            for screen_name in liking_users:
                liking_users_data[screen_name] = {
                    'name': liking_users[screen_name].get("name"),
                    "profile_image_url": liking_users[screen_name].get("profile_image_url"),
                    "count": liking_users_data.get(screen_name, {"count": 0}).get("count", 0) + 1
                }
            sleep(30)

        most_liking_users = dict(sorted(liking_users_data.items(), key=lambda x: x[1].get("count"), reverse=True)[:number_of_results])
        for _username in most_liking_users.keys():
            most_liking_users[_username]["count"] /= num_tweets * 0.01

        return most_liking_users, total_likes / num_tweets

    def get_users_by_user_id_list(self, user_ids: list) -> str:
        # Old
        return self.tweepy_api.lookup_users(user_id=user_ids, include_entities=False)

    def send_result_in_direct(self, conversation_id: str, output_address: str, ):
        message = f"{self.generate_result_tweet_text}:\n{output_address}\n{PRIVATE_OUTPUT_MESSAGE}"
        self.send_direct_message(conversation_id, f"نتیجه شما: {output_address}")

    def send_direct_message(self, conversation_id: str, message_text: str = None, media_path: str = None):
        # Not working when media is added, Gives 403 (Invalid media)

        # Upload media
        # if media_path:
        #     uploaded_media = self.upload_media(media_path)
        # elif not message_text:
        #     raise Exception("Nothing to send")

        params = {
            'ext': 'mediaColor,altText,mediaStats,highlightedLabel,voiceInfo,birdwatchPivot,superFollowMetadata,unmentionInfo,editControl',
            'include_ext_alt_text': 'true',
            'include_ext_limited_action_results': 'true',
            'include_reply_count': '1',
            'tweet_mode': 'extended',
            'include_ext_views': 'true',
            'include_groups': 'true',
            'include_inbox_timelines': 'true',
            'include_ext_media_color': 'true',
            'supports_reactions': 'true',
        }

        json_data = {
            'conversation_id': conversation_id,
            # 'media_id': uploaded_media.media_id, # Uncomment for sending media
            'recipient_ids': False,
            'request_id': 'b571c5a0-d999-11ee-a2c8-c1da67973d72',
            'text': message_text,
            'cards_platform': 'Web-12',
            'include_cards': 1,
            'include_quote_count': True,
            'dm_users': False,
        }

        response = requests.post(
            'https://twitter.com/i/api/1.1/dm/new2.json',
            params=params,
            cookies=self.cookies,
            headers=self.headers,
            json=json_data,
        )

        if response.status_code != http.HTTPStatus.OK:
            raise Exception(f"Failed to sent result to {conversation_id}")

    def fix_image_address(self, image_link) -> str:
        # remove _normal.jpg from image like
        return image_link.replace("_normal.jpg", ".jpg")

    def get_direct_api(self):
        # Old
        # if token file exists, load tokens from it
        tokens_file_path = "direct_tokens.txt"
        tokens = None
        if os.path.exists(tokens_file_path):
            with open(tokens_file_path, "r") as f:
                tokens = f.read()
        access_token, access_token_secret = tokens.split()

        auth = tweepy.OAuth1UserHandler(
            config("APP_API_KEY"), config("APP_API_KEY_SECRET"),
            access_token, access_token_secret
        )
        self.direct_api = tweepy.API(auth)

    def save_bot_tokens(self, access_token: str, access_token_secret: str):
        # Old
        tokens_file_path = "bot_tokens.txt"
        with open(tokens_file_path, "w") as f:
            f.write(f"{access_token} {access_token_secret}")

    def get_user_most_liked_users(self, username: str, number_of_results: int = 12) -> dict:
        """
        Output:
        (
            {screen_name: {
                name: ,
                profile_image_url: ,
                count:        
            }},
            total_likes_count: int
        )
        """
        if self.check_user_is_private_by_screen_name(username):
            raise PrivateAccountException(f"{username} is a private account")
        user_id = self.get_user_id_by_username(username)
        liked_users, total_likes_count = self.get_user_likes(user_id)
        if not liked_users and not total_likes_count:
            raise Exception("This user has no likes")
        liked_users = dict(Counter(liked_users))

        most_liked_users = dict(
            sorted(liked_users.items(), key=lambda x: x[-1].get("count", 0), reverse=True)[:number_of_results]
        )

        return most_liked_users, total_likes_count

    def tweet_result(self, image_path: str, tweet_id: str):  
        try:
            uploaded_media = self.api.media_upload(image_path)

            self.client.create_tweet(
                text=self.generate_result_tweet_text(),
                media_ids=[uploaded_media.media_id],
                in_reply_to_tweet_id=tweet_id
            )
        except Exception as e:
            logging.error(f"Something went wront when tweeting results: {e}")

    def send_output_in_reply(self, image_path: str, tweet_id: str):
        uploaded_media = self.api.media_upload(image_path)

        json_data = {
            'variables': {
                'tweet_text': self.generate_result_tweet_text(),
                'reply': {
                    'in_reply_to_tweet_id': str(tweet_id),
                    'exclude_reply_user_ids': [],
                },
                'batch_compose': 'BatchSubsequent',
                'dark_request': False,
                'media': {
                    'media_entities': [
                        {
                            'media_id': str(uploaded_media.media_id),
                            'tagged_users': [],
                        },
                    ],
                    'possibly_sensitive': False,
                },
                'semantic_annotation_ids': [],
            },
            'features': {
                'c9s_tweet_anatomy_moderator_badge_enabled': True,
                'tweetypie_unmention_optimization_enabled': True,
                'responsive_web_edit_tweet_api_enabled': True,
                'graphql_is_translatable_rweb_tweet_is_translatable_enabled': True,
                'view_counts_everywhere_api_enabled': True,
                'longform_notetweets_consumption_enabled': True,
                'responsive_web_twitter_article_tweet_consumption_enabled': True,
                'tweet_awards_web_tipping_enabled': False,
                'longform_notetweets_rich_text_read_enabled': True,
                'longform_notetweets_inline_media_enabled': True,
                'rweb_video_timestamps_enabled': True,
                'responsive_web_graphql_exclude_directive_enabled': True,
                'verified_phone_label_enabled': False,
                'freedom_of_speech_not_reach_fetch_enabled': True,
                'standardized_nudges_misinfo': True,
                'tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled': True,
                'responsive_web_graphql_skip_user_profile_image_extensions_enabled': False,
                'responsive_web_graphql_timeline_navigation_enabled': True,
                'responsive_web_enhance_cards_enabled': False,
            },
            'queryId': 'sgqau0P5BUJPMU_lgjpd_w',
        }

        response = requests.post(
            'https://twitter.com/i/api/graphql/sgqau0P5BUJPMU_lgjpd_w/CreateTweet',
            cookies=self.bot_cookies,
            headers=self.bot_headers,
            json=json_data,
        )

        if response.status_code != http.HTTPStatus.OK:
            return False

    def get_inbox_initial_state(self) -> list:
        params = {
            'nsfw_filtering_enabled': 'false',
            'include_profile_interstitial_type': '1',
            'include_blocking': '1',
            'include_blocked_by': '1',
            'include_followed_by': '1',
            'include_want_retweets': '1',
            'include_mute_edge': '1',
            'include_can_dm': '1',
            'include_can_media_tag': '1',
            'include_ext_is_blue_verified': '1',
            'include_ext_verified_type': '1',
            'include_ext_profile_image_shape': '1',
            'skip_status': '1',
            'dm_secret_conversations_enabled': 'false',
            'krs_registration_enabled': 'true',
            'cards_platform': 'Web-12',
            'include_cards': '1',
            'include_ext_alt_text': 'true',
            'include_ext_limited_action_results': 'true',
            'include_quote_count': 'true',
            'include_reply_count': '1',
            'tweet_mode': 'extended',
            'include_ext_views': 'true',
            'dm_users': 'true',
            'include_groups': 'true',
            'include_inbox_timelines': 'true',
            'include_ext_media_color': 'true',
            'supports_reactions': 'true',
            'include_ext_edit_control': 'true',
            'include_ext_business_affiliations_label': 'true',
            'ext': 'mediaColor,altText,mediaStats,highlightedLabel,voiceInfo,birdwatchPivot,superFollowMetadata,unmentionInfo,editControl',
        }

        response = requests.get(
            'https://twitter.com/i/api/1.1/dm/inbox_initial_state.json',
            params=params,
            cookies=self.cookies,
            headers=self.headers
        )

        return response.json().get("inbox_initial_state").get("inbox_timelines").get("trusted").get("min_entry_id")

    def iterate_over_user_inbox_conversations(self, max_id: str, direct_message_time_treshold: datetime.datetime) -> list:
        # This functions finds the users that requested in direct messages
        # It just gives the users that send a direct message after direct_message_time_treshold
        """
        Outpu: {
            screen_name: {
                conversation_id: str
            }
        }
        """
        requesting_users = {}
        while True:
            params = {
                'max_id': f'{max_id}',
                'nsfw_filtering_enabled': 'false',
                'include_profile_interstitial_type': '1',
                'include_blocking': '1',
                'include_blocked_by': '1',
                'include_followed_by': '1',
                'include_want_retweets': '1',
                'include_mute_edge': '1',
                'include_can_dm': '1',
                'include_can_media_tag': '1',
                'include_ext_is_blue_verified': '1',
                'include_ext_verified_type': '1',
                'include_ext_profile_image_shape': '1',
                'skip_status': '1',
                'dm_secret_conversations_enabled': 'false',
                'krs_registration_enabled': 'true',
                'cards_platform': 'Web-12',
                'include_cards': '1',
                'include_ext_alt_text': 'true',
                'include_ext_limited_action_results': 'true',
                'include_quote_count': 'true',
                'include_reply_count': '1',
                'tweet_mode': 'extended',
                'include_ext_views': 'true',
                'dm_users': 'false',
                'include_groups': 'true',
                'include_inbox_timelines': 'true',
                'include_ext_media_color': 'true',
                'supports_reactions': 'true',
                'include_ext_edit_control': 'true',
                'ext': 'mediaColor,altText,businessAffiliationsLabel,mediaStats,highlightedLabel,voiceInfo,birdwatchPivot,superFollowMetadata,unmentionInfo,editControl',
            }

            response = requests.get(
                'https://twitter.com/i/api/1.1/dm/inbox_timeline/trusted.json',
                params=params,
                cookies=self.cookies,
                headers=self.headers,
            )

            if response.status_code != http.HTTPStatus.OK:
                raise Exception("Request failed to get directs with status code: " + str(response.status_code))

            max_id = response.json().get("inbox_timeline", {}).get("min_entry_id")
            if not max_id: break

            users = response.json().get("inbox_timeline", {}).get("users", [])
            for conversation in response.json().get("inbox_timeline", {}).get("conversations", {}):
                conversation_timestamp = response.json().get("inbox_timeline", {}).get("conversations", []).get(conversation).get("sort_timestamp")
                if direct_message_time_treshold and \
                    conversation_timestamp and self.epoch_time_convertor(conversation_timestamp) > direct_message_time_treshold:
                    for participant in response.json().get("inbox_timeline", {}).get("conversations", []).get(conversation).get("participants"):
                        screen_name = users.get(participant.get("user_id"), {}).get("screen_name")
                        if not requesting_users.get(screen_name):
                            requesting_users[screen_name] = {
                                "conversation_id": response.json().get("inbox_timeline", {}).get("conversations", {}).get(conversation).get("conversation_id")
                            }

            # Same thing with iterating over every message
            # This solution does not get conversations that are just message from the account owner
            # for i in response.json().get("inbox_timeline", {}).get("entries", []):
            #     msg_time = i.get("message", {}).get("message_data", {}).get("time")
            #     if msg_time and self.epoch_time_convertor(msg_time) > direct_message_time_treshold:
            #         screen_name = users.get(i.get("message", {}).get("message_data", {}).get("sender_id"), {}).get("screen_name")
            #         usernames[screen_name] = {
            #             "screen_name": screen_name,
            #             "message_id": i.get("message", {}).get("id")
            #         }

        return requesting_users

    def get_direct_usernames(self, direct_message_time_treshold: datetime.datetime = datetime.datetime(2023, 1, 1)) -> list:
        entry_id = self.get_inbox_initial_state()
        return self.iterate_over_user_inbox_conversations(entry_id, direct_message_time_treshold)

    def upload_media(self, media_path: str):
        return self.api.media_upload(media_path)

    def get_user_directs_sender_ids(self) -> dict:
        # Old
        sender_ids = {}
        # Get messages with cursor
        # msgs = self.bot_api.get_direct_messages(count=100)
        msg_pages = tweepy.Cursor(self.bot_api.get_direct_messages).pages(5)
        try:
            for page in msg_pages:
                for msg in page:
                    time.sleep(0.1)
                    sender_ids[msg.message_create['sender_id']] = msg.id
        except Exception as e:
            logging.error(e)
            logging.info("Wait in get directs")
            time.sleep(5 * 60)
        return sender_ids

    def get_user_followings(self, username: str = None, user_id: str = None) -> list:
        """
        Output: {
            "screen_name": str,
            "name": str
            "followed_by": bool (Did this user follwed me?)
        }
        """
        if username and not user_id:
            user_id = self.get_user_id_by_username(username)
        if not user_id:
            raise Exception("user_id is required")
        
        followings = []

        cursor = None
        while True:
            params = {
                'variables': f"{{\"userId\":\"{user_id}\"{f',{DOUBLE_QUOTE_CHAR}cursor{DOUBLE_QUOTE_CHAR}:' + f'{DOUBLE_QUOTE_CHAR}{cursor}{DOUBLE_QUOTE_CHAR}' if cursor else ''},\"count\":100,\"includePromotedContent\":false}}",
                'features': '{"responsive_web_graphql_exclude_directive_enabled":true,"verified_phone_label_enabled":false,"creator_subscriptions_tweet_preview_api_enabled":true,"responsive_web_graphql_timeline_navigation_enabled":false,"responsive_web_graphql_skip_user_profile_image_extensions_enabled":false,"c9s_tweet_anatomy_moderator_badge_enabled":true,"tweetypie_unmention_optimization_enabled":true,"responsive_web_edit_tweet_api_enabled":true,"graphql_is_translatable_rweb_tweet_is_translatable_enabled":true,"view_counts_everywhere_api_enabled":true,"longform_notetweets_consumption_enabled":true,"responsive_web_twitter_article_tweet_consumption_enabled":true,"tweet_awards_web_tipping_enabled":false,"freedom_of_speech_not_reach_fetch_enabled":true,"standardized_nudges_misinfo":true,"tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled":true,"rweb_video_timestamps_enabled":true,"longform_notetweets_rich_text_read_enabled":true,"longform_notetweets_inline_media_enabled":true,"responsive_web_enhance_cards_enabled":false}',
            }

            response = requests.get(
                'https://twitter.com/i/api/graphql/PiHWpObvX9tbClrUl6rL9g/Following',
                params=params,
                cookies=self.cookies,
                headers=self.headers,
            )

            if response.status_code != http.HTTPStatus.OK:
                raise Exception("Something went wrong")

            entries = response.json().get("data", {}).get("user", {}).get("result", {}).get("timeline", {}).get("timeline", {}).get("instructions", [{"entries": []}])[-1].get("entries", [])
            if not entries: break
            for entry in entries:
                legacy = entry.get("content", {}).get("itemContent", {}).get("user_results", {}).get("result", {}).get("legacy")
                if not legacy: continue
                followings.append({
                    "screen_name": legacy.get("screen_name", ""),
                    "name": legacy.get("name"),
                    "followed_by": bool(legacy.get("followed_by")), # Did he followed me?
                })

            logging.info(f"Loaded followings: {len(followings)}")
            cursor = entries[-2].get("content").get("value")
            if not cursor or cursor.split("|")[0] == "0": break
            sleep(5)

        return followings

    def check_twitter_account_is_ok(self) -> bool:
        pass
        # TODO: Raise different exceptions

    def load_twitter_config(self, path: str):
        if not os.path.exists(path):
            raise Exception(f"Config file not found at {path}")
        with open(path, "r") as f:
            config = json.load(f)
        
        return config.get("cookies"), config.get("headers")

    def check_username_exists(self, screen_name: str) -> bool:
        try:
            if not self.get_full_user_info_by_screen_name(screen_name).get("data").get("user").get("result").get("rest_id"):
                return False
        except Exception as e:
            return False
        return True

    def generate_result_tweet_text(self) -> str:
        # Choose random element of messages list
        return random.choice(RESULT_TWEET_TEXTS)

    def epoch_time_convertor(self, epoch_time: int) -> datetime:
        return datetime.datetime.fromtimestamp(int(epoch_time) // 1000)
    
    def move_image_to_folder(self, image_path: str, folder_path: str):
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        os.rename(image_path, os.path.join(folder_path, os.path.basename(image_path)))
