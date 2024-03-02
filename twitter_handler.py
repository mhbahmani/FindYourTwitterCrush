from http.client import TOO_MANY_REQUESTS
from collections import Counter
from enum import Enum
from time import sleep
from pytz import UTC

from messages import RESULT_TWEET_TEXTS

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


API_KEY = config("API_KEY2")
API_KEY_SECRET = config("API_KEY_SECRET2")

ACCESS_TOKEN=config("ACCESS_TOKEN2")
ACCESS_TOKEN_SECRET=config("ACCESS_TOKEN_SECRET2")

DOUBLE_QUOTE_CHAR = "\""
FETCH_LIKES_COUNT = 150
LIKES_PER_EACH_REQUEST = 100


class REQUEST_TYPE(Enum):
    DIRECT = "d"
    TWEET = "t"

class Twitter():
    CONFIG_FILE_PATH = "config/twitter.json"
    BOT_CONFIG_FILE_PATH = "config/twitter_bot.json"

    def __init__(self) -> None:
        self.cookies, self.headers = self.load_twitter_config(Twitter.CONFIG_FILE_PATH)
        self.bot_cookies, self.bot_headers = self.load_twitter_config(Twitter.BOT_CONFIG_FILE_PATH)

        CONSUMER_KEY = config("CONSUMER_KEY"),
        CONSUMER_SECRET = config("CONSUMER_SECRET"),
        ACCESS_TOKEN = config("ACCESS_TOKEN"),
        ACCESS_TOKEN_SECRET = config("ACCESS_TOKEN_SECRET")

        self.auth_media = tweepy.OAuthHandler(
            CONSUMER_KEY,
            CONSUMER_SECRET
        )   
        self.auth_media.set_access_token(
            ACCESS_TOKEN,
            ACCESS_TOKEN_SECRET
        )

        self.client = tweepy.Client(
            consumer_key=self.CONSUMER_KEY,
            consumer_secret=self.CONSUMER_SECRET,
            access_token=self.ACCESS_TOKEN,
            access_token_secret=self.ACCESS_TOKEN_SECRET
        )


    def get_replied_users(self, tweet_id: int, tweet_author_username: str = None) -> list:
        repliers = set()
        repliers_with_tweet_id = {}
        if tweet_author_username: repliers.add(tweet_author_username)
        cursor = None
        # self.dump_json("tweet.json ", tweet)

        while True:
            tweet = self.get_tweet_info_by_id(tweet_id, cursor)
            entries = tweet.get("data", {}).get("threaded_conversation_with_injections_v2", {}).get("instructions")[0].get("entries", [])
            for entry in entries[:-1]:
                if entry.get("content", {}).get("items", {}):
                    for _item in entry.get("content", {}).get("items", {}):
                        screen_name = _item.get("item", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {}).get("core", {}).get("user_results", {}).get("result", {}).get("legacy", {}).get("screen_name")
                        if not repliers_with_tweet_id.get(screen_name):
                            repliers_with_tweet_id[screen_name] = [
                                screen_name,
                                _item.get("item", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {}).get("rest_id"),
                                str(REQUEST_TYPE.TWEET)
                            ]
                else:
                    screen_name = entry.get("content", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {}).get("core", {}).get("user_results", {}).get("result", {}).get("legacy", {}).get("screen_name")
                    repliers_with_tweet_id[screen_name] = [
                        screen_name,
                        entry.get("content", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {}).get("rest_id"),
                        str(REQUEST_TYPE.TWEET)
                    ]
                    
            if entries[-1] and entries[-1].get("content", {}).get("itemContent", {}).get("cursorType") == "Bottom":
                cursor = entries[-1].get("content", {}).get("itemContent", {}).get("value")
            else: break

        return repliers

    def dump_json(self, filename: str, content: dict):
        import json
        with open(filename, "w") as f:
            json.dump(content, f, indent=4)

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
        Outpu:
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

            response = requests.get(
                'https://twitter.com/i/api/graphql/QcxQeD_5XNaZ_GZpixExZQ/Likes',
                params=params,
                cookies=self.cookies,
                headers=self.headers
            )

            if response.status_code != http.HTTPStatus.OK:
                raise Exception("Request failed to get user likes with status code: " + str(response.status_code))

            # User info in each entry:
            # entry.get("content").get("itemContent").get("tweet_results").get("result").get("core").get("user_results").get("result").get("legacy")
            iteration_likes = response.json().get("data", {}).get("user", {}).get("result", {}).get("timeline_v2").get("timeline").get("instructions")[0].get("entries", [])
            fetched_likes_count += len(iteration_likes)

            for like in iteration_likes[:-2]:
                total_likes_count += 1
                user = self.get_liked_tweet_author_user(like)
                if not user:
                    print(f"Something is wrong with this tweet {like}")
                    continue
                liked_users[user.get("screen_name")] = {
                    "name": user.get("name"),
                    "profile_image_url": self.fix_image_address(user.get("profile_image_url_https")),
                    "count": liked_users.get(user.get("screen_name"), {"count": 0}).get("count", 0) + 1,
                    "screen_name": user.get("screen_name")
                }

            print(fetched_likes_count)
            if fetched_likes_count >= FETCH_LIKES_COUNT: break
            
            last_tweet_id = iteration_likes[-3].get("content", {}).get("itemContent", {}).get("tweet_results", {}).get("result", {}).get("rest_id")
            try:
                last_tweet_date = self.get_tweet_creattion_date_by_id(last_tweet_id)
                print(last_tweet_date)
                if last_tweet_date < datetime.datetime.now().astimezone(UTC) - datetime.timedelta(days=356):
                    break
            except:
                print("Error in getting tweet date")

            if iteration_likes[-1].get("content", {}).get("cursorType") == "Bottom":
                cursor = f'"{iteration_likes[-1].get("content", {}).get("value")}"'
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
            headers=self.headers,
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

    def get_user_tweets(self, user_id: str) -> list:
        # Old
        """
            outputs: [{id: , text: }]
        """
        params = {
            'max_results': 100,
            'exclude': 'replies,retweets',
            'tweet.fields': 'created_at'
        }
        tweets = []
        while True:
            response = requests.get(f'https://api.twitter.com/2/users/{user_id}/tweets', headers=self.headers, params=params)
            if response.status_code == TOO_MANY_REQUESTS:
                logging.info("Wait in get_user_tweets")
                self.update_headers()
                time.sleep(2 * 60)
                logging.info("Retry in get_user_tweets")
                continue
            tweets += response.json().get('data', [])
            logging.info(f"tweets {len(tweets)}")
            next_token = response.json().get('meta', {}).get("next_token")
            if not next_token: break
            # Turn str date to datetime
            last_tweet_create_date = datetime.datetime.strptime(tweets[-1].get('created_at'), "%Y-%m-%dT%H:%M:%S.%fZ")
            if tweets and last_tweet_create_date < datetime.datetime.now() - datetime.timedelta(days=365) \
            or len(tweets) >= 299: break
            params['pagination_token'] = next_token
            time.sleep(5)
        return tweets

    def get_tweet_likes(self, tweet_id: str) -> list:
        # Old
        # logging.info(tweet_id)
        params = {
            'max_results': 100,
            'user.fields': 'name,profile_image_url,username'
        }
        response = requests.get(f"https://api.twitter.com/2/tweets/{tweet_id}/liking_users", headers=self.headers, params=params)
        if response.status_code == TOO_MANY_REQUESTS:
            raise Exception("Too many requests")
        # if errors := response.json().get('errors'):
        #     return errors
        liking_users = []
        liking_users += response.json().get('data', [])
        token_num = self.token_number
        self.update_headers()
        next_token = response.json().get('meta', {}).get("next_token")
        while next_token:
            params = {
                'max_results': 100,
                'user.fields': 'name,profile_image_url,username',
                'pagination_token': next_token,
            }
            logging.info(f"tweet likes {len(liking_users)}")
            response = requests.get(f"https://api.twitter.com/2/tweets/{tweet_id}/liking_users", headers=self.headers, params=params)
            if response.status_code == TOO_MANY_REQUESTS:
                logging.info("Wait in get_tweet_likes")
                self.update_headers()
                sleep(30)
                logging.info("Retrying")
                continue
            liking_users += response.json().get('data', [])
            next_token = response.json().get('meta', {}).get("next_token")
            if not next_token: break
            time.sleep(5)
        self.update_headers(token_num)
        return liking_users

    def get_user_huge_fans(self, username: str) -> list:
        # Old
        user_id = self.get_user_id_by_username(username)
        tweets = self.get_user_tweets(user_id)

        liking_users_data = {}
        num_tweets = len(tweets)
        counter = total_likes = 0
        for tweet in tweets:
            logging.info(f"{int(counter / len(tweets) * 100)}% has been processed {tweet.get('id')} {username}")
            # if counter % 20 == 19:
            #     self.update_headers()
            #     logging.info("Changing token and waiting 30 seconds")
            #     sleep(30)
            while True:
                try:
                    likes = self.get_tweet_likes(tweet.get('id'))
                    break
                except Exception as e:
                    logging.error(e)
                    self.update_headers()
                    logging.info("Changing token and waiting 5 minutes")
                    sleep(30)
                    logging.info("Trying again")
            counter += 1
            total_likes += len(likes)
            # logging.info(counter)
            for like in likes:
                liking_users_data[like.get('username')] = {
                    'name': like.get('name'),
                    "profile_image_url": self.fix_image_address(like.get('profile_image_url')),
                    "count": liking_users_data.get(like.get('username'), {"count": 0}).get("count", 0) + 1
                }
            sleep(4)

        most_liking_users = dict(sorted(liking_users_data.items(), key=lambda x: x[1].get("count"))[-12:])
        for _username in most_liking_users.keys():
            most_liking_users[_username]["count"] /= num_tweets * 0.01
        # logging.info(res)
        return most_liking_users, total_likes / num_tweets

    def update_headers(self, token_num=-1) -> None:
        # Old
        prev_tok = self.token_number
        if token_num == -1:
            self.token_number += 1
        else:
            self.token_number = token_num
        self.token_number %= len(self.bearer_tokens)
        self.headers = {
            'Authorization': f"Bearer {self.bearer_tokens[self.token_number]}"
        }
        # logging.info(f"Token updated from {prev_tok} to {self.token_number}")

    def update_client(self) -> None:
        # Old
        self.client_number += 1
        self.client = self.clients[self.client_number % len(self.clients)]

    def get_users_by_user_id_list(self, user_ids: list) -> str:
        # Old
        return self.tweepy_api.lookup_users(user_id=user_ids, include_entities=False)

    def send_result_in_direct(self, image_path: str, user_id: str):
        # Old
        try:
            media = self.bot_api.media_upload(image_path)
            self.bot_api.send_direct_message(
                recipient_id=user_id,
                text=self.generate_result_tweet_text(),
                attachment_type="media",
                attachment_media_id=media.media_id)
        except Exception as e:
            logging.error(f"Something went wrong on sending the results in direct {image_path} {user_id}")
            logging.error(e)

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

    def generate_result_tweet_text(self) -> str:
        # Old
        # Choose random element of messages list
        return random.choice(RESULT_TWEET_TEXTS)

    def get_user_most_liked_users(self, username: str, number_of_results: int = 12) -> dict:
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
        user_id = self.get_user_id_by_username(username)
        liked_users, total_likes_count = self.get_user_likes(user_id)
        liked_users = dict(Counter(liked_users))

        most_liked_users = dict(
            sorted(liked_users.items(), key=lambda x: x[-1].get("count", 0), reverse=True)[:number_of_results]
        )

        return most_liked_users, total_likes_count

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

    def load_twitter_config(self, path: str):
        if not os.path.exists(path):
            raise Exception(f"Config file not found at {path}")
        with open(path, "r") as f:
            config = json.load(f)
        
        return config.get("cookies"), config.get("headers")
