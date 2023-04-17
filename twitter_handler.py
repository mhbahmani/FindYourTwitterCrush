from http.client import TOO_MANY_REQUESTS
from collections import Counter
from time import sleep
from pytz import UTC

from messages import RESULT_TWEET_TEXTS

import requests
import datetime
import logging
import tweepy
import twitter
import random
import time
import os

from decouple import config


API_KEY = config("API_KEY2")
API_KEY_SECRET = config("API_KEY_SECRET2")

ACCESS_TOKEN=config("ACCESS_TOKEN2")
ACCESS_TOKEN_SECRET=config("ACCESS_TOKEN_SECRET2")


class Twitter():
    def __init__(self) -> None:
        self.token_number = 2
        self.bearer_tokens = [config("BEARER_TOKEN1"), config("BEARER_TOKEN2"), config("BEARER_TOKEN3")]
        self.update_headers()
        
        auth = tweepy.OAuth1UserHandler(
        API_KEY, API_KEY_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
        )
        self.tweepy_api = tweepy.API(auth)

        self.clients = [tweepy.Client(token) for token in self.bearer_tokens]
        self.client_number = 0
        self.client = self.clients[self.client_number]

        write_auth = tweepy.OAuth1UserHandler(
            config("APP_API_KEY"),
            config("APP_API_KEY_SECRET"),
            config("APP_ACCESS_TOKEN"),
            config("APP_ACCESS_TOKEN_SECRET")
        )
        self.write_api = tweepy.API(write_auth)

        self.write_api = self.tweepy_api

        self.twiiter_api = twitter.Api(
            consumer_key=API_KEY,
            consumer_secret=API_KEY_SECRET,
            access_token_key=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            sleep_on_rate_limit=True

        )

        self.bot_api = None
        self.get_bot_token()

        # self.direct_api = None
        # self.get_direct_api()
    
    def get_tweet_repliers(self, tweet_id: int, tweet_author: str = None, checked: set = set()) -> list:
        # ! deprecated !
        if tweet_author and tweet_author in checked:
            return
        if not tweet_author: tweet_author = self.get_tweet_author_username(tweet_id)
        max_id = None
        page_index = 0
        while True:
            page_index += 1
            try:
                term = "to:%s" % tweet_author
                replies = self.twiiter_api.GetSearch(
                    term=term,
                    since_id=tweet_id,
                    max_id=max_id,
                    count=100,
                )
            except twitter.error.TwitterError as e:
                time.sleep(60)
                continue
            
            if not replies:
                break
            
            for reply in replies:
                if reply.in_reply_to_status_id == tweet_id:
                    checked.add(reply.user.screen_name)
                    yield (reply.user.screen_name, reply.id_str)

            if len(replies) != 100:
                break

    def get_tweet_replies_with_tweepy(self, tweet_id: int, tweet_author: str = None) -> list:
        if not tweet_author: tweet_author = self.get_tweet_author_username(tweet_id)
        repliers = []
        try:
            tweets = tweepy.Cursor(self.write_api.search_tweets, q=f"to:{tweet_author}", since_id=tweet_id, count=100).items(1000)
            for tweet in tweets:
                if tweet.in_reply_to_status_id == tweet_id:
                    repliers.append((tweet.user.screen_name, tweet.id_str))
            return repliers
        except Exception as e:
            logging.error(e)
            time.sleep(15 * 60)
            return self.get_tweet_replies_with_tweepy(tweet_id, tweet_author)

    def get_user_id_by_user_name(self, username: str) -> str:
        response = requests.get(f"https://api.twitter.com/2/users/by/username/{username}", headers=self.headers)
        return response.json().get('data', {}).get('id')

    def get_user_name_by_username(self, username: str) -> str:
        response = requests.get(f"https://api.twitter.com/2/users/by/username/{username}", headers=self.headers)
        return response.json().get('data', {}).get('name')

    def get_user_profile_image(self, username: str=None):
        response = requests.get(f"https://api.twitter.com/1.1/users/show.json?screen_name={username}", headers=self.headers)
        return response.json().get('profile_image_url')

    def get_tweet_author_username(self, tweet_id: str) -> str:
        return self.tweepy_api.get_status(tweet_id).user.screen_name

    def get_user_likes(self, user_id, username: str = None) -> list:
        likes = []
        next_token = None
        counter = 0
        while True:
            try:
                response = self.client.get_liked_tweets(
                    user_id, max_results=100,
                    pagination_token=next_token,
                    tweet_fields=["created_at", "author_id"])
            except Exception as e:
                logging.error(e)
                self.update_client()
                time.sleep(10)
                continue
            if response.data: likes += response.data
            logging.info(f"likes {len(likes)} {username}")
            # if tweet was older than one year
            last_year_date = datetime.datetime.now() - datetime.timedelta(days=365)
            last_year_date = last_year_date.replace(tzinfo=UTC)
            if response.data and response.data[-1].created_at < last_year_date: break
            if response.meta: 
                next_token = response.meta.get("next_token")
                if not next_token: break
            else: break
            time.sleep(4)
        return likes

    def get_user_tweets(self, user_id: str) -> list:
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
        user_id = self.get_user_id_by_user_name(username)
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
        self.client_number += 1
        self.client = self.clients[self.client_number % len(self.clients)]

    def get_users_by_user_id_list(self, user_ids: list) -> str:
        return self.tweepy_api.lookup_users(user_id=user_ids, include_entities=False)

    def get_user_most_liked_users(self, username: str) -> list:
        user_id = self.get_user_id_by_user_name(username)
        liked_user_ids = [like.get('author_id') for like in self.get_user_likes(user_id, username=username)]
        total_likes = len(liked_user_ids)

        users_data = {}
        user_id_count = dict(Counter(liked_user_ids))
        most_liked_users_ids = dict(sorted(user_id_count.items(), key=lambda x: x[1])[-12:])
        liked_users_object = []
        liked_users_object = self.get_users_by_user_id_list(most_liked_users_ids)
        for user in liked_users_object:
            users_data[user.screen_name] = {
                "name": user.name,
                "profile_image_url": self.fix_image_address(user.profile_image_url_https),
                "count": user_id_count.get(user.id, 0),
            }

        return users_data, total_likes

    def tweet_result(self, image_path: str, tweet_id: str):
        try:
            media = self.bot_api.media_upload(image_path)
            self.bot_api.update_status(status=self.generate_result_tweet_text(), media_ids=[media.media_id], in_reply_to_status_id=int(tweet_id), auto_populate_reply_metadata=True)
        except Exception as e:
            logging.error(f"Something went wrong on tweeting the results {image_path} {tweet_id}")
            logging.error(e)

    def send_result_in_direct(self, image_path: str, user_id: str):
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

    def get_bot_token(self):
        # if token file exists, load tokens from it
        tokens_file_path = "bot_tokens.txt"
        tokens = None
        if os.path.exists(tokens_file_path):
            with open(tokens_file_path, "r") as f:
                tokens = f.read()
        if tokens: 
            access_token, access_token_secret = tokens.split()
        else:
            oauth1_user_handler = tweepy.OAuth1UserHandler(
                config("APP_API_KEY"),
                config("APP_API_KEY_SECRET"),
                config("APP_ACCESS_TOKEN"),
                config("APP_ACCESS_TOKEN_SECRET"),
                callback="http://51.89.107.199:5000/callback"
            )
            print(oauth1_user_handler.get_authorization_url())
            # check if tokens file is exists
            # if not, wait for 1 second
            # if tokens file exists, read it and return the tokens
            tokens_file_path = "oauth_tokens.txt"
            while True:
                if os.path.exists(tokens_file_path):
                    with open(tokens_file_path, "r") as f:
                        tokens = f.read()
                    if tokens:
                        break
                sleep(2)
            os.remove(tokens_file_path)
            oauth_token, oauth_verifier = tokens.split(" ")

            request_token = oauth1_user_handler.request_token["oauth_token"]
            request_secret = oauth1_user_handler.request_token["oauth_token_secret"]
            print(request_secret, request_token)

            new_oauth1_user_handler = tweepy.OAuth1UserHandler(
                request_token, request_secret,
                callback="http://51.89.107.199:5000/callback"
            )
            new_oauth1_user_handler.request_token = {
                "oauth_token": oauth_token,
                "oauth_token_secret": request_secret
            }
            access_token, access_token_secret = (
                new_oauth1_user_handler.get_access_token(
                    oauth_verifier
                )
            )

        self.save_bot_tokens(access_token, access_token_secret)
        auth = tweepy.OAuth1UserHandler(
            config("APP_API_KEY"), config("APP_API_KEY_SECRET"),
            access_token, access_token_secret
        )
        self.bot_api = tweepy.API(auth)
        # Generate random text and send it to twitter
        # import random, string
        # text = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
        # try:
        #     self.bot_api.update_status(text)
        # except Exception as e:
        #     logging.error(e)
        #     if os.path.exists(tokens_file_path):
        #         os.remove(tokens_file_path)
        #         self.get_bot_token()

    def save_bot_tokens(self, access_token: str, access_token_secret: str):
        tokens_file_path = "bot_tokens.txt"
        with open(tokens_file_path, "w") as f:
            f.write(f"{access_token} {access_token_secret}")

    def generate_result_tweet_text(self) -> str:
        # Choose random element of messages list
        return random.choice(RESULT_TWEET_TEXTS)
        
    def get_user_directs_sender_ids(self) -> dict:
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
    
    def get_directs_usernames(self) -> list:
        direct_requests = []
        sender_ids = self.get_user_directs_sender_ids()
        # lookup users in 100 user chunks
        i = 0
        while i < len(sender_ids):
            users = self.get_users_by_user_id_list(list(sender_ids.keys())[i:i+100])
            for user in users:
                direct_requests.append({
                    "username": user.screen_name,
                    "user_id": user.id
                })
            i += 100
            time.sleep(1)
        return direct_requests

# twitter_client = Twitter()
# twitter_client.get_directs_usernames()
# print(twitter_client.get_user_most_liked_users("mh_bahmani"))
# print(twitter_client.get_user_huge_fans("mh_bahmani"))
