from http.client import TOO_MANY_REQUESTS
from time import sleep

import requests
import tweepy
import twitter
import time


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

        self.twiiter_api = twitter.Api(
            consumer_key=API_KEY,
            consumer_secret=API_KEY_SECRET,
            access_token_key=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            sleep_on_rate_limit=True

        )
    def get_tweet_repliers(self, tweet_id: int, tweet_author: str = None, checked: set = set()) -> list:
        print(tweet_author in checked)
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
                    yield reply.user.screen_name

            if len(replies) != 100:
                break

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

    def get_user_tweets(self, user_id: str) -> list:
        """
            outputs: [{id: , text: }]
        """
        params = {
            'max_results': 100,
            'exclude': 'replies,retweets',
        }
        response = requests.get(f'https://api.twitter.com/2/users/{user_id}/tweets', headers=self.headers, params=params)
        return response.json().get('data', [])

    def get_tweet_likes(self, tweet_id: str) -> list:
        print(tweet_id)
        params = {
            'max_results': 100,
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
        self.update_headers()
        while next_token := response.json().get('meta', {}).get("next_token"):
            params = {
                'max_results': 100,
                'pagination_token': next_token,
            }
            response = requests.get(f"https://api.twitter.com/2/tweets/{tweet_id}/liking_users", headers=self.headers, params=params)
            if response.status_code == TOO_MANY_REQUESTS:
                sleep(15 * 60)
                response = requests.get(f"https://api.twitter.com/2/tweets/{tweet_id}/liking_users", headers=self.headers, params=params)
            liking_users += response.json().get('data', [])
        self.update_headers(token_num)
        return liking_users

    def get_user_huge_fans(self, username: str) -> list:
        counter = 0
        user_id = self.get_user_id_by_user_name(username)
        tweets = self.get_user_tweets(user_id)
        liking_users = {}
        like_counts = []
        for tweet in tweets:
            if counter % 15 == 0:
                self.update_headers()
                sleep(30)
            try:
                likes = self.get_tweet_likes(tweet.get('id'))
            except Exception as e:
                print(e)
                self.update_headers()
                sleep(15 * 60)
                # print(liking_users)
                likes = self.get_tweet_likes(tweet.get('id'))
            counter += 1
            like_counts.append(len(likes))
            # print(counter)
            for like in likes:
                liking_users[like.get('username')] = liking_users.get(like.get('username'), 0) + 1
            sleep(5)
        res = dict(sorted(liking_users.items(), key=lambda x: x[1])[-20:]), sum(like_counts) / len(like_counts)
        # print(res)
        return res

    def update_headers(self, token_num=-1) -> None:
        prev_tok = self.token_number
        if token_num == -1:
            self.token_number += 1
        else:
            self.token_number = token_num
        self.token_number %= 3
        self.headers = {
            'Authorization': f"Bearer {self.bearer_tokens[self.token_number]}"
        }
        # print(f"Token updated from {prev_tok} to {self.token_number}")

    def butify_output(self, username: str) -> None:
        liking_users, likes_avg = self.get_user_huge_fans(username)
        res = {}
        print()
        liking = {}
        for username, likes in liking_users.items():
            name = self.get_user_name_by_username(username)
            liking[name] = f"{likes}%"
            print(f"{name} ({username}): {likes}%")
        print(f"میانگین لایک: {likes_avg}")
        print()
        print()
        print(liking_users)
        print(list(liking_users.keys()))


# twitter_client = Twitter()
# twitter_client.butify_output("mh_bahmani")