from http.client import TOO_MANY_REQUESTS
from time import sleep
import requests

from decouple import config


class Twitter():
    def __init__(self) -> None:
        self.token_number = 2
        self.bearer_tokens = [config("BEARER_TOKEN1"), config("BEARER_TOKEN2"), config("BEARER_TOKEN3"), config("BEARER_TOKEN4")]
        self.update_headers()

    def get_user_id_by_user_name(self, username: str) -> str:
        response = requests.get(f"https://api.twitter.com/2/users/by/username/{username}", headers=self.headers)
        return response.json().get('data', {}).get('id')

    def get_user_name_by_username(self, username: str) -> str:
        response = requests.get(f"https://api.twitter.com/2/users/by/username/{username}", headers=self.headers)
        return response.json().get('data', {}).get('name')

    def get_user_profile_image(self, username: str=None):
        response = requests.get(f"https://api.twitter.com/1.1/users/show.json?screen_name={username}", headers=self.headers)
        return response.json().get('profile_image_url')

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
        self.token_number %= 4
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

import sys

if __name__ == "__main__":
    username = sys.argv[1]
    print(username)
    twitter_client = Twitter()
    twitter_client.butify_output(username)
